from __future__ import annotations

import importlib
import inspect
import json
import sys
import time
from pathlib import Path
from typing import Any

# ============================================================
# 1. DÁN ĐƯỜNG DẪN HỢP ĐỒNG MẪU VÀO ĐÂY
# ============================================================
CONTRACT_PATH = r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx"  # Ví dụ: r"D:\legal-ai-assistant\backend\data\sample_contracts\docx_test.docx"

CONTRACT_SUMMARY: str = ""
MODEL_NAME: str | None = None
MAX_LLM_CALLS: int = 120


def _ensure_backend_on_path() -> Path:
    here = Path(__file__).resolve().parent
    backend_dir = here if (here / "modes").exists() else (here / "backend")
    for p in (str(backend_dir), str(backend_dir.parent)):
        if p not in sys.path:
            sys.path.insert(0, p)
    return backend_dir


from pathlib import Path
from typing import Any
from parser.parser_factory import ParserFactory  # type: ignore


def _parse_contract_file(path_obj: Path) -> Any:
    parser = ParserFactory.get_parser(path_obj)
    for method_name in ("parse", "parse_file", "extract_text", "extract", "read"):
        fn = getattr(parser, method_name, None)
        if callable(fn):
            return fn(path_obj) if len(inspect.signature(fn).parameters) > 0 else fn()
    raise AttributeError(
        f"Không tìm thấy method parse trên {type(parser).__name__}: "
        f"{[m for m in dir(parser) if not m.startswith('_')]}"
    )

def _chunk_parsed_content(parsed: Any, path_obj: Path) -> list[Any]:
    """Dùng chunker có sẵn trong package `chunking`."""
    try:
        from chunking.chunker_factory import get_chunker  # type: ignore

        chunker = get_chunker(parsed) if "parsed" in inspect.signature(get_chunker).parameters else get_chunker()
        for method_name in ("chunk", "chunk_text", "chunk_document", "split"):
            fn = getattr(chunker, method_name, None)
            if callable(fn):
                return list(fn(parsed))
    except Exception:
        pass

    for mod_name in ("chunking.chunker_factory", "chunking.article_chunker", "chunking"):
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        for fn_name in ("chunk_text", "chunk_contract", "build_chunks", "create_chunks"):
            fn = getattr(mod, fn_name, None)
            if callable(fn):
                sig = inspect.signature(fn)
                params = list(sig.parameters.keys())
                if isinstance(parsed, dict):
                    text = parsed.get("text") or parsed.get("content") or str(parsed)
                else:
                    text = parsed
                if params:
                    return list(fn(text))
                return list(fn())

    raise RuntimeError(
        "Không gọi được chunker từ package `chunking`. "
        "Kiểm tra hàm/factory trong `chunking/chunker_factory.py`."
    )


def main() -> None:
    _ensure_backend_on_path()

    raw_path = (sys.argv[1] if len(sys.argv) > 1 else CONTRACT_PATH).strip().strip('"').strip("'")
    if not raw_path:
        raise ValueError("Chưa dán đường dẫn hợp đồng vào CONTRACT_PATH.")

    path_obj = Path(raw_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path_obj}")

    from modes.risk_assessment.service import assess_contract_risks  # type: ignore

    t0 = time.perf_counter()
    parsed = _parse_contract_file(path_obj)
    chunks = _chunk_parsed_content(parsed, path_obj)
    print(f"[1/2 PARSE+CHUNK] {len(chunks)} chunks ({time.perf_counter() - t0:.2f}s)")

    t1 = time.perf_counter()
    assessment = assess_contract_risks(
        chunks=chunks,
        contract_summary=CONTRACT_SUMMARY,
        model_name=MODEL_NAME,
        max_llm_calls=MAX_LLM_CALLS,
    )
    print(f"[2/2 ASSESS] {time.perf_counter() - t1:.2f}s\n")

    output = assessment.model_dump() if hasattr(assessment, "model_dump") else assessment
    print("=== SUMMARY ===")
    print(f"risk_level : {output.get('risk_level')}")
    print(f"summary    : {output.get('summary')}")
    print(f"issues     : {len(output.get('issues') or [])}")
    print(f"conflicts  : {len(output.get('cross_clause_conflicts') or [])}\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()