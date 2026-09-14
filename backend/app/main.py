import sys
import os
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

db_url = os.environ.get("DATABASE_URL", "")
if db_url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

try:
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
    
    
    @app.get("/api/setup")
    def setup_database():
        try:
            from scripts.seed import seed_database
            seed_database()
            return {"status": "success", "message": "Database tables and seed data created successfully!"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    from app.api.v1 import api_router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    

except Exception as e:
    err = traceback.format_exc()
    async def app(scope, receive, send):
        assert scope['type'] == 'http'
        await send({
            'type': 'http.response.start',
            'status': 500,
            'headers': [
                (b'content-type', b'text/plain'),
            ]
        })
        await send({
            'type': 'http.response.body',
            'body': err.encode('utf-8'),
        })
