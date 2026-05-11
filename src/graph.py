"""核心图流转编排 (Graph Orchestration).

这是整个系统的大脑。在这里，我们将各个节点 (Nodes) 连接起来，
并通过条件边 (Conditional Edges) 实现控制流（如异常时的条件分支）以及人机协同（中断挂起）。
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import PipelineState
from src.nodes.lifecycle import load_case, run_test, finish
from src.nodes.observer import pre_observe, post_observe
from src.nodes.differentiator import diff_snapshot
from src.nodes.gatekeeper import rule_gate
from src.nodes.analyzer import evaluate_or_analyze, generate_report


def check_gate_decision(state: PipelineState) -> str:
    """路由函数：根据 rule_gate 的结果决定下一步去哪里。"""
    if state.get("gate_decision") == "FAIL":
        return "evaluate_or_analyze"
    
    # 如果是 PASS，不需要分析，直接走向结束（或者你可以改回 load_case 跑下一个）
    return "finish"


def build_graph():
    """构建状态图。这就是 LangGraph 的核心玩法。"""
    
    # 1. 初始化图对象，明确告诉它我们的全局状态是什么格式
    workflow = StateGraph(PipelineState)

    # 2. 注册所有的节点 (把函数绑定到节点名称上)
    workflow.add_node("load_case", load_case)
    workflow.add_node("pre_observe", pre_observe)
    workflow.add_node("run_test", run_test)
    workflow.add_node("post_observe", post_observe)
    workflow.add_node("diff_snapshot", diff_snapshot)
    workflow.add_node("rule_gate", rule_gate)
    workflow.add_node("evaluate_or_analyze", evaluate_or_analyze)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("finish", finish)

    # 3. 编排固定的单向执行流 (这部分是线性的)
    workflow.add_edge("load_case", "pre_observe")
    workflow.add_edge("pre_observe", "run_test")
    workflow.add_edge("run_test", "post_observe")
    workflow.add_edge("post_observe", "diff_snapshot")
    workflow.add_edge("diff_snapshot", "rule_gate")

    # 4. 编排条件路由 (这部分会根据判定结果走分岔路)
    workflow.add_conditional_edges(
        "rule_gate",             # 从 rule_gate 出来后进行路由判断
        check_gate_decision,     # 执行路由函数
        {
            # 函数返回值映射到具体的节点
            "evaluate_or_analyze": "evaluate_or_analyze", 
            "finish": "finish"                            
        }
    )

    # 失败分支后续走向
    workflow.add_edge("evaluate_or_analyze", "generate_report")
    workflow.add_edge("generate_report", "finish")
    
    # 收尾
    workflow.add_edge("finish", END)

    # 5. 设置流转的起点
    workflow.set_entry_point("load_case")

    # 6. 编译图，并设置在断点处挂起 (这就是 Human Decision 机制的核心)
    # 使用内存持久化，保证能在暂停后接续执行
    memory = MemorySaver()
    app = workflow.compile(
        checkpointer=memory,
        # 魔法所在：设置在执行 finish 之前暂停，这样人类就能查看 report 并决定下一步
        interrupt_before=["finish"] 
    )
    
    return app
