from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from functools import lru_cache
from typing import Any
from dataclasses import dataclass, field

from dotenv import load_dotenv
from neo4j import GraphDatabase

from .schemas import LegalReference
from config.settings import settings


# ============================================================
# CONFIG
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

CHUNKS_FILE = Path(
    os.getenv(
        "CHUNKS_FILE",
        str(BASE_DIR / "data" / "chunks.jsonl"),
    )
)

MAX_ENTITIES = 120
MAX_RELATIONSHIPS = 10  # Agent 3 chỉ mở rộng tối đa 10 cạnh mỗi lượt search
MAX_REFERENCES = 8

# Candidate/reranker settings.
# Model + device are centralized in config.settings so every retrieval
# pipeline uses the same reranker configuration.
LEGAL_RERANK_CANDIDATES = max(
    int(os.getenv("LEGAL_RERANK_CANDIDATES", "30")),
    1,
)

SUPERSESSION_RELATIONS = {"SUPERSEDES", "REPLACES"}


@dataclass
class LegalSearchResult:
    """Kết quả legal_search tương thích với test và dễ dùng cho Agent 3."""
    references: list[LegalReference] = field(default_factory=list)
    search_count: int = 0
    query: str = ""
    search_phrases: list[str] = field(default_factory=list)
    entities: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)

    @property
    def results(self):
        return self.references

    def __len__(self):
        return len(self.references)

    def __iter__(self):
        return iter(self.references)

    def __getitem__(self, index):
        return self.references[index]



# ============================================================
# TEXT HELPERS
# ============================================================


def normalize_text(text: Any) -> str:
    if text is None:
        return ""

    text = str(text).lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip(" .,;:!?()[]{}\"'")


def _clean_phrases(
    search_phrases: list[str] | None,
) -> list[str]:
    phrases = []
    seen = set()

    for phrase in search_phrases or []:
        phrase = normalize_text(phrase)

        if len(phrase) < 3:
            continue

        if phrase in seen:
            continue

        seen.add(phrase)
        phrases.append(phrase)

    return phrases


def _safe_relationship_types(
    relationship_types: list[str] | None,
) -> list[str]:
    result = []

    for value in relationship_types or []:
        value = str(value).strip().upper()

        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
            continue

        if value not in result:
            result.append(value)

    return result


# ============================================================
# NEO4J
# ============================================================


def get_neo4j_driver():
    if not NEO4J_URI:
        raise RuntimeError("Thiếu NEO4J_URI.")

    if not NEO4J_USER:
        raise RuntimeError(
            "Thiếu NEO4J_USER hoặc NEO4J_USERNAME."
        )

    if not NEO4J_PASSWORD:
        raise RuntimeError("Thiếu NEO4J_PASSWORD.")

    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )


# ============================================================
# GRAPH SCHEMA CONTEXT
# ============================================================


def _get_graph_schema_with_driver(driver) -> dict:
    """Đọc schema thực tế được tạo bởi build_graph_v2.py."""
    with driver.session(database=NEO4J_DATABASE) as session:
        entity_rows = session.run("""
            MATCH (e:Entity)
            WHERE e.type IS NOT NULL
            RETURN DISTINCT e.type AS entity_type
            ORDER BY entity_type
        """)
        entity_types = [
            str(row["entity_type"])
            for row in entity_rows
            if row.get("entity_type")
        ]

        relationship_rows = session.run("""
            MATCH ()-[r]->()
            RETURN DISTINCT type(r) AS relationship_type
            ORDER BY relationship_type
        """)
        relationship_types = [
            str(row["relationship_type"])
            for row in relationship_rows
            if row.get("relationship_type")
        ]

    return {
        "entity_types": entity_types,
        "relationship_types": relationship_types,
    }


def get_graph_schema_context(
    search_phrases: list[str] | None = None,
    max_entities: int = 20,
    max_relationships: int = 30,
) -> dict:
    """
    Context cho Agent 3:
    - toàn bộ Entity.type và relationship type đang có trong DB;
    - một nhóm Entity khớp với risk hiện tại để Agent định hướng.

    Không truy vấn Relationship ở bước này. Agent 3 sẽ chọn relationship_types
    trước; legal_search mới truy vấn tối đa relationship_top_k cạnh phù hợp.
    Schema inventory được lấy trực tiếp từ Neo4j; không hardcode type.
    """
    driver = get_neo4j_driver()
    try:
        schema = _get_graph_schema_with_driver(driver)
        phrases = _clean_phrases(search_phrases)
        entities = _search_entities_with_driver(
            driver=driver,
            search_phrases=phrases,
            entity_types=[],
            limit=max(1, min(int(max_entities), MAX_ENTITIES)),
        ) if phrases else []
        # Chỉ gửi Entity mẫu và inventory type. Không mở rộng cạnh trước
        # khi Agent 3 chọn relationship_types, tránh một truy vấn thừa.
        # Chỉ gửi trường cần thiết cho LLM, không đưa JSON provenance dài.
        compact_entities = []
        for item in entities:
            compact_entities.append({
                "entity_id": item.get("entity_id"),
                "text": item.get("text"),
                "normalized_text": item.get("normalized_text"),
                "type": item.get("type"),
                "description": (item.get("description") or "")[:240],
                "chunk_ids": (item.get("chunk_ids") or [])[:8],
                "score": item.get("score"),
            })

        return {
            **schema,
            "matched_entities": compact_entities,
            "matched_relationships": [],
        }
    finally:
        driver.close()


# ============================================================
# ENTITY SEARCH
# ============================================================


def _search_entities_with_driver(
    driver,
    search_phrases: list[str],
    entity_types: list[str] | None = None,
    limit: int | None = None,
    top_k: int | None = None,
) -> list[dict]:
    """
    Tìm Entity theo nhiều phrase và ưu tiên entity match nhiều phrase.

    Điểm quan trọng so với bản cũ:
    - Không LIMIT ngay sau từng phrase rồi mới cắt kết quả.
    - Tính score trên toàn bộ phrase của từng entity.
    - Entity match nhiều phrase được cộng điểm coverage.
    - Giữ entity type bonus nếu Agent cung cấp type.

    Mục đích là tăng recall ở bước candidate; ranking cuối cùng vẫn
    được thực hiện trên chunk trong ``_rank_references``.
    """

    phrases = _clean_phrases(search_phrases)

    if not phrases:
        return []

    entity_types = [
        str(item).strip().upper()
        for item in (entity_types or [])
        if str(item).strip()
    ]

    requested_limit = top_k if top_k is not None else limit
    if requested_limit is None:
        requested_limit = MAX_ENTITIES

    limit = min(
        max(int(requested_limit), 1),
        MAX_ENTITIES,
    )

    query = """
    UNWIND $search_phrases AS phrase

    MATCH (e:Entity)

    WITH
        e,
        phrase,
        toLower(coalesce(e.text, "")) AS text,
        toLower(coalesce(e.normalized_text, "")) AS normalized,
        toLower(coalesce(e.description, "")) AS description

    WITH
        e,
        phrase,
        CASE
            WHEN text = phrase THEN 30 + size(phrase) * 0.8
            WHEN text CONTAINS phrase THEN 20 + size(phrase) * 0.6
            ELSE 0
        END AS text_score,
        CASE
            WHEN normalized = phrase THEN 25 + size(phrase) * 0.7
            WHEN normalized CONTAINS phrase THEN 16 + size(phrase) * 0.5
            ELSE 0
        END AS normalized_score,
        CASE
            WHEN description CONTAINS phrase THEN 4
            ELSE 0
        END AS description_score

    WITH
        e,
        phrase,
        text_score
        + normalized_score
        + description_score AS phrase_score,
        (text_score > 0 OR normalized_score > 0) AS matched

    WITH
        e,
        collect({
            phrase: phrase,
            score: phrase_score,
            matched: matched
        }) AS matches

    WITH
        e,
        matches,
        reduce(
            total = 0.0,
            item IN matches |
            total + item.score
        ) AS total_score,
        reduce(
            best = 0.0,
            item IN matches |
            CASE
                WHEN item.score > best THEN item.score
                ELSE best
            END
        ) AS best_score,
        size([item IN matches WHERE item.matched]) AS matched_count

    WITH
        e,
        matches,
        best_score
        + total_score * 0.15
        + CASE
            WHEN matched_count >= 3 THEN 32
            WHEN matched_count = 2 THEN 18
            ELSE 0
          END AS base_score,
        matched_count

    WITH
        e,
        matches,
        base_score
        + CASE
            WHEN e.type IN $entity_types
                 AND matched_count > 0
            THEN 10
            ELSE 0
          END AS score,
        matched_count

    WHERE matched_count > 0

    RETURN
        e.entity_id AS entity_id,
        e.chunk_ids AS chunk_ids,
        e.document_ids AS document_ids,
        e.occurrence_count AS occurrence_count,
        e.text AS text,
        e.normalized_text AS normalized_text,
        e.type AS type,
        e.description AS description,
        [item IN matches WHERE item.matched | item.phrase] AS matched_phrases,
        matched_count AS phrase_coverage,
        score AS score

    ORDER BY
        score DESC,
        phrase_coverage DESC
    LIMIT $limit
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            query,
            search_phrases=phrases,
            entity_types=entity_types,
            limit=limit,
        )

        rows = [dict(record) for record in result]

    unique = {}

    for row in rows:
        entity_id = row.get("entity_id")

        if not entity_id:
            continue

        old = unique.get(entity_id)

        if old is None or float(row.get("score") or 0) > float(
            old.get("score") or 0
        ):
            unique[entity_id] = row

    return sorted(
        unique.values(),
        key=lambda item: (
            float(item.get("score") or 0),
            int(item.get("phrase_coverage") or 0),
        ),
        reverse=True,
    )[:limit]


def search_entities(
    search_phrases: list[str] | None = None,
    entity_types: list[str] | None = None,
    top_k: int | None = None,
    driver=None,
    limit: int | None = None,
) -> list[dict]:
    """
    Public entity-search API.

    - Test có thể gọi trực tiếp mà không cần truyền driver.
    - legal_search có thể truyền driver để tái sử dụng connection.
    """
    owns_driver = driver is None
    if owns_driver:
        driver = get_neo4j_driver()

    requested_limit = top_k if top_k is not None else limit
    if requested_limit is None:
        requested_limit = MAX_ENTITIES

    try:
        return _search_entities_with_driver(
            driver=driver,
            search_phrases=search_phrases or [],
            entity_types=entity_types or [],
            limit=requested_limit,
        )
    finally:
        if owns_driver:
            driver.close()


# ============================================================
# RELATIONSHIP SEARCH
# ============================================================


def _search_relationships_with_driver(
    driver,
    entity_ids: list[str] | None = None,
    relationship_types: list[str] | None = None,
    limit: int | None = None,
    top_k: int | None = None,
    search_phrases: list[str] | None = None,
) -> list[dict]:
    """
    Lấy relationship quanh các Entity đã tìm được.

    Logic tương đương nodes.py nhưng dùng entity_id vì DB hiện tại
    không có node_id.

    Relationship type lấy bằng type(r), không dùng r.relation.
    """

    # Test có thể truyền search_phrases thay vì entity_ids.
    # Khi đó dùng chính entity search logic để lấy entity IDs trước.
    if not entity_ids and search_phrases:
        matched_entities = _search_entities_with_driver(
            driver=driver,
            search_phrases=search_phrases,
            entity_types=[],
            top_k=MAX_ENTITIES,
        )
        entity_ids = [
            item.get("entity_id")
            for item in matched_entities
            if item.get("entity_id")
        ]

    entity_ids = [
        str(item)
        for item in entity_ids or []
        if item
    ]

    if not entity_ids:
        return []

    safe_types = _safe_relationship_types(
        relationship_types
    )

    # Không có type được Agent 3 chọn thì không mở rộng toàn bộ graph.
    # Entity search và lexical fallback vẫn tiếp tục ở legal_search.
    if not safe_types:
        return []

    rel_pattern = ":" + "|".join(safe_types)

    requested_limit = top_k if top_k is not None else limit
    if requested_limit is None:
        requested_limit = MAX_RELATIONSHIPS

    limit = min(
        max(int(requested_limit), 1),
        MAX_RELATIONSHIPS,
    )

    query = f"""
    UNWIND $entity_ids AS entity_id

    MATCH (e:Entity {{entity_id: entity_id}})
          -[r{rel_pattern}]-(other:Entity)

    WITH DISTINCT e, r, other

    WITH e, r, other,
        reduce(
            score = 0.0,
            phrase IN $search_phrases |
            score + CASE
                WHEN toLower(coalesce(r.evidence, "")) CONTAINS phrase THEN 3.0
                WHEN any(item IN coalesce(r.evidence_list, [])
                         WHERE toLower(item) CONTAINS phrase) THEN 3.0
                WHEN toLower(coalesce(other.text, "")) CONTAINS phrase THEN 2.0
                WHEN toLower(coalesce(e.text, "")) CONTAINS phrase THEN 1.0
                ELSE 0.0
            END
        ) AS relevance

    RETURN
        e.entity_id AS source_entity_id,
        e.chunk_ids AS source_chunk_ids,
        e.document_ids AS source_document_ids,
        e.text AS source_text,
        e.type AS source_type,

        type(r) AS relation,

        other.entity_id AS target_entity_id,
        other.chunk_ids AS target_chunk_ids,
        other.document_ids AS target_document_ids,
        other.text AS target_text,
        other.type AS target_type,

        r.relationship_id AS relationship_id,
        r.chunk_ids AS relationship_chunk_ids,
        r.document_ids AS relationship_document_ids,
        r.evidence AS evidence,
        r.evidence_list AS evidence_list,
        r.provenance_count AS provenance_count,
        r.needs_semantic_review AS needs_semantic_review,
        relevance AS score

    ORDER BY relevance DESC, coalesce(r.provenance_count, 0) DESC
    LIMIT $limit
    """

    with driver.session(database=NEO4J_DATABASE) as session:
        result = session.run(
            query,
            entity_ids=entity_ids,
            search_phrases=_clean_phrases(search_phrases),
            limit=limit,
        )

        return [dict(record) for record in result]


def search_relationships(
    search_phrases: list[str] | None = None,
    relationship_types: list[str] | None = None,
    top_k: int | None = None,
    entity_ids: list[str] | None = None,
    driver=None,
    limit: int | None = None,
) -> list[dict]:
    """
    Public relationship-search API.

    Test có thể truyền search_phrases + relationship_types trực tiếp.
    Nếu có entity_ids thì dùng trực tiếp; nếu không, tìm Entity trước.
    """
    owns_driver = driver is None
    if owns_driver:
        driver = get_neo4j_driver()

    requested_limit = top_k if top_k is not None else limit
    if requested_limit is None:
        requested_limit = MAX_RELATIONSHIPS

    try:
        return _search_relationships_with_driver(
            driver=driver,
            entity_ids=entity_ids,
            relationship_types=relationship_types or [],
            limit=requested_limit,
            search_phrases=search_phrases,
            top_k=requested_limit,
        )
    finally:
        if owns_driver:
            driver.close()


# ============================================================
# CHUNK LEXICAL FALLBACK
# ============================================================


def _lexical_chunk_candidates(
    chunks: dict[str, dict],
    search_phrases: list[str],
    limit: int = 40,
) -> list[tuple[str, float]]:
    """
    Fallback trực tiếp trên chunks.jsonl.

    Mục đích: nếu extraction chưa tạo Entity/Relationship cho một điều
    khoản quan trọng, retrieval vẫn có đường lui để lấy đúng chunk.

    Đây chỉ là candidate generation; ranking cuối vẫn chạy qua
    _rank_references().
    """

    phrases = _clean_phrases(search_phrases)
    if not phrases:
        return []

    # Tính độ hiếm của phrase trên toàn bộ corpus thay vì hardcode
    # một danh sách từ "generic" theo từng lĩnh vực.
    phrase_document_frequency = {phrase: 0 for phrase in phrases}
    total_documents = 0

    for data in chunks.values():
        content = normalize_text(data.get("content") or "")
        title = normalize_text(data.get("title") or "")
        if not content:
            continue
        total_documents += 1
        for phrase in phrases:
            if phrase in content or phrase in title:
                phrase_document_frequency[phrase] += 1

    total_documents = max(total_documents, 1)

    scored = []

    for chunk_id, data in chunks.items():
        content = normalize_text(data.get("content") or "")
        title = normalize_text(data.get("title") or "")

        if not content:
            continue

        score = 0.0
        coverage = 0

        for phrase in phrases:
            if not phrase:
                continue

            # IDF-like weight: phrase xuất hiện càng ít trong corpus thì
            # càng có giá trị phân biệt, hoàn toàn độc lập với domain.
            df = phrase_document_frequency.get(phrase, 0)
            rarity = 1.0 + math.log((total_documents + 1) / (df + 1))
            weight = min(8.0 + len(phrase) * 0.7, 24.0) * rarity

            if phrase in content:
                score += 25.0 + weight
                coverage += 1

            if phrase in title:
                score += 20.0 + weight

        if coverage == 0:
            continue

        if coverage >= 3:
            score += 60.0
        elif coverage == 2:
            score += 38.0

        scored.append((chunk_id, score, coverage))

    scored.sort(
        key=lambda item: (
            item[1],
            item[2],
        ),
        reverse=True,
    )

    return [
        (chunk_id, score)
        for chunk_id, score, _ in scored[:limit]
    ]

# ============================================================
# DOCUMENT STATUS / SUPERSESSION
# ============================================================


def _get_superseded_document_ids(driver) -> set[str]:
    """Lấy document_ids từ Entity occurrence arrays theo schema build_graph_v2."""
    query = """
    MATCH (new:Entity)-[r]->(old:Entity)
    WHERE type(r) IN ['SUPERSEDES', 'REPLACES']
    UNWIND coalesce(old.document_ids, []) AS old_document_id
    RETURN DISTINCT old_document_id AS document_id
    """

    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            return {
                str(record["document_id"])
                for record in session.run(query)
                if record.get("document_id")
            }
    except Exception as exc:
        # Supersession chỉ là tín hiệu xếp hạng phụ; không làm hỏng retrieval.
        print(f"[Legal Search] Không đọc được supersession metadata: {exc}")
        return set()


def _document_status_bonus(
    reference: LegalReference,
    superseded_document_ids: set[str],
    chunks: dict[str, dict],
) -> float:
    """
    Tín hiệu generic dựa trên metadata trạng thái của document.

    Không phụ thuộc lĩnh vực, loại nghĩa vụ hay nội dung query.
    """

    data = chunks.get(reference.chunk_id, {})
    document_id = str(data.get("document_id") or "")

    if document_id and document_id in superseded_document_ids:
        return -90.0

    status = normalize_text(
        data.get("status")
        or data.get("document_status")
        or data.get("legal_status")
        or ""
    )

    if any(
        term in status
        for term in (
            "đã hết hiệu lực",
            "hết hiệu lực",
            "bị thay thế",
            "được thay thế",
            "superseded",
            "repealed",
        )
    ):
        return -100.0

    if any(
        term in status
        for term in (
            "còn hiệu lực",
            "đang hiệu lực",
            "effective",
            "current",
            "active",
        )
    ):
        return 25.0

    return 0.0


# ============================================================
# CHUNKS
# ============================================================


def load_chunks_file() -> dict[str, dict]:
    """Backward-compatible alias used by the Neo4j test module."""
    return load_chunks()


def load_chunks() -> dict[str, dict]:
    """
    Load backend/data/chunks.jsonl.

    Neo4j lưu chunk_ids trên Entity/Relationship để truy xuất provenance.
    Nội dung pháp luật đầy đủ được lấy từ chunks.jsonl.
    """

    path = Path(CHUNKS_FILE)

    if not path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy chunks.jsonl: {path}"
        )

    chunks = {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(file, 1):
            line = line.strip()

            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"[Chunks] Bỏ dòng JSON lỗi: {line_number}"
                )
                continue

            chunk_id = (
                data.get("chunk_id")
                or data.get("id")
            )

            if chunk_id:
                chunks[chunk_id] = data

    return chunks


# ============================================================
# REFERENCES
# ============================================================


def _build_reference(
    chunk_id: str,
    data: dict,
    score: float = 0.0,
) -> LegalReference:
    return LegalReference(
        chunk_id=chunk_id,
        title=data.get("title", ""),
        article=(
            data.get("article")
            or data.get("article_number")
        ),
        clause=(
            data.get("clause")
            or data.get("clause_number")
        ),
        point=(
            data.get("point")
            or data.get("point_number")
        ),
        content=data.get("content", ""),
        score=float(score),
    )


def _rank_references(
    references: list[LegalReference],
    search_phrases: list[str],
    chunks: dict[str, dict] | None = None,
    superseded_document_ids: set[str] | None = None,
) -> list[LegalReference]:
    """
    Xếp hạng candidate references bằng các tín hiệu retrieval tổng quát.

    Không chứa rule riêng cho bất kỳ lĩnh vực hoặc loại query nào.
    Các tín hiệu gồm:
    - entity score từ Neo4j;
    - exact phrase match trong content/title;
    - độ hiếm của phrase trong tập candidate (IDF-like);
    - coverage của nhiều phrase;
    - độ dài/specificity của phrase;
    - metadata trạng thái/supersession của document.

    Đây là candidate ranking, không phải semantic/legal reasoning.
    """
    phrases = _clean_phrases(search_phrases)
    chunks = chunks or {}
    superseded_document_ids = superseded_document_ids or set()

    if not phrases:
        return references

    # Tính độ hiếm phrase trên candidate set. Không có vocabulary hardcode.
    document_frequency = {phrase: 0 for phrase in phrases}
    total_candidates = 0

    for reference in references:
        content = normalize_text(reference.content)
        title = normalize_text(reference.title)
        if not content and not title:
            continue

        total_candidates += 1
        for phrase in phrases:
            if phrase in content or phrase in title:
                document_frequency[phrase] += 1

    total_candidates = max(total_candidates, 1)

    ranked = []

    for reference in references:
        content = normalize_text(reference.content)
        title = normalize_text(reference.title)

        entity_score = float(reference.score or 0.0)
        base_score = entity_score * 0.35
        lexical_score = 0.0
        matched_count = 0
        matched_lengths = []

        for phrase in phrases:
            phrase_tokens = re.findall(r"\w+", phrase, flags=re.UNICODE)
            token_count = max(len(phrase_tokens), 1)

            # Phrase dài/mang nhiều token có tính phân biệt tự nhiên cao hơn.
            specificity = min(8.0 + token_count * 4.0 + len(phrase) * 0.15, 28.0)

            df = document_frequency.get(phrase, 0)
            idf = 1.0 + math.log((total_candidates + 1) / (df + 1))

            if phrase in content:
                lexical_score += (24.0 + specificity) * idf
                matched_count += 1
                matched_lengths.append(len(phrase))

            if phrase in title:
                lexical_score += (14.0 + specificity * 0.6) * idf

        coverage_ratio = matched_count / len(phrases)
        coverage_bonus = coverage_ratio * 30.0

        # Match ở phần đầu chunk thường hữu ích vì nhiều chunk có heading/
        # mô tả điều khoản trước nội dung chi tiết. Đây vẫn là heuristic
        # vị trí tổng quát, không phụ thuộc vocabulary pháp lý.
        prefix_bonus = 0.0
        first_part = content[:300]
        for phrase in phrases:
            if phrase in first_part:
                prefix_bonus += 8.0

        status_bonus = _document_status_bonus(
            reference=reference,
            superseded_document_ids=superseded_document_ids,
            chunks=chunks,
        )

        score = (
            base_score
            + lexical_score
            + coverage_bonus
            + prefix_bonus
            + status_bonus
        )

        reference.score = round(score, 3)

        if matched_count > 0 or entity_score > 0:
            ranked.append(
                (
                    reference,
                    matched_count,
                    max(matched_lengths or [0]),
                )
            )

    ranked.sort(
        key=lambda item: (
            item[0].score,
            item[1],
            item[2],
        ),
        reverse=True,
    )

    return [item[0] for item in ranked]


# ============================================================
# SEMANTIC RERANKING
# ============================================================

@lru_cache(maxsize=1)
def _get_legal_reranker():
    """
    Lazy-load CrossEncoder so importing legal_tools does not immediately
    load a large ML model.

    Model và device được lấy trực tiếp từ config.settings để dùng chung
    với các pipeline khác của project.
    """
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        raise RuntimeError(
            "Chưa cài sentence-transformers. Cài bằng: "
            "pip install sentence-transformers"
        ) from exc

    return CrossEncoder(
        settings.RERANKER_MODEL,
        device=settings.RERANKER_DEVICE,
        max_length=settings.RERANKER_MAX_LENGTH,
    )


def _reference_rerank_text(reference: LegalReference) -> str:
    """Build the text seen by the semantic reranker."""
    parts = []

    if reference.title:
        parts.append(str(reference.title))

    if reference.article:
        parts.append(str(reference.article))

    if reference.clause:
        parts.append(str(reference.clause))

    if reference.point:
        parts.append(str(reference.point))

    if reference.content:
        parts.append(str(reference.content))

    return "\n".join(parts).strip()


def _semantic_rerank(
    query: str,
    references: list[LegalReference],
    top_k: int,
) -> list[LegalReference]:
    """
    Semantic reranking trên một candidate set nhỏ.

    Retrieval/ranking phía trước chịu trách nhiệm recall.
    CrossEncoder chỉ chịu trách nhiệm sắp xếp lại candidate theo mức
    liên quan giữa toàn bộ query và toàn bộ chunk.
    """
    if not references or not query.strip():
        return references[:top_k]

    reranker = _get_legal_reranker()

    if reranker is None:
        return references[:top_k]

    pairs = [
        (query, _reference_rerank_text(reference))
        for reference in references
    ]

    scores = reranker.predict(
        pairs,
        show_progress_bar=False,
    )

    scored = []

    for reference, semantic_score in zip(references, scores):
        try:
            value = float(semantic_score)
        except (TypeError, ValueError):
            value = float("-inf")

        scored.append((reference, value))

    scored.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    # Semantic score là score cuối của bước reranking.
    # Không cộng các điểm keyword cũ vào đây để tránh một lexical hit
    # mạnh đánh bại relevance ngữ nghĩa.
    result = []

    for reference, semantic_score in scored[:top_k]:
        reference.score = round(semantic_score, 6)
        result.append(reference)

    return result


# ============================================================
# LEGAL SEARCH
# ============================================================


def legal_search(
    query: str,
    search_phrases: list[str],
    entity_types: list[str] | None = None,
    relationship_types: list[str] | None = None,
    top_k: int = 5,
    relationship_top_k: int = 10,
    rerank: bool | None = None,
    rerank_candidates: int | None = None,
) -> LegalSearchResult:
    """
    Legal retrieval tool cho Agent.

    Flow:

        search_phrases
              ↓
        Neo4j Entity search
              ↓
        Entity IDs
              ↓
        Relationship search
              ↓
        candidate chunk IDs
              ↓
        chunks.jsonl
              ↓
        rank references
              ↓
        top_k LegalReference

    Tool chỉ RETRIEVE.
    Không kết luận hợp đồng có vi phạm pháp luật hay không.
    """

    phrases = _clean_phrases(search_phrases)

    # Nếu Agent không tạo search phrase thì dùng query.
    if not phrases and query:
        phrases = _clean_phrases([query])

    if not phrases:
        return LegalSearchResult(query=query, search_phrases=phrases)

    top_k = min(
        max(int(top_k), 1),
        MAX_REFERENCES,
    )

    chunks = load_chunks()
    driver = get_neo4j_driver()
    superseded_document_ids = set()

    try:
        graph_schema = _get_graph_schema_with_driver(driver)
        valid_entity_types = set(graph_schema["entity_types"])
        valid_relationship_types = set(graph_schema["relationship_types"])

        # Chỉ sử dụng type thực sự tồn tại trong database.
        requested_entity_types = [
            str(item).strip()
            for item in (entity_types or [])
            if str(item).strip() in valid_entity_types
        ]
        requested_relationship_types = [
            item for item in _safe_relationship_types(relationship_types)
            if item in valid_relationship_types
        ]

        entities = _search_entities_with_driver(
            driver=driver,
            search_phrases=phrases,
            entity_types=requested_entity_types,
            limit=MAX_ENTITIES,
        )

        entity_ids = [
            entity.get("entity_id")
            for entity in entities
            if entity.get("entity_id")
        ]

        relationships = _search_relationships_with_driver(
            driver=driver,
            entity_ids=entity_ids,
            relationship_types=requested_relationship_types,
            top_k=min(max(int(relationship_top_k), 1), MAX_RELATIONSHIPS),
            search_phrases=phrases,
        )

        superseded_document_ids = _get_superseded_document_ids(
            driver=driver,
        )

    finally:
        driver.close()

    # --------------------------------------------------------
    # Candidate chunk IDs (Entity/Relationship lưu mảng chunk_ids)
    # --------------------------------------------------------

    candidate_chunk_ids = set()
    chunk_scores = {}

    def add_chunk_scores(chunk_ids, score):
        for value in chunk_ids or []:
            if not value:
                continue
            chunk_id = str(value)
            candidate_chunk_ids.add(chunk_id)
            chunk_scores[chunk_id] = max(
                chunk_scores.get(chunk_id, 0.0),
                float(score or 0.0),
            )

    for entity in entities:
        add_chunk_scores(
            entity.get("chunk_ids"),
            entity.get("score"),
        )

    for relationship in relationships:
        # Source/target chunk arrays là occurrences của hai Entity.
        add_chunk_scores(
            relationship.get("source_chunk_ids"),
            float(relationship.get("score") or 0.0),
        )
        add_chunk_scores(
            relationship.get("target_chunk_ids"),
            float(relationship.get("score") or 0.0),
        )
        add_chunk_scores(
            relationship.get("relationship_chunk_ids"),
            float(relationship.get("score") or 0.0),
        )

    # --------------------------------------------------------
    # Lexical fallback
    # --------------------------------------------------------
    # Không phụ thuộc hoàn toàn vào entity extraction.
    # Nếu một điều khoản có phrase trực tiếp nhưng chưa có Entity,
    # nó vẫn được đưa vào candidate set.
    lexical_candidates = _lexical_chunk_candidates(
        chunks=chunks,
        search_phrases=phrases,
        limit=40,
    )

    for chunk_id, _lexical_score in lexical_candidates:
        candidate_chunk_ids.add(chunk_id)

    if not candidate_chunk_ids:
        return LegalSearchResult(query=query, search_phrases=phrases)

    # Relationship evidence chứa phrase thì cộng nhẹ điểm cho các chunk
    # provenance; relationship không tự tạo kết luận pháp lý.
    for relationship in relationships:
        evidence_values = relationship.get("evidence_list") or []
        if relationship.get("evidence"):
            evidence_values = [relationship["evidence"], *evidence_values]
        evidence_text = normalize_text(" ".join(map(str, evidence_values)))

        if not evidence_text or not any(
            phrase in evidence_text for phrase in phrases
        ):
            continue

        relation = str(relationship.get("relation") or "").upper()
        relation_bonus = 6.0
        if relation in set(requested_relationship_types):
            relation_bonus += 4.0

        for chunk_id in (relationship.get("relationship_chunk_ids") or []):
            if not chunk_id:
                continue
            chunk_id = str(chunk_id)
            candidate_chunk_ids.add(chunk_id)
            chunk_scores[chunk_id] = chunk_scores.get(chunk_id, 0.0) + relation_bonus

    # --------------------------------------------------------
    # Build references from chunks.jsonl
    # --------------------------------------------------------

    lexical_score_map = dict(lexical_candidates)

    for chunk_id, lexical_score in lexical_score_map.items():
        # Nếu chunk đã có entity score, lexical fallback chỉ bổ sung nhẹ.
        # Nếu chưa có, score này là tín hiệu candidate ban đầu.
        chunk_scores[chunk_id] = (
            chunk_scores.get(chunk_id, 0.0)
            + lexical_score * 0.35
        )

    references = []

    for chunk_id in candidate_chunk_ids:
        data = chunks.get(chunk_id)

        if not data:
            continue

        references.append(
            _build_reference(
                chunk_id=chunk_id,
                data=data,
                score=chunk_scores.get(chunk_id, 0.0),
            )
        )

    # --------------------------------------------------------
    # Rank
    # --------------------------------------------------------

    references = _rank_references(
        references=references,
        search_phrases=phrases,
        chunks=chunks,
        superseded_document_ids=superseded_document_ids,
    )

    # --------------------------------------------------------
    # Dedupe
    # --------------------------------------------------------

    unique = {}

    for reference in references:
        old = unique.get(reference.chunk_id)

        if (
            old is None
            or reference.score > old.score
        ):
            unique[reference.chunk_id] = reference

    references = sorted(
        unique.values(),
        key=lambda item: item.score,
        reverse=True,
    )

    # --------------------------------------------------------
    # Semantic reranking
    # --------------------------------------------------------
    # Chỉ rerank một candidate set nhỏ để kiểm soát latency.
    # Nếu tắt rerank thì legal_search vẫn hoạt động như candidate retriever.

    # Mặc định dùng reranker đã cấu hình trong config.settings.
    # Caller vẫn có thể truyền rerank=False để bỏ qua bước này khi cần.
    use_rerank = True if rerank is None else bool(rerank)

    candidate_limit = max(
        top_k,
        rerank_candidates or LEGAL_RERANK_CANDIDATES,
    )

    candidate_references = references[:candidate_limit]

    if use_rerank and candidate_references:
        try:
            references = _semantic_rerank(
                query=query,
                references=candidate_references,
                top_k=top_k,
            )
        except Exception as exc:
            # Retrieval phải vẫn chạy được nếu model reranker chưa sẵn sàng.
            # Không nuốt lỗi khi caller chủ động bật rerank.
            if rerank is True:
                raise

            print(f"[Legal Reranker] fallback to generic ranking: {exc}")
            references = references[:top_k]
    else:
        references = references[:top_k]

    return LegalSearchResult(
        references=references,
        search_count=len(references),
        query=query,
        search_phrases=phrases,
        entities=entities,
        relationships=relationships,
    )
