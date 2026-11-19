import re
from typing import TYPE_CHECKING


STAGE_PATTERNS = [
    ("mature", re.compile(r"上市|IPO|Pre-IPO|成熟期|规模化盈利|已盈利")),
    ("seed", re.compile(r"天使轮|种子轮|预研|样机|尚未盈利|尚无收入|A 轮|A轮")),
    ("growth", re.compile(r"B 轮|B轮|C 轮|C轮|PoC|试点|试运行|初步商业化")),
]

KEY_FIELD_CHECKS = [
    ("授权", "材料未说明数据/内容授权安排，请补充授权文件或授权说明。"),
    ("客户集中度", "材料未说明客户集中度（前五大客户占比），请补充。"),
    ("供应商", "材料未提供关键部件供应商清单，请补充。"),
    ("伦理审查", "材料未说明是否开展科技伦理审查，请补充。"),
]


def _pick_company_name(text: str, fallback: str) -> str:
    for pattern in (r"企业名称[:：]\s*([^\n\r]+)", r"公司名称[:：]\s*([^\n\r]+)", r"公司[:：]\s*([^\n\r]{2,30})"):
        match = re.search(pattern, text or "")
        if match:
            return match.group(1).strip()[:60]
    return fallback or "未命名企业"

def _pick_industry(text: str) -> str:
    """从材料里的“行业：xxx”一行取行业；取不到返回空串。"""
    for pattern in (r"所属行业[:：]\s*([^\n\r]+)", r"行业[:：]\s*([^\n\r]+)"):
        match = re.search(pattern, text or "")
        if match:
            return match.group(1).strip()[:40]
    return ""

def _detect_stage(text: str) -> str:
    for stage, pattern in STAGE_PATTERNS:
        if pattern.search(text or ""):
            return stage
    return "growth"

def _slice_material(material_text: str, keywords: list[str], limit: int) -> str:
    lines = [line.strip() for line in (material_text or "").splitlines() if line.strip()]
    preamble = lines[:6]
    relevant = [line for line in lines if any(kw in line for kw in keywords)]
    seen: set[str] = set()
    parts = []
    for line in preamble + relevant:
        if line not in seen:
            seen.add(line)
            parts.append(line)
    return "\n".join(parts)[:limit]