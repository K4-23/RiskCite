from typing import TYPE_CHECKING
from langchain_core.messages import HumanMessage, SystemMessage
from ...core.llm import get_chat_model, invoke_json, llm_configured
from ...rules.obligations import recall_obligations
from .. import prompts
from ..state import PipelineState

if TYPE_CHECKING:
    from ..graph import PipelineContext


async def compliance_check(state: PipelineState, ctx: "PipelineContext") -> dict:
    t = ctx.tracer.node_start("compliance_check")
    material = state["material_text"]
    degradation = list(state.get("degradation", []))
    candidates = recall_obligations(material)
    results: list[dict] = []

    def _entry(ob: dict, verdict: str, evidence: str, **extra) -> dict:
        entry = {"id": ob["id"], "domain": ob.get("domain", ""), "obligation": ob.get("obligation", ""),
                 "question": ob.get("question", ""), "document": ob.get("document", ""),
                 "article": ob.get("article", ""), "verdict": verdict,
                 "evidence": evidence[:200]}
        entry.update(extra)
        return entry

    if candidates and llm_configured():
        parsed = await invoke_json(
            get_chat_model(temperature=0.0),
            [SystemMessage(content=prompts.COMPLIANCE_SYSTEM),
             HumanMessage(content=prompts.compliance_prompt(candidates, material[:15000]))],
            "compliance_check", ctx.tracer)
        verdict_map: dict[str, dict] = {}
        if isinstance(parsed, dict):
            for v in parsed.get("results") or []:
                if isinstance(v, dict) and v.get("id"):
                    verdict_map[str(v["id"])] = v
        unverified = 0
        for ob in candidates:
            v = verdict_map.get(ob["id"])
            if v and v.get("verdict") in ("violation", "suspect", "not_found"):
                results.append(_entry(ob, v["verdict"], str(v.get("evidence") or ob["evidence_line"])))
            else:
                results.append(_entry(ob, "suspect", ob["evidence_line"], unverified=True))
                unverified += 1
        if unverified:
            degradation.append(f"合规核查有 {unverified} 条情形 LLM 未给出结论，按疑似处理")
    elif candidates:
        for ob in candidates:
            results.append(_entry(ob, "suspect", ob["evidence_line"], rule_based=True))
        degradation.append("合规核查使用规则兜底（模型未启用或调用失败）：粗筛命中即列为疑似，待人工核验")

    ctx.tracer.node_end("compliance_check", t,
                        {"candidates": len(candidates), "results": len(results),
                         "violations": sum(1 for r in results if r["verdict"] == "violation")})
    return {"compliance_results": results, "degradation": degradation}