from chunking.article_chunker import ArticleChunker
from chunking.base_chunker import BaseChunker
from chunking.document_structure import (
    DocumentStructure,
    detect_structure,
)
from chunking.fallback_chunker import FallbackChunker
from chunking.section_chunker import SectionChunker


class ChunkerFactory:

    @staticmethod
    def create(text: str) -> BaseChunker:

        structure = detect_structure(text)

        if structure == DocumentStructure.ARTICLE:
            return ArticleChunker()

        if structure == DocumentStructure.SECTION:
            return SectionChunker()

        return FallbackChunker()