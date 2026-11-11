from pathlib import Path

from parser.parser_factory import ParserFactory
from parser.cleaner import TextCleaner

from chunking.chunker_factory import ChunkerFactory

from embeddings.embedding_factory import EmbeddingFactory

from qdrant.vector_store_factory import VectorStoreFactory

from indexing.bm25_indexer import BM25Indexer


class DocumentIndexer:
    """
    Index a contract/document into:

        1. Qdrant vector store
        2. Shared persistent BM25 index

    Flow:

        Document
            ↓
        Parser
            ↓
        Cleaner
            ↓
        Chunker
            ↓
        Attach contract_id
            ↓
        ┌───────────────┐
        ↓               ↓
    Embedding        BM25Indexer
        ↓               ↓
      Qdrant        Shared BM25
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
        contract_id: str | None = None,
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
        # 4. Attach contract_id
        # ==================================================

        if contract_id:
            for chunk in chunks:
                chunk.metadata.contract_id = (
                    contract_id
                )

        # ==================================================
        # 5. Embedding
        # ==================================================

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
        # 6. Store vectors in Qdrant
        # ==================================================

        self.vector_store.add_chunks(
            chunks=chunks,
            embeddings=embeddings,
        )

        # ==================================================
        # 7. Update shared BM25
        # ==================================================

        if contract_id:

            self.bm25_indexer.upsert_contract(
                chunks=chunks,
                contract_id=contract_id,
            )

        else:

            self.bm25_indexer.build_and_save(
                chunks
            )

        # ==================================================
        # 8. Return result
        # ==================================================

        return {
            "file": str(file_path),
            "contract_id": contract_id,
            "chunks": len(chunks),
            "embeddings": len(embeddings),
            "vector_dimension": self.embedder.dimension,
            "bm25_index": str(
                self.bm25_indexer.index_path
            ),
        }