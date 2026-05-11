"""规则门控节点 (Gatekeeper Node).

通过轻量级、无 LLM 的硬编码规则，快速过滤正常的测试，节约大模型分析成本。
"""
from src.state import PipelineState

def rule_gate(state: PipelineState) -> dict:
    """规则门控判断。"""
    print("--> [rule_gate] 规则引擎校验中...")
    test_result = state.get("test_result", {})
    state_diff = state.get("state_diff", "")
    
    # 规则 1：如果测试脚本直接报非零退出码，拦截去排查
    if test_result.get("exit_code", 0) != 0:
        print("    [Gate FAIL] 测试断言失败！导向排障流。")
        return {"gate_decision": "FAIL"}
        
    # 规则 2：如果 Diff 中看到了 Error 日志，哪怕测试是绿的也要查（抓脏数据）
    if "Error" in state_diff or "Exception" in state_diff:
        print("    [Gate FAIL] 测试虽过，但基建爆出 Error！导向排障流。")
        return {"gate_decision": "FAIL"}
        
    print("    [Gate PASS] 一切正常，放行。")
    return {"gate_decision": "PASS"}
