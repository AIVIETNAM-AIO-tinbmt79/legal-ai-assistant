from typing import Iterable
from chunking.chunk_models import Chunk
from .schemas import ContractChunk


MAX_BATCH_TOKENS = 6000


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def convert_chunk(chunk: Chunk) -> ContractChunk:
    metadata = chunk.metadata

    return ContractChunk(
        id=chunk.id,
        text=chunk.text,
        article=metadata.article,
        clause=metadata.clause,
        point=metadata.point,
        hierarchy_path=metadata.hierarchy_path,
        chunk_type=metadata.chunk_type,
        parent_chunk_id=metadata.parent_chunk_id,
    )


def convert_chunks(chunks: Iterable[Chunk]) -> list[ContractChunk]:
    return [convert_chunk(chunk) for chunk in chunks]


def create_batches(
    chunks: list[ContractChunk],
    max_tokens: int = MAX_BATCH_TOKENS,
) -> list[list[ContractChunk]]:
    batches = []
    current = []
    current_tokens = 0

    for chunk in chunks:
        tokens = estimate_tokens(chunk.text)

        if tokens > max_tokens:
            if current:
                batches.append(current)
                current = []
                current_tokens = 0

            batches.append([chunk])
            continue

        if current and current_tokens + tokens > max_tokens:
            batches.append(current)
            current = []
            current_tokens = 0

        current.append(chunk)
        current_tokens += tokens

    if current:
        batches.append(current)

    return batches


def format_batch(batch: list[ContractChunk]) -> str:
    parts = []

    for chunk in batch:
        parts.append(
            f"""
CHUNK_ID: {chunk.id}
HIERARCHY: {chunk.hierarchy_path or ""}
ARTICLE: {chunk.article or ""}
CLAUSE: {chunk.clause or ""}
POINT: {chunk.point or ""}

CONTENT:
{chunk.text}
""".strip()
        )

    return "\n\n".join(parts)
