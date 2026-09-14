import sys
import os
import traceback

# Fix Vercel Paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_url = os.environ.get("DATABASE_URL", os.environ.get("POSTGRES_URL", ""))
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
os.environ["DATABASE_URL"] = db_url


# Global error state
init_error = None

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from app.core.config import settings
    from app.core.rate_limit import limiter
    
    app_instance = FastAPI(title=settings.PROJECT_NAME)
    
    app_instance.state.limiter = limiter
    app_instance.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    app_instance.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app_instance.get("/health", tags=["Health"])
    def health_check():
        return {"status": "ok", "version": "1.0.0"}
        
    @app_instance.get("/api/setup")
    def setup_database():
        try:
            from scripts.seed import seed_database
            seed_database()
            return {"status": "success", "message": "Database tables and seed data created successfully!"}
        except Exception as e:
            return {"status": "error", "message": traceback.format_exc()}
            
    from app.api.v1 import api_router
    app_instance.include_router(api_router, prefix=settings.API_V1_STR)

except Exception as e:
    init_error = traceback.format_exc()

# Define the global 'app' that Vercel statically finds
async def app(scope, receive, send):
    if init_error:
        assert scope['type'] == 'http'
        await send({
            'type': 'http.response.start',
            'status': 500,
            'headers': [(b'content-type', b'text/plain')]
        })
        await send({
            'type': 'http.response.body',
            'body': init_error.encode('utf-8')
        })
    else:
        # Pass through to FastAPI
        await app_instance(scope, receive, send)
