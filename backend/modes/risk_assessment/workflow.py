from __future__ import annotations

from functools import lru_cache
from langgraph.graph import END, START, StateGraph

from .nodes import (
    make_batch_agent_node,
    merge_and_split_node,
    prepare_batches_node,
    synthesize_report_node,
    verify_and_audit_node,
)
from .schemas import RiskAssessmentState


def build_risk_assessment_graph():
    graph = StateGraph(RiskAssessmentState)

    graph.add_node("prepare_batches", prepare_batches_node)
    graph.add_node("agent_1", make_batch_agent_node("agent_1"))
    graph.add_node("agent_2", make_batch_agent_node("agent_2"))
    graph.add_node("merge_and_split", merge_and_split_node)
    graph.add_node("verify_and_audit", verify_and_audit_node)
    graph.add_node("synthesize_report", synthesize_report_node)

    graph.add_edge(START, "prepare_batches")
    graph.add_edge("prepare_batches", "agent_1")
    graph.add_edge("prepare_batches", "agent_2")
    graph.add_edge("agent_1", "merge_and_split")
    graph.add_edge("agent_2", "merge_and_split")
    graph.add_edge("merge_and_split", "verify_and_audit")
    graph.add_edge("verify_and_audit", "synthesize_report")
    graph.add_edge("synthesize_report", END)

    return graph.compile()


@lru_cache(maxsize=1)
def get_risk_assessment_graph():
    return build_risk_assessment_graph()