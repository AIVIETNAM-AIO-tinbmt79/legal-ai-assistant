from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.ai_components import AIComponents
from app.core.database import init_revoked_tokens_table

from modes.risk_assessment.legal_tools import (
    close_neo4j_driver,
    set_shared_reranker,
)




@asynccontextmanager
async def lifespan(app: FastAPI):
    init_revoked_tokens_table()
    # Khởi tạo các thành phần AI khi ứng dụng khởi động
    ai_components = AIComponents()
    app.state.ai_components = ai_components

    # Đăng ký reranker dùng chung cho Risk Assessment
    set_shared_reranker(ai_components.reranker)

    try:
        yield
    finally:
        # Gỡ tham chiếu khi ứng dụng tắt
        set_shared_reranker(None)
        app.state.ai_components = None

        # Đóng kết nối Neo4j
        close_neo4j_driver()


app = FastAPI(lifespan=lifespan)

app.include_router(api_router)


@app.get("/")
def root():
    return {"message": "Contract AI Assisstant API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
