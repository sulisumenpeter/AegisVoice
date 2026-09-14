from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.user import UserResponse
from app.api.deps import get_current_user

from app.core.rate_limit import limiter
from fastapi import Request

router = APIRouter()

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token = create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    """Returns the trusted server-side authenticated identity."""
    return current_user

def require_permissions(*permissions: str):
    def dependency(current_user: User = Depends(get_current_user)):
        from app.core.rbac import has_permission, Permission
        for p in permissions:
            if not has_permission(current_user.role, Permission(p)):
                raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return dependency

@router.post("/approve_dummy")
def approve_dummy(current_user: User = Depends(require_permissions("transaction:approve"))):
    return {"status": "approved"}

