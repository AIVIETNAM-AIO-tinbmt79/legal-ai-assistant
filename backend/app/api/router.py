from fastapi import APIRouter
from app.api.routes import auth, contract, conversation, message, qa, risk

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router)
api_router.include_router(contract.router)
api_router.include_router(conversation.router)
api_router.include_router(message.router)
api_router.include_router(qa.router)
api_router.include_router(risk.router)
