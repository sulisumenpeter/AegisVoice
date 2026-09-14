from decimal import Decimal
from typing import List
from pydantic import BaseModel
from app.models.user import User, RoleEnum
from app.services.risk_engine import RiskAssessment

class PolicyDecision(BaseModel):
    decision: str  # ALLOW, STEP_UP, DENY
    reason_codes: List[str]

ROLE_LIMITS = {
    RoleEnum.FINANCE_OFFICER: Decimal("500000.00"),
    RoleEnum.FINANCE_MANAGER: Decimal("5000000.00"),
    RoleEnum.ADMINISTRATOR: Decimal("999999999.00"),
}

class PolicyEngine:
    @staticmethod
    def evaluate(user: User, amount: Decimal, risk: RiskAssessment) -> PolicyDecision:
        reasons = []

        # 1. Hard limits check
        user_limit = ROLE_LIMITS.get(user.role, Decimal("0.00"))
        if amount > user_limit:
            return PolicyDecision(decision="DENY", reason_codes=["AMOUNT_EXCEEDS_USER_LIMIT"])

        # 2. Risk check mapping
        if risk.level == "HIGH":
            return PolicyDecision(decision="DENY", reason_codes=["HIGH_RISK_SCORE_DENIED"])
        
        if risk.level == "MEDIUM":
            return PolicyDecision(decision="STEP_UP", reason_codes=["MEDIUM_RISK_SCORE_REQUIRES_STEP_UP"] + [f.code for f in risk.factors])

        return PolicyDecision(decision="ALLOW", reason_codes=["POLICY_REQUIREMENTS_MET"])
