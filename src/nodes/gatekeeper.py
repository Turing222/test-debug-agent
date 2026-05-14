"""Gatekeeper node. 用轻量规则判断是否需要生成失败诊断报告。"""

from src.state import PipelineState


def rule_gate(state: PipelineState) -> dict[str, str]:
    """Route failed pytest or failed observation into report generation."""
    print("--> [rule_gate] checking result")
    test_result = state.get("test_result", {})
    timed_out = bool(test_result.get("timed_out", False))

    if timed_out:
        print("    [Gate FAIL] pytest timed out")
        return {"gate_decision": "FAIL"}

    if test_result.get("exit_code", 0) != 0:
        print("    [Gate FAIL] pytest failed")
        return {"gate_decision": "FAIL"}

    observability_status = state.get("observability_status", "")
    if observability_status == "error_detected":
        print("    [Gate FAIL] sidecar logs contain errors")
        return {"gate_decision": "FAIL"}

    if state.get("mcp_error"):
        print("    [Gate FAIL] sidecar MCP observation failed")
        return {"gate_decision": "FAIL"}

    print("    [Gate PASS] pytest passed")
    return {"gate_decision": "PASS"}
