from pydantic import BaseModel, Field, UUID4
from decimal import Decimal
from typing import Optional
from datetime import datetime
from app.models.transaction import TransactionStatus

class TransactionBase(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    beneficiary_id: UUID4
    idempotency_key: str = Field(..., min_length=1)
    reason: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: UUID4
    user_id: UUID4
    status: TransactionStatus
    approval_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
