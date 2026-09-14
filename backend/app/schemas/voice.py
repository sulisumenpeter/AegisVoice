from pydantic import BaseModel, Field, UUID4, ConfigDict
from decimal import Decimal
from typing import Optional
import uuid

class VoiceSessionResponse(BaseModel):
    session_id: UUID4
    expires_at: str
    
class InitiateTransferIntent(BaseModel):
    beneficiary_reference: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    reason: Optional[str] = None
    
    # CRITICAL: Forbid any prompt-injected authorization fields. 
    # If the LLM hallucinates `role: ADMIN` or `execute: true`, the request fails validation immediately (422).
    model_config = ConfigDict(extra='forbid')

class VoiceIntentResponse(BaseModel):
    decision: str
    transaction_id: Optional[UUID4] = None
    status: str
    reason: str
    reason_code: str
    risk_score: Optional[int] = None
    policy_decision: Optional[str] = None
    next_action: str
