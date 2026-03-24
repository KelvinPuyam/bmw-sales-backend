from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.deps import get_db, get_current_user, get_admin_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Returns the profile of the currently logged-in user."""
    return current_user


@router.get("/", response_model=list[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),   # admin only
):
    """Returns all registered users. Admin only."""
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.patch("/{user_id}/role", response_model=schemas.UserResponse)
def assign_role(
    user_id: int,
    payload: schemas.AssignRoleRequest,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_admin_user),   # admin only
):
    """Promote or demote a user's role. Admin only."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user
