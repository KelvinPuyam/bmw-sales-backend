from sqlalchemy.orm import Session

from app import models, schemas
from app.security import hash_password, verify_password, create_access_token
from app.exceptions.base import (
    UsernameTakenError,
    EmailTakenError,
    InvalidCredentialsError,
)
from app.logger import get_logger

logger = get_logger(__name__)


def create_user(payload: schemas.SignupRequest, db: Session) -> models.User:
    """
    Register a new user.
    """
    logger.info("Signup attempt for username='%s'", payload.username)

    if db.query(models.User).filter(models.User.username == payload.username).first():
        logger.warning("Signup rejected — username already taken: '%s'", payload.username)
        raise UsernameTakenError()

    if db.query(models.User).filter(models.User.email == payload.email).first():
        logger.warning("Signup rejected — email already registered: '%s'", payload.email)
        raise EmailTakenError()

    try:
        user = models.User(
            username        = payload.username,
            email           = payload.email,
            first_name      = payload.first_name,
            last_name       = payload.last_name,
            phone           = payload.phone,
            dob             = payload.dob,
            hashed_password = hash_password(payload.password),
            role            = models.RoleEnum.user,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("User created successfully: id=%d username='%s'", user.id, user.username)
        return user
    except Exception as exc:
        db.rollback()
        logger.exception("Unexpected error during user creation for '%s': %s", payload.username, exc)
        raise


def authenticate_user(username: str, password: str, db: Session) -> str:
    """
    Validate credentials and return a JWT access token.
    """
    logger.info("Login attempt for username='%s'", username)

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        logger.warning("Login failed for username='%s'", username)
        raise InvalidCredentialsError()

    token = create_access_token({"sub": user.username, "role": user.role})
    logger.info("Login successful for username='%s'", username)
    return token
