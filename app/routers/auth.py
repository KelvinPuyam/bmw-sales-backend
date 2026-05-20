from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import schemas
from app.deps import get_db
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    return auth_service.create_user(payload, db)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    """JSON login — use this in React."""
    token = auth_service.authenticate_user(payload.username, payload.password, db)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/token", response_model=schemas.TokenResponse, include_in_schema=False)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Form-data login — only exists so the Swagger Authorize button works."""
    token = auth_service.authenticate_user(form_data.username, form_data.password, db)
    return {"access_token": token, "token_type": "bearer"}
