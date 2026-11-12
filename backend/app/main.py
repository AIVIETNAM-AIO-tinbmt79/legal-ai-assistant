
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.router import api_router
from app.core.database import init_revoked_tokens_table


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_revoked_tokens_table()
    yield


app = FastAPI(
    title="Contract AI Assisstant API",
    description="API xác thực và hỗ trợ phân tích hợp đồng pháp lý",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Contract AI Assisstant API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
