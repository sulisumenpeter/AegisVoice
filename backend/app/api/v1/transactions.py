import uuid
from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import TransactionResponse
from app.services.transaction_service import TransactionService
from app.services.audit_service import AuditService
from app.services.mock_executor import MockExecutor
from app.core.rbac import has_permission, Permission

router = APIRouter()

def enforce_expiration(db: Session, txn: Transaction, current_user: User):
    """Lazily enforce expiration if the transaction is pending approval."""
    if txn.status in [TransactionStatus.STEP_UP_REQUIRED, TransactionStatus.APPROVAL_PENDING]:
        if txn.approval_expires_at and datetime.now(UTC).replace(tzinfo=None) > txn.approval_expires_at:
            if txn.status == TransactionStatus.STEP_UP_REQUIRED:
                txn = TransactionService.advance_status(db, txn.id, TransactionStatus.APPROVAL_PENDING)
            txn = TransactionService.advance_status(db, txn.id, TransactionStatus.EXPIRED)
            AuditService.log_event(db, txn.idempotency_key, "TRANSACTION_EXPIRED", {"reason": "Approval time elapsed"}, current_user.id)
            db.commit()
    return txn

@router.post("/{transaction_id}/approve", response_model=TransactionResponse)
def approve_transaction(transaction_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not has_permission(current_user.role, Permission.TRANSACTION_APPROVE):
        raise HTTPException(status_code=403, detail="Forbidden: Missing approve permission")

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).with_for_update().first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn = enforce_expiration(db, txn, current_user)

    if txn.user_id == current_user.id:
        AuditService.log_event(db, txn.idempotency_key, "APPROVAL_DENIED", {"reason": "SELF_APPROVAL_ATTEMPT"}, current_user.id)
        raise HTTPException(status_code=403, detail="Forbidden: Cannot approve own transaction")

    if txn.status not in [TransactionStatus.STEP_UP_REQUIRED, TransactionStatus.APPROVAL_PENDING]:
        raise HTTPException(status_code=400, detail=f"Cannot approve transaction in state {txn.status}")

    # If it was still STEP_UP_REQUIRED, we transition it through APPROVAL_PENDING quickly
    if txn.status == TransactionStatus.STEP_UP_REQUIRED:
        txn = TransactionService.advance_status(db, txn.id, TransactionStatus.APPROVAL_PENDING)

    txn = TransactionService.advance_status(db, txn.id, TransactionStatus.APPROVED)
    AuditService.log_event(db, txn.idempotency_key, "TRANSACTION_APPROVED", {"approver_id": str(current_user.id)}, current_user.id)
    return txn

@router.post("/{transaction_id}/reject", response_model=TransactionResponse)
def reject_transaction(transaction_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not has_permission(current_user.role, Permission.TRANSACTION_APPROVE):
        raise HTTPException(status_code=403, detail="Forbidden: Missing approve permission")

    txn = db.query(Transaction).filter(Transaction.id == transaction_id).with_for_update().first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn = enforce_expiration(db, txn, current_user)

    if txn.status not in [TransactionStatus.STEP_UP_REQUIRED, TransactionStatus.APPROVAL_PENDING]:
        raise HTTPException(status_code=400, detail=f"Cannot reject transaction in state {txn.status}")

    if txn.status == TransactionStatus.STEP_UP_REQUIRED:
        txn = TransactionService.advance_status(db, txn.id, TransactionStatus.APPROVAL_PENDING)

    txn = TransactionService.advance_status(db, txn.id, TransactionStatus.REJECTED)
    AuditService.log_event(db, txn.idempotency_key, "TRANSACTION_REJECTED", {"rejector_id": str(current_user.id)}, current_user.id)
    return txn

@router.post("/{transaction_id}/execute", response_model=TransactionResponse)
def execute_transaction(transaction_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. We just look it up. Real execution authorization happens in the gateway / mock executor boundary.
    txn = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn = enforce_expiration(db, txn, current_user)

    try:
        txn = MockExecutor.execute_transaction(db, str(txn.id), current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return txn
