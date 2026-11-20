from datetime import datetime

from ..rules.severity import SURVIVAL_KEYWORDS
from .channels import CHANNELS

DOMAIN_SOURCES = [
    ("技术与研发", "Tyebjee & Bruno (1984)；科技保险研发类险种；贝恩尽调支柱"),
    ("算法与模型", "TC260《人工智能安全治理框架》2.0"),
    ("数据合规与隐私", "《个人信息保护法》《数据安全法》《生成式人工智能服务管理暂行办法》"),
    ("网络安全与系统", "网络安全保险险种；NIST AI RMF"),
    ("知识产权", "知识产权侵权责任保险；贝恩尽调支柱"),
    ("商业化与市场", "Cantamessa et al. (2018)；CB Insights 失败案例统计"),
    ("融资与现金流", "金融监管总局金发〔2024〕2号；CB Insights"),
    ("供应链与地缘", "《出口管制法》《两用物项出口管制条例》；NBER (2023)"),
    ("伦理与治理", "两办《关于加强科技伦理治理的意见》《科技伦理审查办法（试行）》"),
    ("组织与人才", "MacMillan et al. (1985)；CB Insights；人才创业保险"),
]

OBLIGATION_VERDICT_TEXT = {"violation": "违规", "suspect": "疑似", "not_found": "未发现"}

# 附录严重度规则表，关键词取自 severity
SEVERITY_RULES_MD = f"""| 档 | 编号 | 判定条件 |
|---|---|---|
| 高 | SL-1 | 命中违法情形（合规核查判定） |
| 高 | SL-2 | 存在 L1 证据且触及存续类风险 |
| 中 | SL-3 | 存在 L1 或 L2 证据 |
| 低 | SL-4 | 仅 L3（证据不足），标"待核查" |

存续类关键词：{"、".join(SURVIVAL_KEYWORDS)}。"""


def _render_finding(f: dict) -> str:
    lines = [f"### {f['id']} ｜ {CHANNELS[f['domain']]['name']} ｜ 严重度：{f['severity']}", ""]
    lines.append(f"**主张**：{f['title']}")
    lines.append("")
    lines.append(f"{f['statement']}")
    lines.append("")
    lines.append("**证据**：")
    if f["evidence"]:
        for e in f["evidence"]:
            src, art = e.get("source") or "", e.get("article") or ""
            loc = "（" + " · ".join(p for p in (src, art) if p) + "）" if (src or art) else ""
            lines.append(f"- [{e['id']}] {e['text'][:160]}{loc} —— {e['grade']}")
    else:
        lines.append("- （无证据引用）")
    if f.get("obligations"):
        lines.append(f"**违法情形**：{', '.join(f['obligations'])}（合规核查判定）")
    lines.append(f"**严重度依据**：{f['severity_reason']}")
    if f.get("recommendation"):
        lines.append(f"**建议**：{f['recommendation']}")
    review = f.get("review") or {}
    if review.get("comment"):
        lines.append(f"**复核**：{review.get('verdict', '')} —— {review['comment']}")
    lines.append("")
    return "\n".join(lines)


def compose_report(state: dict) -> str:
    profile = state["profile"]
    findings = state["findings"]
    order = {"high": 0, "medium": 1, "low": 2}
    findings_sorted = sorted(findings, key=lambda f: order.get(f["severity"], 3))
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    enabled_names = [CHANNELS[c]["name"] for c in state.get("channels", [])]

    stage_label = {"seed": "种子期", "growth": "成长期", "mature": "成熟期"}.get(profile.get("lifeStage"), "未判定")
    md = [
        f"# {profile.get('companyName', state['company_name'])} · 风险发现清单",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 一、企业画像",
        "",
        f"- 企业名称：{profile.get('companyName', '')}",
        f"- 行业：{profile.get('industry', '')}",
        f"- 生命周期阶段：{stage_label}",
        f"- 判定依据：{profile.get('stageReason', '')}",
        f"- 本次启用风险域：{'、'.join(enabled_names) or '无'}",
        "",
        "## 二、违法情形核查（对照违法情形清单逐条核对）",
        "",
    ]
    compliance_results = state.get("compliance_results", [])
    if compliance_results:
        for res in compliance_results:
            verdict = OBLIGATION_VERDICT_TEXT.get(res["verdict"], res["verdict"])
            law = f"{res.get('document', '')}{res.get('article', '')}"
            md.append(f"- **{res['obligation']}**（{res['id']}｜{verdict}）—— 依据：{law}｜材料原句：{res.get('evidence', '')[:80]}")
    else:
        md.append("- 未发现相关违法情形")
    md += ["", f"## 三、风险发现（高 {counts['high']} / 中 {counts['medium']} / 低 {counts['low']}）", ""]
    if findings_sorted:
        for f in findings_sorted:
            md.append(_render_finding(f))
    else:
        md.append("（本次无风险发现）")
        md.append("")
    md += ["## 四、同类案例对照", ""]
    cases = state.get("cases", [])
    if cases:
        for c in cases:
            meta = "/".join(x for x in (c.get("domain", ""), c.get("stage", ""), c.get("outcome", "")) if x)
            md.append(f"- **{c['source_name']}**（{meta}）—— {c['content'][:120]}…")
    else:
        md.append("- 案例库暂无数据")
    md += ["## 五、追问清单", ""]
    if state.get("followups"):
        for i, item in enumerate(state["followups"], 1):
            md.append(f"{i}. {item['question']}")
    else:
        md.append("（无）")
    md += ["", "## 六、覆盖范围", ""]
    md.append(f"- 本次覆盖：{'、'.join(enabled_names) or '无'}")
    if state.get("degradation"):
        md += ["", "## 七、降级说明", ""]
        for note in dict.fromkeys(state["degradation"]):
            md.append(f"- {note}")
    md += [
        "",
        "---",
        "",
        "## 附录 A：严重度规则表",
        "",
        SEVERITY_RULES_MD,
        "",
        "## 附录 B：风险域引用来源",
        "",
        "| 风险域 | 引用来源 |",
        "|---|---|",
    ]
    for domain, source in DOMAIN_SOURCES:
        md.append(f"| {domain} | {source} |")
    md.append("")
    return "\n".join(md)
