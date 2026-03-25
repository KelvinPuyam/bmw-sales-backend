from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user, get_admin_user
from app.security import verify_password, hash_password

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
    """Update current user's profile"""

    # optional: prevent duplicate email
    existing = db.query(models.User).filter(
        models.User.email == payload.email,
        models.User.id != current_user.id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")

    current_user.first_name = payload.first_name
    current_user.last_name = payload.last_name
    current_user.email = payload.email
    current_user.phone = payload.phone
    current_user.dob = payload.dob

    db.commit()
    db.refresh(current_user)

    return current_user


# ─────────────────────────────────────────
# Change password
# ─────────────────────────────────────────
@router.put("/change-password")
def change_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Change current user's password"""

    # verify old password
    if not verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    # set new password
    current_user.hashed_password = hash_password(payload.new_password)

    db.commit()

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
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


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
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user
