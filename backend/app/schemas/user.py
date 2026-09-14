from pydantic import BaseModel, EmailStr, UUID4
from datetime import datetime
from app.models.user import RoleEnum

class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: RoleEnum
    status: str = "ACTIVE"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: UUID4
    created_at: datetime
    class Config:
        from_attributes = True
