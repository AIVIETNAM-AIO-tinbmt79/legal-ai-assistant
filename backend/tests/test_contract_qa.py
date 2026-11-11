from pathlib import Path
from uuid import uuid4
import shutil
import sys
import traceback
from modes.contract_qa.workflow import build_qa_chain
# =========================================================
# 1. IMPORT PARSER
# =========================================================

from parser.base_parser import BaseParser
from parser.pdf_parser import PDFParser
from parser.docx_parser import DocxParser
from parser.txt_parser import TxtParser
from parser.exceptions import UnsupportedFileTypeError


class ParserFactory:
    _PARSERS = {
        ".pdf": PDFParser,
        ".docx": DocxParser,
        ".txt": TxtParser,
    }

    @classmethod
    def get_parser(cls, file_path: Path) -> BaseParser:
        extension = file_path.suffix.lower()
        parser_class = cls._PARSERS.get(extension)

        if parser_class is None:
            raise UnsupportedFileTypeError(
                f"Unsupported file type: {extension}"
            )

        return parser_class()


# =========================================================
# 2. CONFIG
# =========================================================

CONTRACT_PATH = Path(
    r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx"
)

# Đưa backend vào Python path
BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# =========================================================
# 3. ĐỌC HỢP ĐỒNG
# =========================================================

def read_contract(file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy hợp đồng: {file_path}"
        )

    parser = ParserFactory.get_parser(file_path)

    # Giả định parser có phương thức parse(file_path).
    # Nếu BaseParser của bạn dùng tên phương thức khác,
    # hãy sửa đúng tại đây.
    result = parser.parse(file_path)

    if isinstance(result, str):
        text = result
    elif isinstance(result, dict):
        text = (
            result.get("text")
            or result.get("content")
            or result.get("full_text")
        )
    else:
        text = (
            getattr(result, "text", None)
            or getattr(result, "content", None)
            or getattr(result, "full_text", None)
        )

    if not text:
        raise ValueError(
            "Parser không trả về nội dung văn bản hợp đồng."
        )

    return text


# =========================================================
# 4. INDEX HỢP ĐỒNG
# =========================================================

def index_contract(file_path: Path):
    from config.settings import settings
    from indexing.document_indexer import DocumentIndexer

    contract_id = f"test_{uuid4().hex[:12]}"

    contract_dir = settings.DATA_DIR / "contracts"
    contract_dir.mkdir(parents=True, exist_ok=True)

    stored_path = contract_dir / (
        f"{contract_id}{file_path.suffix.lower()}"
    )

    shutil.copy2(file_path, stored_path)

    indexer = DocumentIndexer()

    indexer.index(
        file_path=stored_path,
        contract_id=contract_id,
    )

    print(f"\nĐã index hợp đồng.")
    print(f"Contract ID: {contract_id}")

    return contract_id, stored_path


# =========================================================
# 5. CONTRACT QA
# =========================================================

def build_contract_qa_dependencies():
    from retrieval.hybrid_retriever import HybridRetriever
    from reranking.reranker_factory import RerankerFactory
    from llm.llm_factory import LLMFactory

    # Khởi tạo Hybrid Retriever
    retriever = HybridRetriever()

    # Khởi tạo Reranker thông qua Factory
    reranker = RerankerFactory.create()

    # Khởi tạo LLM thông qua Factory
    llm = LLMFactory.create(provider="openrouter")

    return retriever, reranker, llm

def debug_retrieval(
    retriever,
    reranker,
    query: str,
    contract_id: str,
    retrieval_top_k: int = 20,
    reranker_top_k: int = 5,
):
    # ==========================================
    # 1. Hybrid Retrieval
    # ==========================================

    retrieved_results = retriever.retrieve(
        query=query,
        top_k=retrieval_top_k,
        contract_id=contract_id,
    )

    print("\n" + "=" * 70)
    print("HYBRID RETRIEVAL")
    print("=" * 70)
    print(f"Retrieved: {len(retrieved_results)} chunks")

    for i, result in enumerate(retrieved_results, 1):
        print(f"\n[{i}] Hybrid score: {result.score:.4f}")
        print(f"Chunk ID: {result.chunk.id}")
        print(result.chunk.text[:500])

    # ==========================================
    # 2. Cross-Encoder Reranking
    # ==========================================

    reranked_results = reranker.rerank(
        query=query,
        results=retrieved_results,
        top_k=reranker_top_k,
    )

    print("\n" + "=" * 70)
    print("CROSS-ENCODER RERANKING")
    print("=" * 70)
    print(f"Reranked: {len(reranked_results)} chunks")

    for i, result in enumerate(reranked_results, 1):
        print(f"\n[{i}] Reranker score: {result.score:.4f}")
        print(f"Chunk ID: {result.chunk.id}")
        print(result.chunk.text[:1000])

    return reranked_results

def run_contract_qa(contract_id: str):
    retriever, reranker, llm = build_contract_qa_dependencies()

    qa_chain = build_qa_chain(
        retriever=retriever,
        reranker=reranker,
        llm=llm,
        retrieval_top_k=20,
        reranker_top_k=5,
        max_context_chars=20000,
    )

    print("\n========== CONTRACT QA ==========")
    print("Nhập 'exit' để thoát.")
    print("Nhập câu hỏi bắt đầu bằng /debug để xem chunks.")

    while True:
        query = input("\nCâu hỏi: ").strip()

        if query.lower() in {"exit", "quit", "q"}:
            break

        if not query:
            continue

        if query.startswith("/debug "):
            actual_query = query[7:].strip()

            debug_results = debug_retrieval(
        retriever=retriever,
        reranker=reranker,
        query=query,
        contract_id=contract_id,
        retrieval_top_k=20,
        reranker_top_k=5,
    )

            continue

        result = qa_chain.run(
            query=query,
            contract_id=contract_id,
        )

        answer = (
            result.get("answer", "")
            if isinstance(result, dict)
            else getattr(result, "answer", "")
        )

        print("\n========== ANSWER ==========")
        print(answer or "Không tạo được câu trả lời.")

# =========================================================
# 6. RISK ASSESSMENT
# =========================================================

def run_risk_assessment(contract_id: str):
    from modes.risk_assessment.service import RiskService

    print("\nĐang phân tích rủi ro hợp đồng...")

    service = RiskService()
    result = service.assess(contract_id)

    print("\n========== RISK ASSESSMENT ==========")

    print("\nRisk level:")
    print(result.risk_level)

    print("\nSummary:")
    print(result.summary)

    print("\nIssues:")
    for index, issue in enumerate(result.issues, 1):
        print(f"\n[{index}]")
        print(issue)

    print("\nRecommendations:")
    for index, recommendation in enumerate(
        result.recommendations, 1
    ):
        print(f"{index}. {recommendation}")


# =========================================================
# 7. MENU
# =========================================================

def main():
    print("=" * 55)
    print("          LEGAL AI - CONTRACT TEST")
    print("=" * 55)

    print("\n1. Contract QA")
    print("2. Risk Assessment")
    print("0. Exit")

    choice = input("\nChọn chức năng: ").strip()

    if choice == "0":
        return

    if choice not in {"1", "2"}:
        print("Lựa chọn không hợp lệ.")
        return

    try:
        print("\nĐang đọc hợp đồng...")

        contract_text = read_contract(CONTRACT_PATH)

        print("Đọc hợp đồng thành công.")
        print(f"Số ký tự: {len(contract_text):,}")

        # Index để hai mode sử dụng chung contract_id.
        contract_id, stored_path = index_contract(
            CONTRACT_PATH
        )

        if choice == "1":
            run_contract_qa(contract_id)

        elif choice == "2":
            run_risk_assessment(contract_id)

    except Exception as error:
        print("\nĐÃ XẢY RA LỖI:")
        print(error)
        traceback.print_exc()


if __name__ == "__main__":
    main()