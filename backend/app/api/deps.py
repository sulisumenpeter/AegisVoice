from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_current_user(db: Session = Depends(get_db)) -> User:
    # Bypass all authentication and just return the first seeded user
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=401, detail="No users found. Run /api/setup first.")
    return user
