"""观测节点 (Observer Nodes).

负责在测试执行前后调用 MCP snapshot 记录系统环境状态（数据库、缓存、日志等）。
"""
from src.state import PipelineState

def pre_observe(state: PipelineState) -> dict:
    """测试前观测节点。"""
    print("--> [pre_observe] 调用 MCP 获取测试前的 DB/Redis 快照...")
    pre_snap = {
        "db_users_count": 10,
        "redis_keys_count": 5
    }
    return {"pre_snapshot": pre_snap}

def post_observe(state: PipelineState) -> dict:
    """测试后观测节点。"""
    print("--> [post_observe] 调用 MCP 获取测试后的 DB/Redis 快照...")
    post_snap = {
        "db_users_count": 10,  # 没变
        "redis_keys_count": 6, # 注意：多了一个 key
        "latest_error_log": "TimeoutError in API auth module" # 新增报错日志
    }
    return {"post_snapshot": post_snap}
