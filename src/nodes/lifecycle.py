"""生命周期节点 (Lifecycle Nodes).

负责测试用例的加载、测试执行及流程结束等核心生命周期环节。
"""
from src.state import PipelineState

def load_case(state: PipelineState) -> dict:
    """模拟加载测试用例。"""
    # 真实场景可能是从列表弹出，这里直接写死一个假用例
    case_name = state.get("test_case_name", "test_api_auth")
    print(f"--> [load_case] 准备执行用例: {case_name}")
    return {"test_case_name": case_name}

def run_test(state: PipelineState) -> dict:
    """模拟执行测试。"""
    # 真实场景会执行 subprocess.run(["pytest", ...])
    print(f"--> [run_test] 正在跑测试脚本...")
    # 我们故意模拟一个报错的测试，为了让它走到 analyzer 节点
    test_result = {
        "exit_code": 1,
        "stdout": "Running... FAIL",
        "stderr": "AssertionError: Expected 200, got 500"
    }
    return {"test_result": test_result}

def finish(state: PipelineState) -> dict:
    """流程结束节点。"""
    print("--> [finish] 整个排障流水线工作结束！")
    return {}
