# 违法情形粗筛：关键词召回
# 数据在 backend/data/obligations.json
import json
from functools import lru_cache
from pathlib import Path

OBLIGATIONS_FILE = Path(__file__).resolve().parents[2] / "data" / "obligations.json"


@lru_cache(maxsize=1)
def load_obligations() -> list[dict]:
    raw = json.loads(OBLIGATIONS_FILE.read_text(encoding="utf-8"))
    return raw["obligations"]


def _contains(text: str, needle: str) -> bool:
    if needle.isascii():
        return needle.lower() in text.lower()
    return needle in text


def recall_obligations(text: str, obligations: list[dict] | None = None) -> list[dict]:
    """粗筛召回：触发词命中且无豁免词的情形进入精判；含证据句（触发词所在行）。"""
    obligations = obligations if obligations is not None else load_obligations()
    text = text or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates: list[dict] = []
    for ob in obligations:
        hit_kw = next((kw for kw in ob.get("keywords", []) if _contains(text, kw)), None)
        if hit_kw is None:
            continue
        if any(_contains(text, kw) for kw in ob.get("exempt", [])):
            continue
        evidence_line = next((line for line in lines if _contains(line, hit_kw)), text[:120])
        candidates.append({
            "id": ob["id"], "domain": ob.get("domain", ""),
            "obligation": ob.get("obligation", ""), "question": ob.get("question", ""),
            "document": ob.get("document", ""), "article": ob.get("article", ""),
            "matched": hit_kw, "evidence_line": evidence_line,
        })
    return candidates
