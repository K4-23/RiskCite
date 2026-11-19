# 管线状态字段声明
from typing import TypedDict


class PipelineState(TypedDict, total=False):
    # 评估输入
    run_id: str
    company_name: str
    material_text: str
    llm_mode: str            # "llm" | "rule-fallback"
    degradation: list[str]   # 降级原因

    # 入口分析产出
    channels: list[str]      # 风险域 id 列表
    profile: dict            # 企业画像

    # 各节点产出
    compliance_results: list[dict]  # 违法情形核查结果
    channel_evidence: dict          # 风险域证据
    drafts: list[dict]              # 草案
    verdicts: list[dict]            # 复核结论
    findings: list[dict]            # 发现单
    cases: list[dict]               # 案例对照
    followups: list[dict]           # 追问清单
    report_md: str                  # 报告 Markdown
