import argparse
import importlib
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime
from functools import wraps
from pathlib import Path


# ============================================================
# 1. LOGGER
# ============================================================

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_PATH = LOG_DIR / f"risk_test_{RUN_ID}.log"
JSON_PATH = LOG_DIR / f"risk_test_{RUN_ID}.json"

logger = logging.getLogger("risk_benchmark")
logger.setLevel(logging.INFO)
logger.handlers.clear()

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def log_info(message):
    logger.info(message)


def rounded(seconds):
    return round(float(seconds), 3)


def count_items(value):
    if value is None:
        return 0

    try:
        return len(value)
    except (TypeError, AttributeError):
        return 0


# ============================================================
# 2. IMPORT MODULE
# ============================================================

from modes.risk_assessment import workflow, agent, legal_tools


def import_symbol(module_names, symbol_name):
    errors = []

    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
            symbol = getattr(module, symbol_name, None)

            if symbol is not None:
                log_info(
                    f"Đã import {symbol_name} từ {module_name}"
                )
                return symbol

        except Exception as exc:
            errors.append(f"{module_name}: {exc}")

    raise ImportError(
        f"Không tìm thấy {symbol_name}. "
        + " | ".join(errors)
    )


AIComponents = import_symbol(
    [
        "core.ai_components",
        "ai_components",
        "components.ai_components",
        "services.ai_components",
        "app.core.ai_components",
    ],
    "AIComponents",
)

RiskService = import_symbol(
    [
        "modes.risk_assessment.service",
        "modes.risk_assessment.risk_service",
        "services.risk_service",
        "risk_service",
    ],
    "RiskService",
)


# ============================================================
# 3. THỐNG KÊ
# ============================================================

stats = {
    "contract_id": None,

    "workflow": {
        "seconds": 0,
        "status": "not_started",
        "error": None,
    },

    "nodes": {},

    "llm": {
        "calls": 0,
        "seconds": 0,
        "errors": 0,
        "calls_detail": [],
    },

    "legal_search": {
        "calls": 0,
        "seconds": 0,
        "errors": 0,
        "references_returned": 0,
        "calls_detail": [],
    },

    "schema_context": {
        "calls": 0,
        "seconds": 0,
        "errors": 0,
        "calls_detail": [],
    },

    "semantic_rerank": {
        "calls": 0,
        "seconds": 0,
        "errors": 0,
        "references_processed": 0,
        "calls_detail": [],
    },

    "legal_search_stages": {},
}


def get_stage(name):
    if name not in stats["legal_search_stages"]:
        stats["legal_search_stages"][name] = {
            "calls": 0,
            "seconds": 0,
            "errors": 0,
            "calls_detail": [],
        }

    return stats["legal_search_stages"][name]


# ============================================================
# 4. ĐO THỜI GIAN NODE
# ============================================================

def instrument_node(module, function_name):
    original = getattr(module, function_name, None)

    if not callable(original):
        log_info(f"[SKIP NODE] Không có {function_name}")
        return

    if getattr(original, "_benchmark_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args, **kwargs):
        started = time.perf_counter()

        item = stats["nodes"].setdefault(
            function_name,
            {
                "calls": 0,
                "seconds": 0,
                "errors": 0,
            },
        )

        log_info(f"[NODE START] {function_name}")

        try:
            result = original(*args, **kwargs)
            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed

            log_info(
                f"[NODE END] {function_name} "
                f"| {elapsed:.2f} giây"
            )

            return result

        except Exception:
            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed
            item["errors"] += 1

            logger.exception(f"[NODE ERROR] {function_name}")
            raise

    wrapper._benchmark_wrapped = True
    setattr(module, function_name, wrapper)


# ============================================================
# 5. ĐO CALL LLM
# ============================================================

def instrument_call_llm(module):
    original = getattr(module, "call_llm", None)

    if not callable(original):
        log_info("[SKIP] Không tìm thấy call_llm")
        return

    if getattr(original, "_benchmark_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args, **kwargs):
        item = stats["llm"]
        call_number = item["calls"] + 1

        started = time.perf_counter()

        prompt = kwargs.get("prompt")

        if prompt is None:
            prompt = next(
                (
                    arg for arg in args
                    if isinstance(arg, str)
                ),
                "",
            )

        log_info(f"[LLM START] call={call_number}")

        try:
            result = original(*args, **kwargs)

            elapsed = time.perf_counter() - started

            response = (
                result if isinstance(result, str)
                else str(result)
            )

            item["calls"] += 1
            item["seconds"] += elapsed

            item["calls_detail"].append({
                "call": call_number,
                "seconds": rounded(elapsed),
                "prompt_chars": len(str(prompt or "")),
                "response_chars": len(response),
                "status": "success",
            })

            log_info(
                f"[LLM] call_llm | {elapsed:.2f} giây "
                f"| prompt={len(str(prompt or ''))} chars "
                f"| response={len(response)} chars"
            )

            return result

        except Exception as exc:
            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed
            item["errors"] += 1

            item["calls_detail"].append({
                "call": call_number,
                "seconds": rounded(elapsed),
                "status": "error",
                "error": str(exc),
            })

            logger.exception("[LLM ERROR]")
            raise

    wrapper._benchmark_wrapped = True
    module.call_llm = wrapper


# ============================================================
# 6. ĐO TỔNG LEGAL_SEARCH
# ============================================================

def instrument_legal_search(module):
    original = getattr(module, "legal_search", None)

    if not callable(original):
        log_info("[SKIP] Không tìm thấy legal_search")
        return

    if getattr(original, "_benchmark_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args, **kwargs):
        item = stats["legal_search"]
        call_number = item["calls"] + 1

        started = time.perf_counter()

        query = kwargs.get("query")

        if query is None and args:
            query = args[0]

        query = str(query or "")

        log_info(
            f"[LEGAL SEARCH START] call={call_number} "
            f"| query={query[:200]}"
        )

        try:
            result = original(*args, **kwargs)

            elapsed = time.perf_counter() - started
            ref_count = count_items(result)

            item["calls"] += 1
            item["seconds"] += elapsed
            item["references_returned"] += ref_count

            item["calls_detail"].append({
                "call": call_number,
                "query": query,
                "seconds": rounded(elapsed),
                "references_returned": ref_count,
                "status": "success",
            })

            log_info(
                f"[LEGAL SEARCH] call={call_number} "
                f"| {elapsed:.2f} giây "
                f"| references={ref_count}"
            )

            return result

        except Exception as exc:
            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed
            item["errors"] += 1

            item["calls_detail"].append({
                "call": call_number,
                "query": query,
                "seconds": rounded(elapsed),
                "status": "error",
                "error": str(exc),
            })

            logger.exception("[LEGAL SEARCH ERROR]")
            raise

    wrapper._benchmark_wrapped = True
    module.legal_search = wrapper


# ============================================================
# 7. ĐO CÁC HÀM NỘI BỘ
# ============================================================

def describe_arguments(function_name, args, kwargs):
    detail = {}

    if function_name == "_semantic_rerank":
        query = (
            args[0] if len(args) > 0
            else kwargs.get("query", "")
        )

        references = (
            args[1] if len(args) > 1
            else kwargs.get("references", [])
        )

        top_k = (
            args[2] if len(args) > 2
            else kwargs.get("top_k")
        )

        detail = {
            "query_chars": len(str(query or "")),
            "candidate_count": count_items(references),
            "top_k": top_k,
        }

    elif function_name == "_lexical_chunk_candidates":
        chunks = (
            args[0] if len(args) > 0
            else kwargs.get("chunks", [])
        )

        phrases = (
            args[1] if len(args) > 1
            else kwargs.get("phrases", [])
        )

        detail = {
            "chunks_count": count_items(chunks),
            "phrases_count": count_items(phrases),
        }

    return detail


def instrument_internal_function(
    module,
    function_name,
    stage_name=None,
):
    original = getattr(module, function_name, None)

    if not callable(original):
        log_info(
            f"[SKIP STAGE] Không có "
            f"{module.__name__}.{function_name}"
        )
        return

    if getattr(original, "_benchmark_wrapped", False):
        return

    stage_name = stage_name or function_name

    @wraps(original)
    def wrapper(*args, **kwargs):
        item = get_stage(stage_name)
        call_number = item["calls"] + 1

        started = time.perf_counter()

        detail = describe_arguments(
            function_name,
            args,
            kwargs,
        )

        try:
            result = original(*args, **kwargs)

            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed

            item["calls_detail"].append({
                "call": call_number,
                "seconds": rounded(elapsed),
                **detail,
                "status": "success",
            })

            detail_text = " | ".join(
                f"{key}={value}"
                for key, value in detail.items()
            )

            log_info(
                f"[LEGAL STAGE] {stage_name} "
                f"| {elapsed:.3f} giây"
                + (f" | {detail_text}" if detail_text else "")
            )

            return result

        except Exception as exc:
            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed
            item["errors"] += 1

            item["calls_detail"].append({
                "call": call_number,
                "seconds": rounded(elapsed),
                **detail,
                "status": "error",
                "error": str(exc),
            })

            logger.exception(
                f"[LEGAL STAGE ERROR] {stage_name}"
            )

            raise

    wrapper._benchmark_wrapped = True
    setattr(module, function_name, wrapper)

    log_info(
        f"[INSTRUMENT] Đã bọc "
        f"{module.__name__}.{function_name}"
    )


# ============================================================
# 8. ĐO RIÊNG SEMANTIC RERANK
# ============================================================

def instrument_semantic_rerank(module):
    original = getattr(module, "_semantic_rerank", None)

    if not callable(original):
        log_info("[SKIP] Không tìm thấy _semantic_rerank")
        return

    if getattr(original, "_benchmark_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args, **kwargs):
        item = stats["semantic_rerank"]
        call_number = item["calls"] + 1

        query = (
            args[0] if len(args) > 0
            else kwargs.get("query", "")
        )

        references = (
            args[1] if len(args) > 1
            else kwargs.get("references", [])
        )

        top_k = (
            args[2] if len(args) > 2
            else kwargs.get("top_k")
        )

        candidate_count = count_items(references)
        started = time.perf_counter()

        try:
            result = original(*args, **kwargs)

            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed
            item["references_processed"] += candidate_count

            item["calls_detail"].append({
                "call": call_number,
                "seconds": rounded(elapsed),
                "candidate_count": candidate_count,
                "top_k": top_k,
                "query_chars": len(str(query or "")),
                "status": "success",
            })

            log_info(
                f"[SEMANTIC RERANK] "
                f"{elapsed:.2f} giây "
                f"| candidates={candidate_count} "
                f"| top_k={top_k}"
            )

            return result

        except Exception as exc:
            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed
            item["errors"] += 1

            item["calls_detail"].append({
                "call": call_number,
                "seconds": rounded(elapsed),
                "candidate_count": candidate_count,
                "top_k": top_k,
                "status": "error",
                "error": str(exc),
            })

            logger.exception("[SEMANTIC RERANK ERROR]")
            raise

    wrapper._benchmark_wrapped = True
    module._semantic_rerank = wrapper


# ============================================================
# 9. ĐO SCHEMA CONTEXT
# ============================================================

def instrument_schema_context(module):
    function_name = "get_graph_schema_context"
    original = getattr(module, function_name, None)

    if not callable(original):
        log_info("[SKIP] Không tìm thấy get_graph_schema_context")
        return

    if getattr(original, "_benchmark_wrapped", False):
        return

    @wraps(original)
    def wrapper(*args, **kwargs):
        item = stats["schema_context"]
        call_number = item["calls"] + 1

        started = time.perf_counter()

        try:
            result = original(*args, **kwargs)

            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed

            item["calls_detail"].append({
                "call": call_number,
                "seconds": rounded(elapsed),
                "status": "success",
            })

            log_info(
                f"[SCHEMA CONTEXT] "
                f"{elapsed:.2f} giây"
            )

            return result

        except Exception as exc:
            elapsed = time.perf_counter() - started

            item["calls"] += 1
            item["seconds"] += elapsed
            item["errors"] += 1

            item["calls_detail"].append({
                "call": call_number,
                "seconds": rounded(elapsed),
                "status": "error",
                "error": str(exc),
            })

            logger.exception("[SCHEMA CONTEXT ERROR]")
            raise

    wrapper._benchmark_wrapped = True
    setattr(module, function_name, wrapper)


# ============================================================
# 10. CÀI INSTRUMENTATION
# ============================================================

def install_instrumentation():
    node_names = [
        "create_global_summary",
        "create_batches_node",
        "run_agent_1_node",
        "run_agent_2_node",
        "merge_candidates_node",
        "run_agent_3_node",
        "build_final_assessment_node",
    ]

    for name in node_names:
        instrument_node(workflow, name)

    instrument_call_llm(agent)
    instrument_legal_search(agent)
    instrument_schema_context(agent)

    # Các hàm có thể tồn tại trong legal_tools.py.
    # Hàm nào không tồn tại sẽ được ghi [SKIP STAGE].
    internal_functions = [
        "_get_superseded_document_ids",
        "_lexical_chunk_candidates",
        "_search_entities_with_driver",
        "_search_relationships_with_driver",
        "_get_cached_graph_schema",
        "_load_chunks",
        "_load_chunks_jsonl",
        "_rank_and_dedupe_references",
        "_dedupe_references",
    ]

    for name in internal_functions:
        instrument_internal_function(
            legal_tools,
            name,
        )

    # Reranker có bộ đếm riêng, không bọc hai lần.
    instrument_semantic_rerank(legal_tools)

    log_info(
        "Đã cài instrumentation cho workflow, LLM, "
        "legal_search và các hàm nội bộ."
    )


# ============================================================
# 11. TỔNG HỢP VÀ LƯU JSON
# ============================================================

def normalize_query(value):
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, dict):
        for key in ("query", "phrase", "text", "search_phrase"):
            result = value.get(key)

            if isinstance(result, str):
                return result.strip()

        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    return str(value).strip() if value is not None else ""


def build_summary():
    query_list = [
        normalize_query(item.get("query"))
        for item in stats["legal_search"]["calls_detail"]
    ]

    query_counts = Counter(
        query for query in query_list if query
    )

    return {
        **stats,
        "duplicate_queries": {
            query: count
            for query, count in query_counts.items()
            if count > 1
        },
        "log_path": str(LOG_PATH),
    }


def print_summary():
    log_info("=" * 70)
    log_info("BENCHMARK SUMMARY")
    log_info("=" * 70)

    log_info(
        f"Workflow: {stats['workflow']['seconds']:.2f}s "
        f"| status={stats['workflow']['status']}"
    )

    for name, item in stats["nodes"].items():
        log_info(
            f"Node {name}: {item['seconds']:.2f}s "
            f"| calls={item['calls']} "
            f"| errors={item['errors']}"
        )

    for key in ("llm", "legal_search", "schema_context"):
        item = stats[key]

        log_info(
            f"{key}: calls={item['calls']} "
            f"| total={item['seconds']:.2f}s "
            f"| errors={item['errors']}"
        )

    rerank = stats["semantic_rerank"]

    log_info(
        f"Semantic rerank: calls={rerank['calls']} "
        f"| total={rerank['seconds']:.2f}s "
        f"| errors={rerank['errors']}"
    )

    for item in rerank["calls_detail"]:
        log_info(
            f"  Rerank #{item['call']}: "
            f"{item['seconds']:.2f}s "
            f"| candidates={item.get('candidate_count')} "
            f"| top_k={item.get('top_k')}"
        )

    log_info("-" * 70)
    log_info("LEGAL SEARCH INTERNAL STAGES")

    stages = sorted(
        stats["legal_search_stages"].items(),
        key=lambda pair: pair[1]["seconds"],
        reverse=True,
    )

    for name, item in stages:
        average = (
            item["seconds"] / item["calls"]
            if item["calls"] else 0
        )

        log_info(
            f"{name}: calls={item['calls']} "
            f"| total={item['seconds']:.3f}s "
            f"| average={average:.3f}s "
            f"| errors={item['errors']}"
        )

        for detail in item["calls_detail"]:
            log_info(
                f"  {name} #{detail['call']}: "
                f"{detail['seconds']:.3f}s "
                f"| status={detail['status']}"
            )

    log_info("=" * 70)


# ============================================================
# 12. MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--contract-id",
        required=True,
        help="ID hợp đồng cần benchmark",
    )

    args = parser.parse_args()

    stats["contract_id"] = args.contract_id

    install_instrumentation()

    try:
        log_info("Đang khởi tạo AIComponents...")

        ai_components = AIComponents()

        set_reranker = getattr(
            legal_tools,
            "set_shared_reranker",
            None,
        )

        if callable(set_reranker):
            set_reranker(
                getattr(ai_components, "reranker", None)
            )
            log_info("Shared reranker đã được đăng ký.")

        service = RiskService()

        started = time.perf_counter()
        stats["workflow"]["status"] = "running"

        result = service.assess(args.contract_id)

        elapsed = time.perf_counter() - started

        stats["workflow"]["seconds"] = rounded(elapsed)
        stats["workflow"]["status"] = "success"

        log_info(
            f"Risk assessment hoàn thành "
            f"| {elapsed:.2f} giây "
            f"| result_type={type(result).__name__}"
        )

    except Exception as exc:
        stats["workflow"]["status"] = "error"
        stats["workflow"]["error"] = str(exc)

        logger.exception("Risk assessment thất bại")
        raise

    finally:
        try:
            set_reranker = getattr(
                legal_tools,
                "set_shared_reranker",
                None,
            )

            if callable(set_reranker):
                set_reranker(None)

        except Exception:
            logger.exception("Lỗi khi clear shared reranker")

        try:
            close_driver = getattr(
                legal_tools,
                "close_neo4j_driver",
                None,
            )

            if callable(close_driver):
                close_driver()

        except Exception:
            logger.exception("Lỗi khi đóng Neo4j driver")

        print_summary()

        with open(JSON_PATH, "w", encoding="utf-8") as file:
            json.dump(
                build_summary(),
                file,
                ensure_ascii=False,
                indent=2,
            )

        log_info(f"Log được lưu tại: {LOG_PATH}")
        log_info(f"JSON được lưu tại: {JSON_PATH}")


if __name__ == "__main__":
    main()