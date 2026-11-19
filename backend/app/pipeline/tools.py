"""风险域分析用到的工具定义。"""

SEARCH_TOOL_NAME = "search_evidence"

SEARCH_EVIDENCE_TOOL = {
    "type": "function",
    "function": {
        "name": SEARCH_TOOL_NAME,
        "description": (
            "检索法规与标准原文。仅当现有证据不足以支撑结论时调用；"
            "检索范围由当前风险领域固定，调用方不需要也不能指定领域。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "中文检索词，具体到风险点或合规要求，例如“数据出境 安全评估”",
                }
            },
            "required": ["query"],
        },
    },
}
