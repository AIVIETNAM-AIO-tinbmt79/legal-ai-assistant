from enum import Enum

from chunking.legal_patterns import (
    match_article,
    match_section,
)


class DocumentStructure(str, Enum):
    ARTICLE = "article"
    SECTION = "section"
    PLAIN = "plain"


def detect_structure(text: str) -> DocumentStructure:
    """
    Detect the dominant structure of a document.

    Priority:
        1. Article-based
        2. Section-based
        3. Plain text
    """

    if not text or not text.strip():
        return DocumentStructure.PLAIN

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    article_count = 0
    section_count = 0

    for line in lines:

        if match_article(line):
            article_count += 1

        elif match_section(line):
            section_count += 1

    # Require at least two structural headings
    # before considering the document structured.
    if article_count >= 2:
        return DocumentStructure.ARTICLE

    if section_count >= 2:
        return DocumentStructure.SECTION

    return DocumentStructure.PLAIN