from indexing.document_indexer import DocumentIndexer


class IndexerFactory:

    @staticmethod
    def create(
        indexer_type: str = "document",
        **kwargs,
    ):

        if indexer_type == "document":
            return DocumentIndexer(
                **kwargs
            )

        raise ValueError(
            f"Unsupported indexer type: "
            f"{indexer_type}"
        )