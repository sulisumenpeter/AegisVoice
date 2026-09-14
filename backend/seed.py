import uuid
from decimal import Decimal
from app.core.database import SessionLocal, Base, engine
from app.models.user import User, RoleEnum
from app.models.beneficiary import Beneficiary
from app.core.security import get_password_hash

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if seeded
    if db.query(User).filter(User.email == "officer@example.com").first():
        print("Database already seeded.")
        return

    # Users
    officer = User(
        name="Finance Officer",
        email="officer@example.com",
        hashed_password=get_password_hash("password"),
        role=RoleEnum.FINANCE_OFFICER
    )
    manager = User(
        name="Finance Manager",
        email="manager@example.com",
        hashed_password=get_password_hash("password"),
        role=RoleEnum.FINANCE_MANAGER
    )
    auditor = User(
        name="Auditor",
        email="auditor@example.com",
        hashed_password=get_password_hash("password"),
        role=RoleEnum.AUDITOR
    )
    
    db.add_all([officer, manager, auditor])
    db.commit()

    # Beneficiary
    ben1 = Beneficiary(
        id=uuid.UUID("a0000000-0000-4000-8000-000000000001"),
        name="Trusted Vendor BEN-001",
        account_identifier="ACC-9999",
        owner_id=officer.id,
        status="APPROVED"
    )
    db.add(ben1)
    db.commit()
    print("Database seeded successfully.")
    
if __name__ == "__main__":
    seed_db()
