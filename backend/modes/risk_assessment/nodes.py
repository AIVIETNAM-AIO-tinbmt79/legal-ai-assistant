from .agent import (
    merge_agent_results,
    run_agent_1,
    run_agent_2,
    run_agent_3,
)
from .chunker import create_batches
from .schemas import (
    AgentTrace,
    FinalRiskAssessment,
    RiskAssessmentState,
)


def create_global_summary(
    state: RiskAssessmentState,
):
    chunks = state.get("chunks", [])

    articles = {
        chunk.article
        for chunk in chunks
        if chunk.article
    }

    summary = (
        f"Hợp đồng gồm {len(chunks)} chunk, "
        f"thuộc {len(articles)} điều khác nhau."
    )

    return {
        "contract_summary": summary,
    }


def create_batches_node(
    state: RiskAssessmentState,
):
    batches = create_batches(
        state.get("chunks", [])
    )

    return {
        "batches": batches,
    }


def run_agent_1_node(
    state: RiskAssessmentState,
):
    results = run_agent_1(
        state.get("batches", [])
    )

    return {
        "agent_1_results": results,
    }


def run_agent_2_node(
    state: RiskAssessmentState,
):
    results = run_agent_2(
        state.get("batches", [])
    )

    return {
        "agent_2_results": results,
    }


def merge_candidates_node(
    state: RiskAssessmentState,
):
    issues = merge_agent_results(
        state.get("agent_1_results", []),
        state.get("agent_2_results", []),
    )

    return {
        "candidate_issues": issues,
    }


def run_agent_3_node(
    state: RiskAssessmentState,
):
    trace = []

    verified = run_agent_3(
        issues=state.get("candidate_issues", []),
        contract_chunks=state.get("chunks", []),
        trace=trace,
    )

    return {
        "verified_issues": verified,
        "agent_trace": [
            AgentTrace.model_validate(item)
            for item in trace
        ],
    }



def build_final_assessment_node(
    state: RiskAssessmentState,
):
    issues = state.get("verified_issues", [])

    if not issues:
        candidates = state.get("candidate_issues", [])

        if not candidates:
            summary = (
                "Qua quá trình rà soát nội dung hợp đồng, hệ thống "
                "chưa ghi nhận vấn đề cụ thể có dấu hiệu rủi ro pháp lý "
                "trong phạm vi đánh giá hiện tại. "
                "Kết quả này chưa đồng nghĩa với việc hợp đồng "
                "hoàn toàn không có rủi ro pháp lý."
            )
        else:
            summary = (
                "Qua quá trình rà soát và đối chiếu với các căn cứ "
                "pháp luật truy xuất được, hệ thống hiện chưa tìm thấy "
                "đủ cơ sở để xác định điều khoản hợp đồng có mâu thuẫn "
                "trực tiếp với quy định pháp luật. "
                "Quý khách nên cân nhắc rà soát thêm các điều khoản "
                "liên quan để bảo đảm quyền và lợi ích hợp pháp của mình."
            )

        result = FinalRiskAssessment(
            risk_level="low",
            summary=summary,
            issues=[],
            recommendations=[],
        )

        return {
            "final_assessment": result,
        }

    highest = max(
        (
            {"low": 1, "medium": 2, "high": 3}[issue.severity]
            for issue in issues
        ),
        default=1,
    )

    risk_level = {
        1: "low",
        2: "medium",
        3: "high",
    }[highest]

    recommendations = [
        (
            f"Đề nghị rà soát điều khoản liên quan đến "
            f"{issue.risk_type} và cân nhắc điều chỉnh phù hợp "
            f"trên cơ sở các căn cứ pháp luật đã được đối chiếu."
        )
        for issue in issues
    ]

    result = FinalRiskAssessment(
        risk_level=risk_level,
        summary=(
            f"Qua quá trình rà soát, hệ thống ghi nhận "
            f"{len(issues)} vấn đề có dấu hiệu rủi ro pháp lý "
            f"đã được đối chiếu với các căn cứ pháp luật liên quan."
        ),
        issues=issues,
        recommendations=recommendations,
    )

    return {
        "final_assessment": result,
    }
