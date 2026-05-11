"""状态定义 (State Definition).

定义了贯穿整个自动化测试与排障流水线的全局状态。
"""
from typing import TypedDict, Any

class PipelineState(TypedDict):
    """流水线状态。

    流转于整个 LangGraph 各个节点的全局状态，用于保存环境快照、测试结果及排障报告。
    """
    test_case_name: str          # 当前测试用例名称
    
    pre_snapshot: dict[str, Any] # 跑之前的 DB/Redis/Log 状态
    test_result: dict[str, Any]  # 测试本身的执行结果 (stdout, stderr, exit_code)
    post_snapshot: dict[str, Any]# 跑之后的 DB/Redis/Log 状态
    
    state_diff: str              # 前后快照的 Diff 字符串
    
    gate_decision: str           # rule_gate 的判定结果 (PASS / FAIL)
    
    analysis_result: str         # LLM 深度诊断结果
    final_report: str            # 生成的报告 Markdown
