from core.auth import _sign_session_id, _unsign_session_id


def test_signed_session_round_trip():
    signed = _sign_session_id("session-123")
    assert signed != "session-123"
    assert _unsign_session_id(signed) == "session-123"


def test_tampered_session_fails():
    signed = _sign_session_id("session-123")
    assert _unsign_session_id(signed + "x") is None
