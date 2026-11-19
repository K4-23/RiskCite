# 严重度规则表 SL-1 ~ SL-4

# 存续类关键词（SL-2 判高条件）
SURVIVAL_KEYWORDS = ["停业", "资质丧失", "吊销", "断供", "无法交付", "融资失败",
                     "核心人员流失", "现金流断裂", "处罚", "清算"]


def _survival(finding: dict) -> bool:
    blob = f"{finding.get('title', '')}{finding.get('statement', '')}"
    return any(kw in blob for kw in SURVIVAL_KEYWORDS)


def _has_grade(finding: dict, *grades: str) -> bool:
    return any(e.get("grade") in grades for e in finding.get("evidence", []))


def classify(finding: dict) -> tuple[str, str]:
    """按 SL-1 ~ SL-4 顺序判定严重度，返回 (档位, 判定依据说明)。"""
    # SL-1 仅适用于确认违规的情形
    if finding.get("obligations") and finding.get("obligation_verdict") == "violation":
        return "high", "SL-1（命中违法情形）"
    if _has_grade(finding, "L1") and _survival(finding):
        return "high", "SL-2（L1 证据 + 存续类风险）"
    if _has_grade(finding, "L1", "L2"):
        return "medium", "SL-3（存在直接或间接证据）"
    return "low", "SL-4（证据不足，待核查）"
