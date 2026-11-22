import hashlib
import hmac
import time

from fastapi import HTTPException, Request, status

from app.core.config import SECRET_KEY, SESSION_TTL_SECONDS


def _sign(timestamp: str) -> str:
    msg = f"admin::session::{timestamp}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def create_admin_token() -> str:
    timestamp = str(int(time.time()))
    return f"{timestamp}:{_sign(timestamp)}"


def verify_admin_token(token: str) -> bool:
    try:
        timestamp, signature = token.split(":", 1)
        issued_at = int(timestamp)
    except (ValueError, AttributeError):
        return False

    if time.time() - issued_at > SESSION_TTL_SECONDS:
        return False
    return hmac.compare_digest(signature, _sign(timestamp))


def require_admin(request: Request) -> None:
    token = request.cookies.get("admin_session")
    if not token or not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado"
        )
