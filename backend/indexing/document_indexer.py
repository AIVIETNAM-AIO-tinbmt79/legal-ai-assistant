from pathlib import Path

from parser.parser_factory import ParserFactory
from parser.cleaner import TextCleaner

from chunking.chunker_factory import ChunkerFactory

from embeddings.embedding_factory import EmbeddingFactory

from qdrant.vector_store_factory import VectorStoreFactory

from indexing.bm25_indexer import BM25Indexer


class DocumentIndexer:
    """
    Index a document into:

        1. Qdrant vector store
        2. Persistent BM25 index

    Flow:

        Document
            ↓
        Parser
            ↓
        Cleaner
            ↓
        Chunker
            ↓
        ┌───────────────┐
        ↓               ↓
    Embedding        BM25Indexer
        ↓               ↓
      Qdrant        bm25_index.pkl
    """

    def __init__(
        self,
        embedder=None,
        vector_store=None,
        bm25_indexer=None,
    ):

        # ==================================================
        # Embedder
        # ==================================================

        self.embedder = (
            embedder
            or EmbeddingFactory.create()
        )

        # ==================================================
        # Vector Store
        # ==================================================

        self.vector_store = (
            vector_store
            or VectorStoreFactory.create(
                dimension=self.embedder.dimension
            )
        )

        # ==================================================
        # BM25 Indexer
        # ==================================================

        self.bm25_indexer = (
            bm25_indexer
            or BM25Indexer()
        )

    # ==================================================
    # Index
    # ==================================================

    def index(
        self,
        file_path: str | Path,
    ) -> dict:

        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(
                f"Document not found: {file_path}"
            )

        # ==================================================
        # 1. Parse
        # ==================================================

        parser = ParserFactory.get_parser(
            file_path
        )

        text = parser.parse(
            file_path
        )

        if not text or not text.strip():
            raise ValueError(
                "Parsed document is empty."
            )

        # ==================================================
        # 2. Clean
        # ==================================================

        text = TextCleaner.clean(
            text
        )

        if not text or not text.strip():
            raise ValueError(
                "Document is empty after cleaning."
            )

        # ==================================================
        # 3. Chunk
        # ==================================================

        chunker = ChunkerFactory.create(
            text
        )

        chunks = chunker.chunk(
            text
        )

        if not chunks:
            raise ValueError(
                "No chunks were created."
            )

        # ==================================================
        # 4. Embedding
        # ==================================================

        # IMPORTANT:
        #
        # embed_text() currently accepts ONE string,
        # not list[str].
        #
        # Therefore embed each chunk separately.

        embeddings = [
            self.embedder.embed_text(
                chunk.text
            )
            for chunk in chunks
        ]

        if len(embeddings) != len(chunks):
            raise ValueError(
                "Number of embeddings does not "
                "match number of chunks."
            )

        # ==================================================
        # 5. Store vectors in Qdrant
        # ==================================================

        self.vector_store.add_chunks(
            chunks=chunks,
            embeddings=embeddings,
        )

        # ==================================================
        # 6. Build BM25 index
        # ==================================================

        self.bm25_indexer.build_and_save(
            chunks
        )

        # ==================================================
        # 7. Return result
        # ==================================================

        return {
            "file": str(file_path),
            "chunks": len(chunks),
            "embeddings": len(embeddings),
            "vector_dimension": self.embedder.dimension,
            "bm25_index": str(
                self.bm25_indexer.index_path
            ),
        }