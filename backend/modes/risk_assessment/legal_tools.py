from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

from tavily import TavilyClient

from config.settings import settings
from .schemas import (
    LegalReference,
    LegalSearchRequest,
    LegalSearchResult,
)

logger = logging.getLogger(__name__)

DEFAULT_ALLOWED_DOMAINS = [
    "chinhphu.vn",
    "thuvienphapluat.vn",
]

MAX_RESULTS = 3
MIN_CONTENT_LENGTH = 100

_tavily_client: TavilyClient | None = None
_search_cache: dict[tuple[str, tuple[str, ...], int], LegalSearchResult] = {}


def _get_tavily_api_key() -> str:
    api_key = getattr(settings, "TAVILY_API_KEY", None) or os.getenv("TAVILY_API_KEY")
    if not api_key or not str(api_key).strip():
        raise RuntimeError("Thiếu TAVILY_API_KEY trong cấu hình.")
    return str(api_key).strip()


def _get_tavily_client() -> TavilyClient:
    global _tavily_client
    if _tavily_client is None:
        _tavily_client = TavilyClient(api_key=_get_tavily_api_key())
    return _tavily_client


def _normalize_domain(domain: str) -> str:
    return domain.lower().strip().rstrip(".")


def _is_allowed_url(
    url: str,
    allowed_domains: list[str],
) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        hostname = _normalize_domain(hostname)
        return any(
            hostname == _normalize_domain(domain)
            or hostname.endswith("." + _normalize_domain(domain))
            for domain in allowed_domains
        )
    except (ValueError, AttributeError):
        return False


def _get_allowed_domains(
    request: LegalSearchRequest,
) -> list[str]:
    allowed = {_normalize_domain(domain) for domain in DEFAULT_ALLOWED_DOMAINS}

    selected: list[str] = []
    for domain in request.allowed_domains:
        norm = _normalize_domain(domain)
        if norm in allowed and norm not in selected:
            selected.append(norm)

    return selected


def _create_reference(item: dict) -> LegalReference:
    url = (item.get("url") or "").strip()
    content = (item.get("content") or "").strip()
    title = (item.get("title") or "").strip()

    parsed = urlparse(url)
    domain = parsed.hostname or ""
    normalized_domain = _normalize_domain(domain)

    return LegalReference(
        title=title,
        url=url,
        snippet=content[:500],
        content=content,
        domain=domain,
        published_date=None,
        effective_date=None,
        is_official_source=(
            normalized_domain == "chinhphu.vn"
            or normalized_domain.endswith(".chinhphu.vn")
        ),
    )


def clear_legal_search_cache() -> None:
    _search_cache.clear()


def legal_search(request: LegalSearchRequest) -> LegalSearchResult:
    query = request.query.strip()
    if not query:
        return LegalSearchResult(
            query="",
            errors=["Truy vấn tìm kiếm đang trống."],
        )

    allowed_domains = _get_allowed_domains(request)
    if not allowed_domains:
        return LegalSearchResult(
            query=query,
            errors=["Không có domain nào được phép tìm kiếm."],
        )

    max_results = min(request.max_results, MAX_RESULTS)
    cache_key = (
        " ".join(query.lower().split()),
        tuple(allowed_domains),
        max_results,
    )
    cached = _search_cache.get(cache_key)
    if cached is not None:
        logger.info("[LegalSearch] Cache hit for query=%r", query)
        return cached

    references: list[LegalReference] = []
    errors: list[str] = []
    search_count = 0

    try:
        client = _get_tavily_client()
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_domains=allowed_domains,
            include_answer=False,
        )

        raw_results = response.get("results", [])
        search_count = len(raw_results)

        for item in raw_results:
            url = (item.get("url") or "").strip()
            if not _is_allowed_url(url, allowed_domains):
                logger.warning("[LegalSearch] Rejected URL: %s", url)
                continue

            content = (item.get("content") or "").strip()
            if len(content) < MIN_CONTENT_LENGTH:
                logger.info(
                    "[LegalSearch] Skipped short content: %s (%d chars)",
                    url,
                    len(content),
                )
                continue

            try:
                references.append(_create_reference(item))
            except Exception:
                logger.exception(
                    "[LegalSearch] Could not create reference: %s",
                    url,
                )

        logger.info(
            "[LegalSearch] query=%r search_count=%d references=%d",
            query,
            search_count,
            len(references),
        )

    except Exception as exc:
        logger.exception("[LegalSearch] Tavily search failed")
        errors.append(f"Tavily search failed: {type(exc).__name__}: {exc}")

    result = LegalSearchResult(
        query=query,
        references=references,
        search_count=search_count,
        errors=errors,
    )

    if not errors:
        _search_cache[cache_key] = result

    return result