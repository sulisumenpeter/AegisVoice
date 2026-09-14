import uuid
import json
from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.voice_session import VoiceSession
from app.schemas.voice import VoiceSessionResponse, InitiateTransferIntent, VoiceIntentResponse
from app.schemas.transaction import TransactionCreate
from app.services.security_gateway import SecurityGateway
from app.services.audit_service import AuditService
from app.core.rate_limit import user_limiter
from fastapi import Request

router = APIRouter()

import httpx
from app.core.config import settings

@router.get("/token")
@user_limiter.limit("10/minute")
async def get_assemblyai_token(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Exchanges the permanent AssemblyAI API key for a short-lived temporary token
    so the frontend can securely connect to AssemblyAI without leaking the main key.
    """
    if not settings.ASSEMBLYAI_API_KEY:
        raise HTTPException(status_code=501, detail="AssemblyAI API key not configured on server")
        
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://streaming.assemblyai.com/v3/token?expires_in_seconds=600",
                headers={"Authorization": settings.ASSEMBLYAI_API_KEY}
            )
            res.raise_for_status()
            return {"token": res.json()["token"]}
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error fetching token: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=500, detail=f"AssemblyAI API Error: {e.response.text}")
    except Exception as e:
        print(f"Unknown Error fetching token: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch temporary voice token")

class TranscriptPayload(BaseModel):
    transcript: str

@router.post("/session", response_model=VoiceSessionResponse)
@user_limiter.limit("10/minute")
def create_voice_session(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a time-bound voice session anchored to the strictly authenticated backend user.
    """
    # Expiration in 15 minutes
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=15)
    
    session = VoiceSession(
        user_id=current_user.id,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    AuditService.log_event(db, str(session.id), "VOICE_SESSION_CREATED", {"user_id": str(current_user.id)}, current_user.id)
    
    return {"session_id": session.id, "expires_at": expires_at.isoformat()}

@router.post("/intent", response_model=VoiceIntentResponse)
@user_limiter.limit("20/minute")
def handle_voice_intent(
    request: Request,
    intent: InitiateTransferIntent,
    x_voice_session_id: uuid.UUID = Header(...),
    idempotency_key: str = Header(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Webhook/Endpoint for AssemblyAI tool calls.
    Extracts the authenticated user via the session ID and matches against JWT.
    """
    voice_session = db.query(VoiceSession).filter(VoiceSession.id == x_voice_session_id).first()
    
    if not voice_session or not voice_session.is_active:
        raise HTTPException(status_code=401, detail="Invalid or inactive voice session")
        
    if voice_session.expires_at < datetime.now(UTC).replace(tzinfo=None):
        raise HTTPException(status_code=401, detail="Voice session expired")
        
    if voice_session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Voice session does not belong to the authenticated user")
        
    if current_user.status != "ACTIVE":
        raise HTTPException(status_code=401, detail="User is invalid or inactive")

    # Resolve beneficiary_reference to a deterministic internal UUID
    from app.services import beneficiary_resolver
    ref = intent.beneficiary_reference
    
    beneficiary = beneficiary_resolver.resolve(db, ref)
        
    if not beneficiary:
        # User requested to return a structured DENY response rather than crashing the tool flow
        return {
            "decision": "DENY",
            "transaction_id": None,
            "status": "DENIED",
            "reason_code": "BENEFICIARY_NOT_FOUND",
            "reason": f"Beneficiary reference '{ref}' could not be resolved to a valid account.",
            "risk_score": None,
            "policy_decision": "DENY",
            "next_action": "Please provide a valid beneficiary reference."
        }

    # Use provided idempotency key, or derive one deterministically from the session if none provided
    # (Since AssemblyAI tool calls don't natively send custom headers easily, we can fallback to session ID + amount)
    derived_key = idempotency_key or f"{x_voice_session_id}-{beneficiary.id}-{intent.amount}"

    # Map intent to backend transaction request
    # Note: We completely rely on the Pydantic model to have stripped out injected roles/flags
    transaction_request = TransactionCreate(
        amount=intent.amount,
        currency=intent.currency,
        beneficiary_id=beneficiary.id,
        reason=intent.reason or "Voice Initiated Transfer",
        idempotency_key=derived_key
    )
    
    # Process through Security Gateway
    try:
        txn = SecurityGateway.process_transaction_request(db, transaction_request, current_user)
    except Exception as e:
        AuditService.log_event(db, str(x_voice_session_id), "VOICE_INTENT_FAILED", {"error": str(e)}, current_user.id)
        raise HTTPException(status_code=400, detail=str(e))
        
    # Derive decision from status
    if txn.status.value == "APPROVED":
        decision = "ALLOW"
    elif txn.status.value == "STEP_UP_REQUIRED":
        decision = "STEP_UP"
    else:
        decision = "DENY"
        
    details = getattr(txn, "gateway_details", {})
        
    # Build structured response that controls the LLM's conversation
    return {
        "decision": decision,
        "transaction_id": txn.id,
        "status": txn.status.value,
        "reason": details.get("reason_text", "Transaction processed."),
        "reason_code": details.get("reason_code", "OK"),
        "risk_score": details.get("risk_score"),
        "policy_decision": details.get("policy_decision"),
        "next_action": details.get("next_action", "No further action required.")
    }
