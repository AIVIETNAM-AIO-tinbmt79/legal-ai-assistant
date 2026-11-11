from pathlib import Path
import pickle

from rank_bm25 import BM25Okapi
from underthesea import word_tokenize

from chunking.chunk_models import Chunk


class BM25Indexer:
    """
    Persistent BM25 indexer.

    The BM25 index is shared across all contracts.

    Each chunk is associated with a contract_id through:

        chunk.metadata.contract_id

    When a contract is indexed again, its old chunks are
    replaced instead of duplicating them.
    """

    def __init__(
        self,
        index_path: str | Path = (
            "storage/bm25/bm25_index.pkl"
        ),
    ):
        self.index_path = Path(index_path)

        self.chunks: list[Chunk] = []
        self.tokenized_corpus: list[list[str]] = []
        self.bm25: BM25Okapi | None = None

    # ==================================================
    # Tokenization
    # ==================================================

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """
        Tokenize Vietnamese text using Underthesea.
        """

        if not text:
            return []

        tokenized_text = word_tokenize(
            text,
            format="text",
        )

        return tokenized_text.split()

    # ==================================================
    # Build
    # ==================================================

    def build(
        self,
        chunks: list[Chunk],
    ) -> None:
        """
        Build BM25 index from chunks.
        """

        if not chunks:
            raise ValueError(
                "Cannot build BM25 index from empty chunks."
            )

        self.chunks = list(chunks)

        self.tokenized_corpus = [
            self.tokenize(chunk.text)
            for chunk in self.chunks
        ]

        self.bm25 = BM25Okapi(
            self.tokenized_corpus
        )

    # ==================================================
    # Save
    # ==================================================

    def save(self) -> None:
        """
        Persist BM25 index to disk.
        """

        if self.bm25 is None:
            raise RuntimeError(
                "BM25 index has not been built."
            )

        self.index_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "chunks": self.chunks,
            "tokenized_corpus": self.tokenized_corpus,
            "bm25": self.bm25,
        }

        with open(
            self.index_path,
            "wb",
        ) as file:

            pickle.dump(
                data,
                file,
            )

    # ==================================================
    # Build + Save
    # ==================================================

    def build_and_save(
        self,
        chunks: list[Chunk],
    ) -> None:
        """
        Build BM25 index and persist it.

        This method is kept for compatibility with existing code.
        """

        self.build(chunks)

        self.save()

    # ==================================================
    # Upsert Contract
    # ==================================================

    def upsert_contract(
        self,
        chunks: list[Chunk],
        contract_id: str,
    ) -> None:
        """
        Add or replace all chunks belonging to one contract.

        Existing chunks with the same contract_id are removed.

        Other contracts remain in the shared BM25 index.
        """

        if not contract_id:
            raise ValueError(
                "contract_id is required."
            )

        if not chunks:
            raise ValueError(
                "Cannot index empty contract chunks."
            )

        # ==============================================
        # Load existing index if available
        # ==============================================

        if self.index_path.exists():
            self.load()

        # ==============================================
        # Remove old chunks of this contract
        # ==============================================

        remaining_chunks = [
            chunk
            for chunk in self.chunks
            if chunk.metadata.contract_id != contract_id
        ]

        # ==============================================
        # Add new chunks
        # ==============================================

        combined_chunks = (
            remaining_chunks
            + list(chunks)
        )

        # ==============================================
        # Rebuild shared BM25
        # ==============================================

        self.build(
            combined_chunks
        )

        self.save()

    # ==================================================
    # Load
    # ==================================================

    def load(self) -> None:
        """
        Load persistent BM25 index.

        Backward compatibility:
        Older BM25 indexes may contain ChunkMetadata
        objects created before contract_id was added.
        """

        if not self.index_path.exists():
            raise FileNotFoundError(
                f"BM25 index not found: "
                f"{self.index_path}"
            )

        with open(
            self.index_path,
            "rb",
        ) as file:

            data = pickle.load(file)

        self.chunks = data["chunks"]

        # ==============================================
        # Backward compatibility
        # ==============================================

        for chunk in self.chunks:

            metadata = chunk.metadata

            if not hasattr(
                metadata,
                "contract_id",
            ):
                metadata.contract_id = None

        self.tokenized_corpus = (
            data["tokenized_corpus"]
        )

        self.bm25 = data["bm25"]

    # ==================================================
    # Build or Load
    # ==================================================

    def build_or_load(
        self,
        chunks: list[Chunk] | None = None,
    ) -> None:
        """
        Load existing index if available.

        Otherwise build and save a new index.
        """

        if self.index_path.exists():
            self.load()
            return

        if chunks is None:
            raise ValueError(
                "No existing BM25 index and "
                "no chunks were provided."
            )

        self.build_and_save(chunks)

    # ==================================================
    # Properties
    # ==================================================

    @property
    def size(self) -> int:
        return len(self.chunks)

    @property
    def is_ready(self) -> bool:
        return self.bm25 is not None