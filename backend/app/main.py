import sys
import os
import traceback

# Vercel Path Fix
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vercel DB URL Fix
db_url = os.environ.get("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.rate_limit import limiter

app = FastAPI(title=settings.PROJECT_NAME)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
def health_check():
    """Production health check endpoint."""
    return {"status": "ok", "version": "1.0.0"}

from app.api.v1 import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)
