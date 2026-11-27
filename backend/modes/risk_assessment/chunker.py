from __future__ import annotations

import re
from typing import Iterable

from chunking.chunk_models import Chunk
from .schemas import ContractChunk


MAX_BATCH_TOKENS = 6000

_TERM_LINE_RE = re.compile(
    r'^\s*(?:[-•*]\s*|\d+[.)]\s*)?[“"\']?([^“"\':\n]{2,60})[”"\']?\s*(?:là|được hiểu là|:)\s*(.+)$',
    re.IGNORECASE,
)


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 3)


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


def extract_global_terms_map(
    chunks: list[ContractChunk],
    max_terms: int = 40,
) -> dict[str, str]:
    """Bóc tách thuật ngữ định nghĩa ở các điều/mục giải thích từ ngữ."""
    terms_map: dict[str, str] = {}

    for chunk in chunks:
        header = f"{chunk.article or ''} {chunk.hierarchy_path or ''} {chunk.chunk_type}".lower()
        is_definition_section = any(
            kw in header for kw in ("định nghĩa", "giải thích từ ngữ", "definition")
        )
        if not is_definition_section:
            continue

        for raw_line in (chunk.text or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            match = _TERM_LINE_RE.match(line)
            if not match:
                continue
            term = re.sub(r"\s+", " ", match.group(1)).strip(" \"'“”")
            definition = re.sub(r"\s+", " ", match.group(2)).strip()
            if term and definition and term not in terms_map:
                terms_map[term] = definition[:300]
                if len(terms_map) >= max_terms:
                    return terms_map

    return terms_map


def _group_by_article(chunks: list[ContractChunk]) -> list[list[ContractChunk]]:
    """Nhóm các chunk cùng một Điều để hạn chế cắt rời giữa chừng."""
    groups: list[list[ContractChunk]] = []
    current_group: list[ContractChunk] = []
    current_article: str | None = None

    for chunk in chunks:
        article_key = chunk.article.strip() if chunk.article else None
        if article_key and article_key == current_article:
            current_group.append(chunk)
        else:
            if current_group:
                groups.append(current_group)
            current_group = [chunk]
            current_article = article_key

    if current_group:
        groups.append(current_group)

    return groups


def create_batches(
    chunks: list[ContractChunk],
    max_tokens: int = MAX_BATCH_TOKENS,
) -> list[list[ContractChunk]]:
    """Gom batch theo giới hạn token nhưng ưu tiên giữ trọn từng Điều."""
    batches: list[list[ContractChunk]] = []
    current: list[ContractChunk] = []
    current_tokens = 0

    for article_group in _group_by_article(chunks):
        group_tokens = sum(estimate_tokens(c.text) for c in article_group)

        if group_tokens > max_tokens:
            if current:
                batches.append(current)
                current = []
                current_tokens = 0

            sub_current: list[ContractChunk] = []
            sub_tokens = 0
            for chunk in article_group:
                c_tokens = estimate_tokens(chunk.text)
                if sub_current and sub_tokens + c_tokens > max_tokens:
                    batches.append(sub_current)
                    sub_current = []
                    sub_tokens = 0
                sub_current.append(chunk)
                sub_tokens += c_tokens
            if sub_current:
                batches.append(sub_current)
            continue

        if current and current_tokens + group_tokens > max_tokens:
            batches.append(current)
            current = []
            current_tokens = 0

        current.extend(article_group)
        current_tokens += group_tokens

    if current:
        batches.append(current)

    return batches


def format_terms_map(terms_map: dict[str, str] | None) -> str:
    if not terms_map:
        return "Không có mục định nghĩa thuật ngữ riêng."
    return "\n".join(f"- {term}: {defn}" for term, defn in terms_map.items())


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