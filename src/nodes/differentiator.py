"""差异比对节点 (Differentiator Node).

负责对比测试前后的环境快照，提取出状态的增量变化。
"""
from src.state import PipelineState

def diff_snapshot(state: PipelineState) -> dict:
    """状态对冲与快照对比。
    
    对比 state 里的 pre_snapshot 与 post_snapshot，计算并提取“增量变化”。
    这里使用了简单易懂的对比方法，过滤掉没有变化的字段，
    生成高信息密度的纯文本，非常适合用来节约大模型的 Token。
    """
    pre = state.get("pre_snapshot", {})
    post = state.get("post_snapshot", {})
    
    diff_results = []
    
    # 1. 寻找新增的或被修改的内容
    for key in post:
        if key not in pre:
            diff_results.append(f"🔴 [新增] {key}:\n{post[key]}")
        elif pre[key] != post[key]:
            diff_results.append(f"🟡 [修改] {key}:\n  之前: {pre[key]}\n  之后: {post[key]}")
            
    # 2. 寻找被删除的内容
    for key in pre:
        if key not in post:
            diff_results.append(f"🟢 [删除] {key}:\n{pre[key]}")
            
    # 3. 聚合为长文本 (如果你需要，也可以返回 JSON)
    if not diff_results:
        final_diff = "未检测到环境状态变化 (No changes detected)."
    else:
        final_diff = "\n\n".join(diff_results)
        
    return {"state_diff": final_diff}
