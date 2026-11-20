# 证据句与原文比对，划分 L1/L2/L3
# 中文连续 8 字或英文连续 4 词判为命中

import re
import unicodedata
from difflib import SequenceMatcher

MIN_OVERLAP = 8      # 条文定位的最小重合字数
MATCH_SCORE = 8      # 证据命中阈值（中文 1 分/字，英文 2 分/词）

# 否定式陈述不计为证据
NEGATIVE_HINTS = ("材料未", "材料中未", "材料没有", "未提供", "未包含", "未提及", "未见相关",
                  "无法验证", "无法评估", "无法判断", "不得而知")


def is_negative_evidence(text: str) -> bool:
    t = text or ""
    return any(h in t for h in NEGATIVE_HINTS)

ARTICLE_RE = re.compile(r"第[0-9零一二三四五六七八九十百千]+条")


def longest_common_substring(a: str, b: str) -> int:
    if not a or not b:
        return 0
    return SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size


CJK_RE = re.compile(r"[\u4e00-\u9fff]")
TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[a-z0-9]+")


def _weighted_tokens(text: str) -> list[tuple[str, int]]:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    return [(m.group(), 1 if CJK_RE.fullmatch(m.group()) else 2)
            for m in TOKEN_RE.finditer(normalized)]


def _max_weighted_run(a: list[tuple[str, int]], b: list[tuple[str, int]]) -> int:
    if not a or not b:
        return 0
    matcher = SequenceMatcher(None, [t for t, _ in a], [t for t, _ in b], autojunk=False)
    best = 0
    for block in matcher.get_matching_blocks():
        if block.size:
            best = max(best, sum(w for _, w in a[block.a:block.a + block.size]))
    return best


def weighted_overlap(a: str, b: str) -> int:
    return _max_weighted_run(_weighted_tokens(a), _weighted_tokens(b))


def split_law_chunks(text: str, max_len: int = 1200) -> list[tuple[str, str]] | None:
    text = text or ""
    matches = list(ARTICLE_RE.finditer(text))
    if len(matches) < 5:
        return None
    out: list[tuple[str, str]] = []
    if matches[0].start() > 0:
        head = text[: matches[0].start()].strip()
        if len(head) >= 30:
            out.append(("文件头", head))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        label, seg = m.group(), text[m.start():end].strip()
        if not seg:
            continue
        if len(seg) <= max_len:
            out.append((label, seg))
        else:
            for k in range(0, len(seg), max_len):
                part = seg[k:k + max_len]
                suffix = f"（续{k // max_len + 1}）" if k else ""
                out.append((label + suffix, part))
    return out or None


def locate_article(chunk_text: str, evidence_text: str) -> str | None:
    text = chunk_text or ""
    matches = list(ARTICLE_RE.finditer(text))
    if not matches:
        return None
    best_label, best = None, MIN_OVERLAP
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        ov = longest_common_substring(evidence_text, text[m.start():end])
        if ov > best:
            best, best_label = ov, m.group()
    return best_label


def grade_evidence(entries: list[dict], candidates: list[dict], company_text: str = "") -> list[dict]:
    """entries: [{text, source?, grade?}]; candidates: [{id, content, source_name, article?}] → 定级后的证据条目。"""
    graded: list[dict] = []
    cand_tokens = [(cand, _weighted_tokens(str(cand.get("content") or ""))) for cand in (candidates or [])]
    company_tokens = _weighted_tokens(company_text) if company_text else []
    for entry in entries or []:
        text = str(entry.get("text") or "").strip()
        declared = entry.get("grade")
        # 来源以比对结果为准
        item = {"text": text, "source": None, "article": None, "grade": "L3"}

        # 否定式陈述不参与比对
        if is_negative_evidence(text):
            item.update(source="材料核对", gap_check=True)
            graded.append(item)
            continue

        quote_tokens = _weighted_tokens(text)
        best_hit = None
        for cand, tokens in cand_tokens:
            overlap = _max_weighted_run(quote_tokens, tokens)
            if overlap >= MATCH_SCORE and (best_hit is None or overlap > best_hit["overlap"]):
                best_hit = {"overlap": overlap, "id": cand.get("id"),
                            "source_name": cand.get("source_name"),
                            "content": str(cand.get("content") or ""),
                            "article": cand.get("article")}

        if best_hit:
            article = best_hit["article"] or locate_article(best_hit["content"], text)
            item.update(grade="L1", source=best_hit["source_name"], article=article, verified=True)
        elif company_tokens and _max_weighted_run(quote_tokens, company_tokens) >= MATCH_SCORE:
            item.update(grade="L1", source="企业材料", verified=True)
        elif declared == "L1":
            item.update(grade="L2", demoted_from="L1")
        elif declared == "L2":
            item.update(grade="L2")
        graded.append(item)
    return graded
