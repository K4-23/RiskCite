import uuid
from typing import TYPE_CHECKING
from ...rules.evidence import grade_evidence
from ..state import PipelineState

if TYPE_CHECKING:
    from ..graph import PipelineContext


async def verify_evidence(state: PipelineState, ctx: "PipelineContext") -> dict:
    t = ctx.tracer.node_start("verify_evidence")
    channel_evidence = state.get("channel_evidence", {})
    findings: list[dict] = []

    def _similar(a: str, b: str) -> bool:
        from ...rules.evidence import longest_common_substring
        shorter = min(len(a), len(b))
        return shorter >= 6 and longest_common_substring(a, b) >= max(8, int(shorter * 0.6))

    for draft in state["drafts"]:
        candidates = channel_evidence.get(draft["channel"], [])
        cand_payload = [{"id": e["id"], "content": e["content"], "source_name": e["source_name"],
                         "article": e.get("article")} for e in candidates]
        graded = grade_evidence(draft.get("evidence", []), cand_payload, state["material_text"])
        for i, entry in enumerate(graded):
            entry["id"] = f"E{i + 1}"
        review = next((v for v in state.get("verdicts", []) if state["drafts"][v["index"]]["key"] == draft["key"]), {})
        finding = {
            "id": f"F-{uuid.uuid4().hex[:6].upper()}",
            "domain": draft["channel"],
            "title": draft["title"],
            "statement": draft["statement"],
            "evidence": graded,
            "obligations": [],
            "recommendation": draft.get("recommendation", ""),
            "review": {"verdict": review.get("verdict", "pass"), "comment": review.get("comment", "")},
            "fallback": draft.get("fallback", False),
        }
        dup = next((f for f in findings if f["domain"] == finding["domain"] and _similar(f["title"], finding["title"])), None)
        if dup:
            # 重复发现保留证据较多的一条
            if len(finding["evidence"]) > len(dup["evidence"]):
                findings[findings.index(dup)] = finding
            continue
        findings.append(finding)
    ctx.tracer.node_end("verify_evidence", t, {"findings": len(findings)})
    return {"findings": findings}