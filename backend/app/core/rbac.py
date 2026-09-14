import enum
from app.models.user import RoleEnum

class Permission(str, enum.Enum):
    TRANSACTION_INITIATE = "transaction:initiate"
    TRANSACTION_VIEW_OWN = "transaction:view:own"
    TRANSACTION_VIEW_TEAM = "transaction:view:team"
    TRANSACTION_VIEW_ALL = "transaction:view:all"
    TRANSACTION_APPROVE = "transaction:approve"
    AUDIT_READ = "audit:read"
    POLICY_MANAGE = "policy:manage"
    USER_MANAGE = "user:manage"

# Authorization Matrix
ROLE_PERMISSIONS = {
    RoleEnum.FINANCE_OFFICER: {
        Permission.TRANSACTION_INITIATE, 
        Permission.TRANSACTION_VIEW_OWN
    },
    RoleEnum.FINANCE_MANAGER: {
        Permission.TRANSACTION_INITIATE, 
        Permission.TRANSACTION_APPROVE, 
        Permission.TRANSACTION_VIEW_TEAM
    },
    RoleEnum.AUDITOR: {
        Permission.TRANSACTION_VIEW_ALL, 
        Permission.AUDIT_READ
    },
    RoleEnum.SECURITY_ANALYST: {
        Permission.TRANSACTION_VIEW_ALL, 
        Permission.AUDIT_READ
    },
    RoleEnum.ADMINISTRATOR: {
        Permission.TRANSACTION_VIEW_ALL, 
        Permission.AUDIT_READ, 
        Permission.POLICY_MANAGE, 
        Permission.USER_MANAGE
    },
}

def has_permission(role: RoleEnum, permission: Permission) -> bool:
    """Check if a specific role possesses a permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())
