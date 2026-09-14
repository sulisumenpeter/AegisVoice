from decimal import Decimal
from typing import List
from pydantic import BaseModel
from app.models.beneficiary import Beneficiary

class RiskFactor(BaseModel):
    code: str
    points: int

class RiskAssessment(BaseModel):
    score: int
    level: str  # LOW, MEDIUM, HIGH
    factors: List[RiskFactor]

class RiskEngine:
    @staticmethod
    def evaluate(amount: Decimal, beneficiary: Beneficiary) -> RiskAssessment:
        """Deterministic risk scoring (No ML)."""
        score = 0
        factors = []

        if not beneficiary or beneficiary.status != "APPROVED":
            score += 50
            factors.append(RiskFactor(code="UNAPPROVED_BENEFICIARY", points=50))

        if amount > Decimal("50000.00"):
            score += 40
            factors.append(RiskFactor(code="HIGH_VALUE_TRANSACTION", points=40))
        elif amount > Decimal("10000.00"):
            score += 20
            factors.append(RiskFactor(code="MEDIUM_VALUE_TRANSACTION", points=20))

        if score < 30:
            level = "LOW"
        elif score < 70:
            level = "MEDIUM"
        else:
            level = "HIGH"

        return RiskAssessment(score=score, level=level, factors=factors)
