"""分析与报告节点 (Analyzer Nodes).

在规则门控判定异常时，调用大模型进行深度排障推理并生成人类可读报告。
"""
from src.state import PipelineState

def evaluate_or_analyze(state: PipelineState) -> dict:
    """LLM 深度诊断排障。"""
    print("--> [analyzer] 请求大模型进行 Root Cause 诊断...")
    # 真实场景中，这里会调用 LLM，喂入用例名称、stderr 和 state_diff
    mock_analysis = "分析结论：由于 Redis 连接超时 (TimeoutError)，导致鉴权 Token 未被正确清理，发生了死键泄露。"
    return {"analysis_result": mock_analysis}

def generate_report(state: PipelineState) -> dict:
    """生成 Markdown 报告。"""
    print("--> [generate_report] 组装最终排障报告...")
    
    report = f"""# SRE 自动排障诊断报告
    
## 🎯 失败用例
`{state.get('test_case_name')}`

## 💥 脚本报错日志
```text
{state.get('test_result', {}).get('stderr', '无')}
```

## 🔍 环境基建异动 (Snapshot Diff)
```text
{state.get('state_diff')}
```

## 🧠 AI 诊断结论
> {state.get('analysis_result')}
"""
    return {"final_report": report}
