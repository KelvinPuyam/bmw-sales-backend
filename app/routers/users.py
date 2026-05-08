from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user, get_admin_user
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


# ─────────────────────────────────────────
# Get current user
# ─────────────────────────────────────────
@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Returns the profile of the currently logged-in user."""
    return current_user


# ─────────────────────────────────────────
# Update profile
# ─────────────────────────────────────────
@router.put("/update", response_model=schemas.UserResponse)
def update_profile(
    payload: schemas.UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update current user's profile."""
    return user_service.update_profile(payload, current_user, db)


# ─────────────────────────────────────────
# Change password
# ─────────────────────────────────────────
@router.put("/change-password")
def change_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Change current user's password."""
    user_service.change_password(payload, current_user, db)
    return {"message": "Password updated successfully"}


# ─────────────────────────────────────────
# Admin: list users
# ─────────────────────────────────────────
@router.get("/", response_model=list[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    """Returns all registered users. Admin only."""
    return user_service.get_all_users(db)


# ─────────────────────────────────────────
# Admin: assign role
# ─────────────────────────────────────────
@router.patch("/{user_id}/role", response_model=schemas.UserResponse)
def assign_role(
    user_id: int,
    payload: schemas.AssignRoleRequest,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),
):
    """Promote or demote a user's role. Admin only."""
    return user_service.assign_role(user_id, payload, db)
