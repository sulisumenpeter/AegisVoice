from sqlalchemy.orm import Session
import uuid
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.services.transaction_service import TransactionService
from app.services.audit_service import AuditService

class MockExecutor:
    @staticmethod
    def execute_transaction(db: Session, transaction_id: str | uuid.UUID, current_user: User) -> Transaction:
        import uuid
        if isinstance(transaction_id, str):
            transaction_id = uuid.UUID(transaction_id)
        # 1. State must be APPROVED before execution
        txn = db.query(Transaction).filter(Transaction.id == transaction_id).with_for_update().first()
        if not txn:
            raise ValueError("Transaction not found")
            
        if txn.status != TransactionStatus.APPROVED:
            AuditService.log_event(db, txn.idempotency_key, "EXECUTION_REJECTED", {"reason": f"Invalid state: {txn.status}"}, current_user.id)
            raise ValueError("Transaction is not authorized for execution")

        # 2. Advance to EXECUTING
        txn = TransactionService.advance_status(db, txn.id, TransactionStatus.EXECUTING)
        AuditService.log_event(db, txn.idempotency_key, "EXECUTION_STARTED", {"amount": str(txn.amount)}, current_user.id)

        # 3. Simulate Financial System Execution (Mock)
        # In a real system, this would call a banking API.
        execution_success = True

        # 4. Handle Result
        if execution_success:
            txn = TransactionService.advance_status(db, txn.id, TransactionStatus.COMPLETED)
            AuditService.log_event(db, txn.idempotency_key, "EXECUTION_COMPLETED", {"status": "SUCCESS"}, current_user.id)
        else:
            txn = TransactionService.advance_status(db, txn.id, TransactionStatus.FAILED)
            AuditService.log_event(db, txn.idempotency_key, "EXECUTION_FAILED", {"status": "FAILED"}, current_user.id)

        return txn
