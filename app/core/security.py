import hashlib
import hmac
import time
from urllib.parse import urlparse

from fastapi import HTTPException, Request, status

from app.core.config import SECRET_KEY, SESSION_TTL_SECONDS

_MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_MAX_CLOCK_SKEW_SECONDS = 60


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

    now = time.time()
    if (
        issued_at > now + _MAX_CLOCK_SKEW_SECONDS
        or now - issued_at > SESSION_TTL_SECONDS
    ):
        return False
    return hmac.compare_digest(signature, _sign(timestamp))


def verify_same_origin(request: Request) -> None:
    """Reject cross-origin mutating requests as defense-in-depth against CSRF."""
    if request.method not in _MUTATING_METHODS:
        return
    origin = request.headers.get("origin")
    if not origin:
        return
    parsed = urlparse(origin)
    if parsed.scheme not in ("http", "https") or parsed.netloc != request.url.netloc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Origen no permitido"
        )


def require_admin(request: Request) -> None:
    token = request.cookies.get("admin_session")
    if not token or not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado"
        )
    verify_same_origin(request)
