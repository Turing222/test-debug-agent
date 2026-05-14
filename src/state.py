"""Pipeline state definitions. 定义测试执行、旁路观测和报告生成的状态边界。"""

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    """State shared by LangGraph nodes."""

    pytest_target: str
    test_case_name: str
    report_dir: str
    report_path: str | None

    container: str
    log_level: str
    db_query: str
    redis_command: str
    redis_args: str
    redis_db: int

    pre_snapshot: dict[str, Any]
    test_result: dict[str, Any]
    post_snapshot: dict[str, Any]
    state_diff: str

    mcp_snapshot_summary: dict[str, Any] | None
    mcp_snapshot_file: str | None
    mcp_error: dict[str, Any] | None
    observability_status: str
    observability_evidence: str

    gate_decision: str
    analysis_result: str
    final_report: str
