from sqlalchemy.orm import Session

from app import models, schemas
from app.security import verify_password, hash_password
from app.exceptions.base import (
    EmailTakenError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from app.logger import get_logger

logger = get_logger(__name__)


def get_all_users(db: Session) -> list[models.User]:
    """Return all users ordered by newest first. Admin only."""
    logger.info("Admin: fetching all users")
    try:
        return db.query(models.User).order_by(models.User.created_at.desc()).all()
    except Exception as exc:
        logger.exception("Failed to fetch user list: %s", exc)
        raise


def update_profile(
    payload: schemas.UserUpdateRequest,
    current_user: models.User,
    db: Session,
) -> models.User:
    """
    Update the current user's profile fields.
    """
    logger.info("Profile update requested by user id=%d", current_user.id)

    existing = db.query(models.User).filter(
        models.User.email == payload.email,
        models.User.id != current_user.id,
    ).first()

    if existing:
        logger.warning(
            "Email conflict on update — email '%s' already used by user id=%d",
            payload.email, existing.id,
        )
        raise EmailTakenError("Email already in use by another account.")

    try:
        current_user.first_name = payload.first_name
        current_user.last_name  = payload.last_name
        current_user.email      = payload.email
        current_user.phone      = payload.phone
        current_user.dob        = payload.dob

        db.commit()
        db.refresh(current_user)
        logger.info("Profile updated successfully for user id=%d", current_user.id)
        return current_user
    except Exception as exc:
        db.rollback()
        logger.exception("Unexpected error updating profile for user id=%d: %s", current_user.id, exc)
        raise


def change_password(
    payload: schemas.ChangePasswordRequest,
    current_user: models.User,
    db: Session,
) -> None:
    """
    Change the current user's password.
    """
    logger.info("Password change requested by user id=%d", current_user.id)

    if not verify_password(payload.old_password, current_user.hashed_password):
        logger.warning("Password change failed — wrong current password for user id=%d", current_user.id)
        raise InvalidCredentialsError("Incorrect current password.")

    try:
        current_user.hashed_password = hash_password(payload.new_password)
        db.commit()
        logger.info("Password changed successfully for user id=%d", current_user.id)
    except Exception as exc:
        db.rollback()
        logger.exception("Unexpected error changing password for user id=%d: %s", current_user.id, exc)
        raise


def assign_role(
    user_id: int,
    payload: schemas.AssignRoleRequest,
    db: Session,
) -> models.User:
    """
    Assign a new role to a user. Admin only.
    """
    logger.info("Admin: assigning role '%s' to user id=%d", payload.role, user_id)

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        logger.warning("Role assignment failed — user id=%d not found", user_id)
        raise UserNotFoundError()

    try:
        old_role = user.role
        user.role = payload.role
        db.commit()
        db.refresh(user)
        logger.info(
            "Role updated: user id=%d '%s' → '%s'",
            user_id, old_role, payload.role,
        )
        return user
    except Exception as exc:
        db.rollback()
        logger.exception("Unexpected error assigning role to user id=%d: %s", user_id, exc)
        raise
