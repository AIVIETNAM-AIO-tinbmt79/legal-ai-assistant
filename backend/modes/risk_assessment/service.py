from chunking.chunk_models import Chunk

from indexing.bm25_indexer import BM25Indexer

from .chunker import convert_chunks
from .schemas import FinalRiskAssessment
from .workflow import build_risk_assessment_graph


class RiskService:
    def __init__(
        self,
        bm25_indexer=None,
    ):
        self.bm25_indexer = (
            bm25_indexer
            or BM25Indexer()
        )

        self.graph = (
            build_risk_assessment_graph()
        )

    def get_contract_chunks(
        self,
        contract_id: str,
    ) -> list[Chunk]:
        if not contract_id:
            raise ValueError(
                "contract_id is required."
            )

        self.bm25_indexer.load()

        chunks = [
            chunk
            for chunk in self.bm25_indexer.chunks
            if chunk.metadata.contract_id
            == contract_id
        ]

        if not chunks:
            raise ValueError(
                f"No chunks found for contract: {contract_id}"
            )

        return chunks

    def assess(
        self,
        contract_id: str,
    ) -> FinalRiskAssessment:
        chunks = self.get_contract_chunks(
            contract_id
        )

        contract_chunks = convert_chunks(
            chunks
        )

        final_state = self.graph.invoke(
            {
                "chunks": contract_chunks,
            }
        )

        result = final_state.get(
            "final_assessment"
        )

        if result is None:
            raise RuntimeError(
                "Risk assessment did not produce "
                "a final assessment."
            )

        return result
