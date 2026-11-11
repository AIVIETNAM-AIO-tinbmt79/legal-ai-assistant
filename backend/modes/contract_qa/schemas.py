from typing import TypedDict

from pydantic import BaseModel, Field

from retrieval.retrieval_result import RetrievalResult


# ============================================================
# QA State
# ============================================================

class QAState(TypedDict, total=False):

    # --------------------------------------------------------
    # Input
    # --------------------------------------------------------

    query: str

    contract_id: str | None

    conversation_id: str | None

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    retrieval_results: list[RetrievalResult]

    reranked_results: list[RetrievalResult]

    # --------------------------------------------------------
    # Context
    # --------------------------------------------------------

    context: str

    sources: list[dict]

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    memory: str

    # --------------------------------------------------------
    # LLM
    # --------------------------------------------------------

    prompt: str

    answer: str


# ============================================================
# Final Result
# ============================================================

class QAResult(BaseModel):

    query: str

    contract_id: str | None = None

    conversation_id: str | None = None

    answer: str = ""

    retrieval_results: list[RetrievalResult] = Field(
        default_factory=list
    )

    reranked_results: list[RetrievalResult] = Field(
        default_factory=list
    )

    context: str = ""

    memory: str = ""

    prompt: str = ""

    sources: list[dict] = Field(
        default_factory=list
    )