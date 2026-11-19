import asyncio
from typing import TYPE_CHECKING
from langchain_core.messages import HumanMessage, SystemMessage
from ..channels import CHANNELS
from ...core.llm import get_chat_model, invoke_json, llm_configured
from .. import prompts
from ..state import PipelineState

if TYPE_CHECKING:
    from ..graph import PipelineContext


async def review(state: PipelineState, ctx: "PipelineContext") -> dict:
    t = ctx.tracer.node_start("review")
    drafts = state["drafts"]
    verdicts: list[dict] = []
    degradation = list(state.get("degradation", []))

    if llm_configured() and drafts:
        parsed = await invoke_json(
            get_chat_model(temperature=0.0),
            [SystemMessage(content=prompts.REVIEW_SYSTEM),
             HumanMessage(content=prompts.review_prompt(drafts))],
            "review", ctx.tracer)
        raw = parsed.get("verdicts") if isinstance(parsed, dict) else None
        if isinstance(raw, list):
            valid = {i for i in range(len(drafts))}
            verdicts = [v for v in raw if isinstance(v, dict) and v.get("index") in valid]
    if not verdicts:
        verdicts = [{
            "index": i,
            "verdict": "needEvidence" if not d.get("evidence") else "pass",
            "comment": "启发式复核：无证据引用" if not d.get("evidence") else "启发式复核通过",
        } for i, d in enumerate(drafts)]
        if llm_configured():
            degradation.append("复核 LLM 输出解析失败，使用启发式")

    # 证据不足时补充检索
    need = [v for v in verdicts if v.get("verdict") == "needEvidence"]
    revised_by_key: dict[str, dict] = {}
    if need and llm_configured():
        by_channel: dict[str, list[dict]] = {}
        for v in need:
            draft = drafts[v["index"]]
            by_channel.setdefault(draft["channel"], []).append(v)

        async def revise(cid: str, items: list[dict]) -> None:
            channel = CHANNELS[cid]
            extra_query = " ".join(drafts[v["index"]]["title"] for v in items)
            new_evidence = await ctx.gateway.retrieve("review", channel["domain"], extra_query)
            parsed = await invoke_json(
                get_chat_model(temperature=0.0),
                [SystemMessage(content=prompts.CHANNEL_SYSTEM),
                 HumanMessage(content=prompts.revise_prompt(channel, drafts, items, new_evidence))],
                f"review:revise:{cid}", ctx.tracer)
            risks = parsed.get("risks") if isinstance(parsed, dict) else None
            if isinstance(risks, list):
                for risk in risks:
                    idx = risk.get("index")
                    if isinstance(idx, int) and 0 <= idx < len(drafts) and drafts[idx]["channel"] == cid:
                        draft = drafts[idx]
                        updated = {
                            **draft,
                            "title": str(risk.get("title", draft["title"])).strip()[:120],
                            "statement": str(risk.get("statement", draft["statement"])).strip(),
                            "evidence": [{"text": str(e.get("text", "")).strip(), "source": e.get("source", "material")}
                                         for e in (risk.get("evidence") or []) if str(e.get("text", "")).strip()] or draft["evidence"],
                            "recommendation": str(risk.get("recommendation", draft["recommendation"])).strip(),
                            "revised": True,
                        }
                        revised_by_key[draft["key"]] = updated

        await asyncio.gather(*(revise(cid, items) for cid, items in by_channel.items()))

    final_drafts = [revised_by_key.get(d["key"], d) for d in drafts]
    for v in verdicts:
        draft = final_drafts[v["index"]]
        if revised_by_key.get(draft["key"]):
            v["verdict"] = "pass"
            v["comment"] = f"{v.get('comment', '')}（已补证修订）".strip()

    ctx.tracer.node_end("review", t, {"verdicts": len(verdicts), "revised": len(revised_by_key)})
    return {"drafts": final_drafts, "verdicts": verdicts, "degradation": degradation}