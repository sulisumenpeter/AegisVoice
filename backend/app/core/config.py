from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AegisVoice"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "supersecretkey_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # AssemblyAI Configuration
    ASSEMBLYAI_API_KEY: str = ""
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://localhost:3000", "http://127.0.0.1:8000", "http://127.0.0.1:3000"]

    # Database
    DATABASE_URL: str = "sqlite:///./aegisvoice.db"
    
    # Redis for distributed rate limiting
    REDIS_URL: str | None = None
    
    # Trusted Proxies (for rate limiting / X-Forwarded-For)
    TRUSTED_PROXY_IPS: list[str] = []

    class Config:
        env_file = ("../.env", ".env")
        extra = "ignore"

settings = Settings()
