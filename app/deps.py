from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from database import SessionLocal
from app import models
from app.security import decode_access_token
from app.exceptions.base import InvalidTokenError, ForbiddenError
from app.logger import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


# ── Database session ──────────────────────────────────────────────────────────

def get_db():
    """Yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Authenticated user ────────────────────────────────────────────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if not username:
            raise InvalidTokenError()
    except JWTError:
        logger.warning("JWT decode failed — invalid or expired token")
        raise InvalidTokenError()

    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        logger.warning("Token valid but user '%s' not found in DB", username)
        raise InvalidTokenError()

    return user


# ── Admin-only ────────────────────────────────────────────────────────────────

def get_admin_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role != models.RoleEnum.admin:
        logger.warning(
            "Forbidden: user '%s' (role=%s) attempted admin-only action",
            current_user.username, current_user.role,
        )
        raise ForbiddenError()
    return current_user
