from contextlib import asynccontextmanager

from fastapi import FastAPI
from config.settings import settings

from app.database.database import init_db
import app.database.models

from app.api.routes.auth import router as auth_router
from app.api.routes.contracts import router as contracts_router
from app.api.routes.qa import router as qa_router
from app.api.routes.risk import router as risk_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=getattr(settings, "APP_NAME", "Legal AI Assistant API"),
    version=getattr(settings, "APP_VERSION", "1.0.0"),
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
    }
)


app.include_router(auth_router, prefix="/api")
app.include_router(contracts_router, prefix="/api")
app.include_router(qa_router, prefix="/api")
app.include_router(risk_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "Legal AI API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}