from llm.llm_factory import LLMFactory
from retrieval.hybrid_retriever import HybridRetriever
from reranking.reranker_factory import RerankerFactory


class AIComponents:
    def __init__(self):
        print("Dang khoi tao cac thanh phan AI...")

        self.retriever = HybridRetriever()
        self.reranker = RerankerFactory.create()
        self.llm = LLMFactory.create()

        print("Khoi tao cac thanh phan AI thanh cong!")