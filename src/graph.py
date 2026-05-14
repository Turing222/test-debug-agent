"""Graph orchestration. 连接测试执行、旁路观测、门控和报告节点。"""

from langgraph.graph import END, StateGraph

from src.nodes.analyzer import evaluate_or_analyze, generate_report
from src.nodes.differentiator import diff_snapshot
from src.nodes.gatekeeper import rule_gate
from src.nodes.lifecycle import finish, load_case, run_test
from src.nodes.observer import post_observe, pre_observe
from src.state import PipelineState


def check_gate_decision(state: PipelineState) -> str:
    """Route by gate decision."""
    if state.get("gate_decision") == "FAIL":
        return "evaluate_or_analyze"
    return "finish"


def build_graph():
    """Build the executable graph."""
    workflow = StateGraph(PipelineState)

    workflow.add_node("load_case", load_case)
    workflow.add_node("pre_observe", pre_observe)
    workflow.add_node("run_test", run_test)
    workflow.add_node("post_observe", post_observe)
    workflow.add_node("diff_snapshot", diff_snapshot)
    workflow.add_node("rule_gate", rule_gate)
    workflow.add_node("evaluate_or_analyze", evaluate_or_analyze)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("finish", finish)

    workflow.add_edge("load_case", "pre_observe")
    workflow.add_edge("pre_observe", "run_test")
    workflow.add_edge("run_test", "post_observe")
    workflow.add_edge("post_observe", "diff_snapshot")
    workflow.add_edge("diff_snapshot", "rule_gate")

    workflow.add_conditional_edges(
        "rule_gate",
        check_gate_decision,
        {
            "evaluate_or_analyze": "evaluate_or_analyze",
            "finish": "finish",
        },
    )

    workflow.add_edge("evaluate_or_analyze", "generate_report")
    workflow.add_edge("generate_report", "finish")
    workflow.add_edge("finish", END)
    workflow.set_entry_point("load_case")

    return workflow.compile()
