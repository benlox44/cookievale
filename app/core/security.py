import os
import hmac
import hashlib
from fastapi import Request, HTTPException, status

SECRET_KEY = os.environ["SECRET_KEY"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


def create_admin_token() -> str:
    msg = "admin::session".encode("utf-8")
    return hmac.new(SECRET_KEY.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify_admin_token(token: str) -> bool:
    return hmac.compare_digest(token, create_admin_token())


def get_current_admin(request: Request) -> str:
    token = request.cookies.get("admin_session")
    if not token or not verify_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return "Valentina"
