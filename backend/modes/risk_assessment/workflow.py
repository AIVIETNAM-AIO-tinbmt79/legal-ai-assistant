from langgraph.graph import StateGraph, START, END

from .nodes import (
    build_final_assessment_node,
    create_batches_node,
    create_global_summary,
    merge_candidates_node,
    run_agent_1_node,
    run_agent_2_node,
    run_agent_3_node,
)
from .schemas import RiskAssessmentState


def route_after_merge(state: RiskAssessmentState) -> str:
    """Skip Agent 3 entirely when both detection agents found no candidates."""
    return (
        "agent_3"
        if state.get("candidate_issues", [])
        else "final_report"
    )


def build_risk_assessment_graph():
    graph = StateGraph(
        RiskAssessmentState
    )

    graph.add_node(
        "create_global_summary",
        create_global_summary,
    )

    graph.add_node(
        "create_batches",
        create_batches_node,
    )

    graph.add_node(
        "agent_1",
        run_agent_1_node,
    )

    graph.add_node(
        "agent_2",
        run_agent_2_node,
    )

    graph.add_node(
        "merge_candidates",
        merge_candidates_node,
    )

    graph.add_node(
        "agent_3",
        run_agent_3_node,
    )

    graph.add_node(
        "final_report",
        build_final_assessment_node,
    )

    graph.add_edge(
        START,
        "create_global_summary",
    )

    graph.add_edge(
        "create_global_summary",
        "create_batches",
    )

    # Hai agent chạy độc lập.
    graph.add_edge(
        "create_batches",
        "agent_1",
    )

    graph.add_edge(
        "create_batches",
        "agent_2",
    )

    # Chỉ merge sau khi cả hai agent hoàn thành.
    graph.add_edge(
        ["agent_1", "agent_2"],
        "merge_candidates",
    )

    # Early exit: an empty candidate list means neither Agent 1 nor Agent 2
    # identified a risk. Do not invoke Agent 3 or any legal/Neo4j tool.
    graph.add_conditional_edges(
        "merge_candidates",
        route_after_merge,
        {
            "agent_3": "agent_3",
            "final_report": "final_report",
        },
    )

    graph.add_edge(
        "agent_3",
        "final_report",
    )

    graph.add_edge(
        "final_report",
        END,
    )

    return graph.compile()
