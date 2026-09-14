from slowapi import Limiter
from fastapi import Request
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def safe_get_remote_address(request: Request):
    """
    In production with a trusted proxy, this reads X-Forwarded-For cautiously.
    If no trusted proxy is configured, it falls back to the direct client connection host.
    """
    if settings.TRUSTED_PROXY_IPS and request.client and request.client.host in settings.TRUSTED_PROXY_IPS:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP which is the true client (assuming trusted proxy)
            return forwarded_for.split(",")[0].strip()
            
    return request.client.host if request.client else "127.0.0.1"

def get_user_identifier(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        return token
    return safe_get_remote_address(request)

# Configure storage backend
storage_uri = "memory://"
in_memory_fallback = []
if settings.REDIS_URL:
    storage_uri = settings.REDIS_URL
    # We deliberately disable in_memory fallback for security-sensitive endpoints.
    # A Redis failure will raise an exception (HTTP 500), failing closed securely.
    logger.info(f"Rate Limiter configured with Redis backend (Fail-Closed on disconnect)")
else:
    logger.warning("Rate Limiter configured with IN-MEMORY storage. Not suitable for multi-worker production.")

# Limiter based on Client IP (for unauthenticated routes like Login)
limiter = Limiter(
    key_func=safe_get_remote_address,
    storage_uri=storage_uri,
    in_memory_fallback_enabled=False
)

# Limiter based on Authenticated User (for voice endpoints)
user_limiter = Limiter(
    key_func=get_user_identifier,
    storage_uri=storage_uri,
    in_memory_fallback_enabled=False
)
