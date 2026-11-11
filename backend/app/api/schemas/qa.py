from pydantic import BaseModel, Field


class QAChatRequest(BaseModel):

    query: str = Field(
        ...,
        min_length=1,
    )

    conversation_id: str | None = None


class QAChatResponse(BaseModel):

    query: str

    contract_id: str

    conversation_id: str | None = None

    answer: str

    sources: list[dict] = Field(
        default_factory=list
    )