from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid
from app.models.transaction import Transaction, TransactionStatus
from app.schemas.transaction import TransactionCreate
from app.services.audit_service import AuditService

class TransactionService:
    VALID_TRANSITIONS = {
        TransactionStatus.REQUESTED: [TransactionStatus.EVALUATING],
        TransactionStatus.EVALUATING: [
            TransactionStatus.APPROVED, 
            TransactionStatus.STEP_UP_REQUIRED, 
            TransactionStatus.DENIED
        ],
        TransactionStatus.STEP_UP_REQUIRED: [TransactionStatus.APPROVAL_PENDING],
        TransactionStatus.APPROVAL_PENDING: [
            TransactionStatus.APPROVED, 
            TransactionStatus.REJECTED, 
            TransactionStatus.EXPIRED
        ],
        TransactionStatus.APPROVED: [TransactionStatus.EXECUTING],
        TransactionStatus.EXECUTING: [TransactionStatus.COMPLETED, TransactionStatus.FAILED],
        # Terminal states
        TransactionStatus.DENIED: [],
        TransactionStatus.REJECTED: [],
        TransactionStatus.EXPIRED: [],
        TransactionStatus.COMPLETED: [],
        TransactionStatus.FAILED: []
    }

    @staticmethod
    def advance_status(db: Session, transaction_id: str | uuid.UUID, new_status: TransactionStatus) -> Transaction:
        import uuid
        if isinstance(transaction_id, str):
            transaction_id = uuid.UUID(transaction_id)
        # Use row-level locking to prevent TOCTOU during state transitions
        txn = db.query(Transaction).filter(Transaction.id == transaction_id).with_for_update().first()
        if not txn:
            raise ValueError("Transaction not found")
            
        if new_status not in TransactionService.VALID_TRANSITIONS[txn.status]:
            raise ValueError(f"Invalid state transition from {txn.status} to {new_status}")
            
        txn.status = new_status
        db.commit()
        db.refresh(txn)
        return txn

    @staticmethod
    def create_transaction(db: Session, request: TransactionCreate, user_id: str) -> Transaction:
        existing_txn = db.query(Transaction).filter_by(idempotency_key=request.idempotency_key).first()
        if existing_txn:
            return existing_txn
            
        txn = Transaction(
            idempotency_key=request.idempotency_key,
            user_id=user_id,
            beneficiary_id=request.beneficiary_id,
            amount=request.amount,
            currency=request.currency,
            reason=request.reason,
            status=TransactionStatus.REQUESTED
        )
        db.add(txn)
        db.commit()
        db.refresh(txn)
        return txn
