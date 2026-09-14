from fastapi import APIRouter
from app.api.v1 import auth, transactions, voice

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
