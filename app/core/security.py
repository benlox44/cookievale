import os
import hmac
import hashlib
import time
from fastapi import Request, HTTPException, status

SECRET_KEY = os.environ["SECRET_KEY"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

SESSION_TTL_SECONDS = 8 * 60 * 60


def create_admin_token() -> str:
    timestamp = str(int(time.time()))
    msg = f"admin::session::{timestamp}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{timestamp}:{signature}"


def verify_admin_token(token: str) -> bool:
    try:
        timestamp_str, signature = token.split(":", 1)
        timestamp = int(timestamp_str)
    except (ValueError, AttributeError):
        return False

    if (time.time() - timestamp) > SESSION_TTL_SECONDS:
        return False

    msg = f"admin::session::{timestamp_str}".encode("utf-8")
    expected = hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)


def get_current_admin(request: Request) -> str:
    token = request.cookies.get("admin_session")
    if not token or not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return "Valentina"
