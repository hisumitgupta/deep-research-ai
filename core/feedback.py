from datetime import datetime, timezone

from core.diagnostics import log_event
from core.security import safe_exception
from core.supabase_client import get_supabase_admin_client


def save_user_feedback(
    user_id: str | None,
    email: str,
    rating: int,
    liked: str,
    disliked: str,
    improvement: str,
    contact_ok: bool,
) -> dict:
    try:
        supabase = get_supabase_admin_client()
        row = {
            "user_id": user_id,
            "email": email.strip()[:200],
            "rating": rating,
            "liked": liked.strip()[:2000],
            "disliked": disliked.strip()[:2000],
            "improvement": improvement.strip()[:2000],
            "contact_ok": contact_ok,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("feedback").insert(row).execute()
        return {"success": True, "error": ""}
    except Exception as exc:
        log_event("feedback_save_failed", {"error": safe_exception(exc)})
        return {
            "success": False,
            "error": "Could not save feedback right now. Please try again later.",
        }
