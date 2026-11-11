from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth.jwt import decode_access_token
from app.database.database import SessionLocal
from app.database.models.user import UserModel
from app.database.repositories.user_repository import UserRepository

from llm.llm_factory import LLMFactory
from retrieval.hybrid_retriever import HybridRetriever
from reranking.reranker_factory import RerankerFactory
from memory.memory_manager import MemoryManager

from modes.contract_qa.workflow import build_qa_chain


security = HTTPBearer()


# ============================================================
# Database
# ============================================================

def get_db() -> Generator[Session, None, None]:

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# Authentication
# ============================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db),
) -> UserModel:

    token = credentials.credentials

    user_id = decode_access_token(token)

    if not user_id:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    user_repository = UserRepository(db)

    user = user_repository.get_by_id(
        user_id
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return user


# ============================================================
# Shared QA Components
# ============================================================

hybrid_retriever = HybridRetriever()

reranker = RerankerFactory.create()

llm = LLMFactory.create()


# ============================================================
# QA Chain
# ============================================================

def get_qa_chain(
    db: Session = Depends(get_db),
):

    memory_manager = MemoryManager(
        session=db
    )

    return build_qa_chain(
        retriever=hybrid_retriever,
        reranker=reranker,
        llm=llm,
        memory_manager=memory_manager,
    )