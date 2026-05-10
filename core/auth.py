import base64
import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

from core.supabase_client import get_supabase_admin_client, get_supabase_client
from core.diagnostics import log_event
from core.security import public_error, safe_exception


AUTH_USER_KEY = "auth_user"
AUTH_SESSION_KEY = "auth_session"
SESSION_STATE_ID_KEY = "auth_session_id"
SESSION_COOKIE_NAME = "dr_session"
SESSION_STORE_PATH = Path(".auth_sessions.json")
SESSION_SECRET_PATH = Path(".session_secret")
SESSION_TTL_DAYS = 7


def _clean_email(email: str) -> str:
    return email.strip().lower()


def _app_url() -> str:
    return (
        os.getenv("APP_URL", "").strip()
        or os.getenv("SITE_URL", "").strip()
        or "http://localhost:8501"
    )


def _user_to_dict(user, profile: dict | None = None) -> dict:
    profile = profile or {}
    return {
        "id": user.id,
        "email": user.email,
        "name": profile.get("name", ""),
        "phone": profile.get("phone", ""),
        "plan": profile.get("plan", "free"),
        "is_active": profile.get("is_active", True),
    }


def _profile_to_user(profile: dict) -> dict:
    return {
        "id": profile["id"],
        "email": profile.get("email", ""),
        "name": profile.get("name", ""),
        "phone": profile.get("phone", ""),
        "plan": profile.get("plan", "free"),
        "is_active": profile.get("is_active", True),
    }


def _read_store() -> dict:
    if not SESSION_STORE_PATH.exists():
        return {}

    try:
        return json.loads(SESSION_STORE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log_event("auth_session_store_read_failed", {"error": safe_exception(exc)})
        return {}


def _write_store(store: dict) -> None:
    SESSION_STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _session_secret() -> str:
    secret = os.getenv("SESSION_SECRET_KEY", "").strip()
    if secret:
        return secret

    if os.getenv("APP_ENV", "").lower() == "production":
        raise RuntimeError("SESSION_SECRET_KEY is required when APP_ENV=production.")

    if SESSION_SECRET_PATH.exists():
        return SESSION_SECRET_PATH.read_text(encoding="utf-8").strip()

    secret = secrets.token_urlsafe(48)
    SESSION_SECRET_PATH.write_text(secret, encoding="utf-8")
    return secret


def _hash_session_id(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def _sign_session_id(session_id: str) -> str:
    payload = base64.urlsafe_b64encode(session_id.encode("utf-8")).decode("utf-8")
    signature = hmac.new(
        _session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def _unsign_session_id(value: str | None) -> str | None:
    if not value:
        return None

    try:
        payload, signature = value.rsplit(".", 1)
        expected_signature = hmac.new(
            _session_secret().encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return None
        return base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8")
    except Exception:
        return None


def _cookie_secure_flag() -> str:
    return "; Secure" if os.getenv("APP_ENV", "").lower() == "production" else ""


def _set_browser_cookie(name: str, value: str, max_age_seconds: int) -> None:
    cookie = (
        f"{name}={quote(value)}; path=/; max-age={max_age_seconds}; "
        f"SameSite=Lax{_cookie_secure_flag()}"
    )
    components.html(
        f"<script>document.cookie = {json.dumps(cookie)};</script>",
        height=0,
        width=0,
    )


def _delete_browser_cookie(name: str) -> None:
    cookie = f"{name}=; path=/; max-age=0; SameSite=Lax{_cookie_secure_flag()}"
    components.html(
        f"<script>document.cookie = {json.dumps(cookie)};</script>",
        height=0,
        width=0,
    )


def _create_server_session(user: dict) -> str:
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    store = _read_store()
    store[_hash_session_id(session_id)] = {
        "user": user,
        "expires_at": expires_at.isoformat(),
    }
    _write_store(store)
    return session_id


def _create_token_session(access_token: str, refresh_token: str) -> str:
    session_id = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    store = _read_store()
    store[_hash_session_id(session_id)] = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at.isoformat(),
    }
    _write_store(store)
    return session_id


def _delete_server_session(session_id: str | None) -> None:
    if not session_id:
        return

    store = _read_store()
    store.pop(_hash_session_id(session_id), None)
    _write_store(store)


def _stored_tokens(session_id: str | None) -> dict | None:
    if not session_id:
        return None

    session = _read_store().get(_hash_session_id(session_id))
    if not session:
        return None

    try:
        expires_at = datetime.fromisoformat(session["expires_at"])
    except Exception:
        _delete_server_session(session_id)
        return None

    if expires_at <= datetime.now(timezone.utc):
        _delete_server_session(session_id)
        return None

    return session


def save_auth_session(session) -> None:
    if not session:
        return

    old_session_id = st.session_state.get(SESSION_STATE_ID_KEY)
    _delete_server_session(old_session_id)

    session_id = _create_token_session(session.access_token, session.refresh_token)
    st.session_state[SESSION_STATE_ID_KEY] = session_id
    st.session_state[AUTH_SESSION_KEY] = {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    }
    _set_browser_cookie(
        SESSION_COOKIE_NAME,
        _sign_session_id(session_id),
        SESSION_TTL_DAYS * 24 * 60 * 60,
    )


def save_user_session(user: dict) -> None:
    if not user:
        return

    old_session_id = st.session_state.get(SESSION_STATE_ID_KEY)
    _delete_server_session(old_session_id)

    session_id = _create_server_session(user)
    st.session_state[SESSION_STATE_ID_KEY] = session_id
    st.session_state[AUTH_USER_KEY] = user
    st.session_state[AUTH_SESSION_KEY] = {"type": "custom_user"}
    _set_browser_cookie(
        SESSION_COOKIE_NAME,
        _sign_session_id(session_id),
        SESSION_TTL_DAYS * 24 * 60 * 60,
    )


def _save_login_response(auth_response) -> dict | None:
    if not auth_response or not auth_response.user:
        return None

    profile = get_profile(auth_response.user.id)
    user = _user_to_dict(auth_response.user, profile)
    st.session_state[AUTH_USER_KEY] = user
    save_auth_session(auth_response.session)
    return user


def clear_auth_session() -> None:
    _delete_server_session(st.session_state.get(SESSION_STATE_ID_KEY))
    st.session_state.pop(AUTH_USER_KEY, None)
    st.session_state.pop(AUTH_SESSION_KEY, None)
    st.session_state.pop(SESSION_STATE_ID_KEY, None)
    _delete_browser_cookie(SESSION_COOKIE_NAME)


def restore_auth_session() -> dict | None:
    signed_session_id = st.context.cookies.get(SESSION_COOKIE_NAME)
    session_id = _unsign_session_id(signed_session_id)
    stored_session = _stored_tokens(session_id)
    if not stored_session:
        return None

    if stored_session.get("user"):
        user = stored_session["user"]
        st.session_state[AUTH_USER_KEY] = user
        st.session_state[AUTH_SESSION_KEY] = {"type": "custom_user"}
        st.session_state[SESSION_STATE_ID_KEY] = session_id
        return user

    try:
        supabase = get_supabase_client()
        response = supabase.auth.set_session(
            stored_session["access_token"],
            stored_session["refresh_token"],
        )
        if not response.user:
            return None

        profile = get_profile(response.user.id)
        user = _user_to_dict(response.user, profile)
        st.session_state[AUTH_USER_KEY] = user
        st.session_state[AUTH_SESSION_KEY] = stored_session
        st.session_state[SESSION_STATE_ID_KEY] = session_id
        return user
    except Exception as exc:
        log_event("auth_restore_failed", {"error": safe_exception(exc)})
        clear_auth_session()
        return None


def create_profile(user_id: str, email: str, name: str, phone: str) -> dict:
    supabase = get_supabase_admin_client()
    profile_data = {
        "id": user_id,
        "email": email,
        "name": name.strip(),
        "phone": phone.strip(),
        "plan": "free",
        "is_active": True,
    }
    response = supabase.table("profiles").insert(profile_data).execute()
    if not response.data:
        return {"success": False, "error": "Profile was not created.", "profile": None}
    return {"success": True, "error": "", "profile": response.data[0]}


def get_profile(user_id: str) -> dict | None:
    supabase = get_supabase_admin_client()
    response = (
        supabase
        .table("profiles")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def _verify_password(password: str, stored_password: str) -> bool:
    try:
        method, salt, digest = stored_password.split("$", 2)
    except ValueError:
        return False

    if method != "pbkdf2_sha256":
        return False

    expected = _hash_password(password, salt).split("$", 2)[2]
    return hmac.compare_digest(expected, digest)


def _find_user_by_email(email: str) -> dict | None:
    supabase = get_supabase_admin_client()
    response = (
        supabase
        .table("users")
        .select("*")
        .eq("email", email)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def _find_user_by_phone(phone: str) -> dict | None:
    supabase = get_supabase_admin_client()
    response = (
        supabase
        .table("users")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def signup_user(email: str, password: str, name: str, phone: str) -> dict:
    supabase = get_supabase_admin_client()
    email = _clean_email(email)
    name = name.strip()
    phone = phone.strip()

    if not name:
        return {"success": False, "error": "Name is required.", "user": None}
    if not phone:
        return {"success": False, "error": "Phone is required.", "user": None}
    if len(password) < 8:
        return {"success": False, "error": "Password must be at least 8 characters.", "user": None}

    try:
        if _find_user_by_email(email):
            return {"success": False, "error": "An account already exists with this email.", "user": None}
        if _find_user_by_phone(phone):
            return {"success": False, "error": "An account already exists with this phone number.", "user": None}

        row = {
            "id": str(uuid.uuid4()),
            "name": name,
            "phone": phone,
            "email": email,
            "password": _hash_password(password),
            "is_active": True,
        }
        response = supabase.table("users").insert(row).execute()
        if not response.data:
            return {"success": False, "error": "Signup failed. User was not created.", "user": None}

        user = _profile_to_user(response.data[0])
        save_user_session(user)
        return {"success": True, "error": "", "user": user}
    except Exception as exc:
        log_event("signup_failed", {"email": email, "error": safe_exception(exc)})
        return {"success": False, "error": public_error("Signup failed. Please check your details and try again."), "user": None}


def login_user(email: str, password: str) -> dict:
    email = _clean_email(email)

    try:
        profile = _find_user_by_email(email)
        if not profile or not _verify_password(password, profile.get("password", "")):
            return {"success": False, "error": "Login failed. Invalid email or password.", "user": None}
        if not profile.get("is_active", True):
            return {"success": False, "error": "This account is disabled.", "user": None}

        user = _profile_to_user(profile)
        save_user_session(user)
        return {"success": True, "error": "", "user": user}
    except Exception as exc:
        log_event("login_failed", {"email": email, "error": safe_exception(exc)})
        return {"success": False, "error": public_error("Login failed. Please try again."), "user": None}


def logout_user() -> None:
    try:
        get_supabase_client().auth.sign_out()
    except Exception as exc:
        log_event("logout_supabase_failed", {"error": safe_exception(exc)})
    clear_auth_session()


def current_user() -> dict | None:
    user = st.session_state.get(AUTH_USER_KEY)
    return user if user else restore_auth_session()


def is_logged_in() -> bool:
    return current_user() is not None


def require_login() -> dict:
    user = current_user()
    if user:
        return user
    st.warning("Please login to continue.")
    st.stop()
