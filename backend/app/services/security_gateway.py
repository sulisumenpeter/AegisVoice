from sqlalchemy.orm import Session
from app.models.user import User
from app.models.transaction import TransactionStatus
from app.schemas.transaction import TransactionCreate
from app.services.transaction_service import TransactionService
from app.services.risk_engine import RiskEngine
from app.services.policy_engine import PolicyEngine
from app.services.audit_service import AuditService
from app.core.rbac import has_permission, Permission
from datetime import datetime, timedelta, UTC

class SecurityGateway:
    @staticmethod
    def process_transaction_request(db: Session, request: TransactionCreate, current_user: User):
        # 1. Initiate Transaction State (Idempotency Handled)
        txn = TransactionService.create_transaction(db, request, current_user.id)
        if txn.status != TransactionStatus.REQUESTED:
            # Duplicate / previously processed idempotent request
            return txn

        # 2. Advance to EVALUATING
        txn = TransactionService.advance_status(db, txn.id, TransactionStatus.EVALUATING)

        # 3. RBAC (Hard Authorization)
        if not has_permission(current_user.role, Permission.TRANSACTION_INITIATE):
            AuditService.log_event(db, txn.idempotency_key, "TRANSACTION_DENIED", {"reason": "RBAC_FORBIDDEN", "role": current_user.role.value}, current_user.id)
            txn = TransactionService.advance_status(db, txn.id, TransactionStatus.DENIED)
            setattr(txn, "gateway_details", {
                "reason_code": "RBAC_FORBIDDEN",
                "reason_text": "Your current role does not have permission to initiate transactions.",
                "policy_decision": "DENY",
                "next_action": "Contact administrator for permissions."
            })
            return txn

        # 4. Beneficiary Validation (Loading related entity safely)
        from app.models.beneficiary import Beneficiary
        beneficiary = db.query(Beneficiary).filter(Beneficiary.id == request.beneficiary_id).first()
        if not beneficiary:
            AuditService.log_event(db, txn.idempotency_key, "TRANSACTION_DENIED", {"reason": "BENEFICIARY_NOT_FOUND"}, current_user.id)
            txn = TransactionService.advance_status(db, txn.id, TransactionStatus.DENIED)
            setattr(txn, "gateway_details", {
                "reason_code": "BENEFICIARY_NOT_FOUND",
                "reason_text": "The requested beneficiary could not be found or is unauthorized.",
                "policy_decision": "DENY",
                "next_action": "Verify beneficiary ID."
            })
            return txn

        # 5. Risk Assessment
        risk = RiskEngine.evaluate(txn.amount, beneficiary)

        # 6. Policy Evaluation
        policy = PolicyEngine.evaluate(current_user, txn.amount, risk)

        # 7. Audit the decision
        event_data = {
            "amount": str(txn.amount),
            "beneficiary_id": str(beneficiary.id),
            "risk_score": risk.score,
            "risk_factors": [f.code for f in risk.factors],
            "decision": policy.decision,
            "reasons": policy.reason_codes
        }
        AuditService.log_event(db, txn.idempotency_key, "POLICY_EVALUATION", event_data, current_user.id)

        # 8. Apply Decision to State Machine
        reason_code = policy.reason_codes[0] if policy.reason_codes else "POLICY_OK"
        reason_text = "Transaction permitted."
        next_action = "Transaction is queuing for execution."
        
        if policy.decision == "ALLOW":
            txn = TransactionService.advance_status(db, txn.id, TransactionStatus.APPROVED)
        elif policy.decision == "STEP_UP":
            txn.approval_expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=10)
            txn = TransactionService.advance_status(db, txn.id, TransactionStatus.STEP_UP_REQUIRED)
            reason_text = "Transaction exceeds standard limits or triggered high risk factors."
            next_action = "Please provide additional step-up authentication on your device."
        else:
            txn = TransactionService.advance_status(db, txn.id, TransactionStatus.DENIED)
            reason_text = "Transaction explicitly blocked by security policy."
            next_action = "Contact fraud department."

        setattr(txn, "gateway_details", {
            "reason_code": reason_code,
            "reason_text": reason_text,
            "policy_decision": policy.decision,
            "risk_score": risk.score,
            "next_action": next_action
        })
        
        return txn
