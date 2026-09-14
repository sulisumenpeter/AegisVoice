import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.user import User, RoleEnum
from app.models.beneficiary import Beneficiary
from app.core.security import get_password_hash

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Create synthetic users
    users_data = [
        {"name": "Finance Officer", "email": "officer@example.com", "role": RoleEnum.FINANCE_OFFICER},
        {"name": "Finance Manager", "email": "finance.manager@example.test", "role": RoleEnum.FINANCE_MANAGER},
        {"name": "Auditor", "email": "auditor@example.test", "role": RoleEnum.AUDITOR},
        {"name": "Security Analyst", "email": "security@example.test", "role": RoleEnum.SECURITY_ANALYST},
        {"name": "Admin", "email": "admin@example.test", "role": RoleEnum.ADMINISTRATOR},
    ]

    hashed_pw = get_password_hash("password")
    
    user_objects = []
    for data in users_data:
        existing = db.query(User).filter_by(email=data["email"]).first()
        if not existing:
            user = User(
                name=data["name"],
                email=data["email"],
                hashed_password=hashed_pw,
                role=data["role"]
            )
            db.add(user)
            user_objects.append(user)
    
    db.commit()

    if user_objects:
        officer = db.query(User).filter_by(email="officer@example.com").first()
        if officer:
            # Create synthetic beneficiaries
            bens = [
                {"name": "Acme Supplies", "account": "BEN-001", "status": "APPROVED"},
                {"name": "ACME Corp", "account": "SYN-1001", "status": "APPROVED"},
                {"name": "Globex Inc", "account": "SYN-1002", "status": "APPROVED"},
                {"name": "Unknown Vendor", "account": "SYN-9999", "status": "PENDING"},
            ]
            for b in bens:
                ben = Beneficiary(name=b["name"], account_identifier=b["account"], status=b["status"], owner_id=officer.id)
                db.add(ben)
            db.commit()
            print("Database seeded with synthetic data.")
    else:
        print("Database already seeded.")
        
    db.close()

if __name__ == "__main__":
    seed_database()
