from sentence_transformers import SentenceTransformer

from config.settings import settings

from embeddings.base_embedder import BaseEmbedder


class SentenceTransformerEmbedder(BaseEmbedder):
    """
    Embedding implementation using SentenceTransformer.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ):

        # ==========================================
        # Configuration
        # ==========================================

        self.model_name = (
            model_name
            if model_name is not None
            else settings.EMBEDDING_MODEL
        )

        self.device = (
            device
            if device is not None
            else settings.EMBEDDING_DEVICE
        )

        # ==========================================
        # Load Model
        # ==========================================

        self.model = SentenceTransformer(
            self.model_name,
            device=self.device,
        )


    # ==================================================
    # Dimension
    # ==================================================

    @property
    def dimension(self) -> int:

        return (
            self.model
            .get_sentence_embedding_dimension()
        )


    # ==================================================
    # Embed Single Text
    # ==================================================

    def embed_text(
        self,
        text: str,
    ) -> list[float]:

        if not text or not text.strip():

            return []


        vector = self.model.encode(
            text,
            normalize_embeddings=True,
        )


        return vector.tolist()


    # ==================================================
    # Embed Documents
    # ==================================================

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:

        if not texts:

            return []


        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
        )


        return vectors.tolist()