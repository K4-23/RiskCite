import asyncio
import json
from typing import TYPE_CHECKING
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from ..channels import CHANNELS
from ...core.llm import extract_json, get_chat_model, invoke_json, llm_configured
from ..tools import SEARCH_EVIDENCE_TOOL
from .. import prompts
from ..state import PipelineState
from .common import _slice_material

if TYPE_CHECKING:
    from ..graph import PipelineContext


def _risk_cards(cid: str, risks) -> list[dict] | None:
    if not isinstance(risks, list) or not risks:
        return None
    return [
        {
            "key": f"{cid}-{i + 1}", "channel": cid,
            "title": str(risk.get("title", "")).strip()[:120],
            "statement": str(risk.get("statement", "")).strip(),
            "evidence": [{"text": str(e.get("text", "")).strip(), "source": e.get("source", "material")}
                         for e in (risk.get("evidence") or []) if str(e.get("text", "")).strip()],
            "recommendation": str(risk.get("recommendation", "")).strip(),
        }
        for i, risk in enumerate(risks[:4])
    ]

def _fallback_card(cid: str, material: str) -> dict:
    fb = CHANNELS[cid]["fallback"]
    ev_lines = _slice_material(material, CHANNELS[cid]["material_keywords"], 600).splitlines()
    return {
        "key": f"{cid}-1", "channel": cid, "title": fb["title"],
        "statement": fb["statement"],
        "evidence": [{"text": ev_lines[0][:120], "source": "material"}] if ev_lines else [],
        "recommendation": fb["recommendation"],
        "fallback": True,
    }

def _parse_cards(cid: str, content) -> list[dict] | None:
    parsed = extract_json(content if isinstance(content, str) else str(content))
    return _risk_cards(cid, parsed.get("risks")) if isinstance(parsed, dict) else None

async def _tool_agent(cid: str, channel: dict, profile: dict, material_slice: str,
                      evidence: list[dict], fetch) -> list[dict] | None:
    model = get_chat_model(temperature=0.15)
    bound = model.bind_tools([SEARCH_EVIDENCE_TOOL])
    messages = [
        SystemMessage(content=prompts.CHANNEL_SYSTEM_TOOL),
        HumanMessage(content=prompts.channel_prompt(
            channel, profile, profile["agenda"].get(cid, []), material_slice, evidence, 1, tool_mode=True)),
    ]
    for round_index in range(1, 4):
        reply = await bound.ainvoke(messages)
        messages.append(reply)
        calls = getattr(reply, "tool_calls", None) or []
        if not calls:
            return _parse_cards(cid, getattr(reply, "content", ""))
        for i, call in enumerate(calls):
            # 每个 tool_call 对应一条 ToolMessage
            tool_id = str(call.get("id", ""))
            query = str((call.get("args") or {}).get("query", "")).strip()
            if i >= 2 or not query:
                messages.append(ToolMessage(content='{"skipped": true}', tool_call_id=tool_id))
                continue
            added = await fetch(query, round_index)
            messages.append(ToolMessage(
                content=json.dumps([
                    {"source": e.get("source_name", ""), "article": e.get("article") or "",
                     "content": (e.get("content") or "")[:300]}
                    for e in added
                ], ensure_ascii=False),
                tool_call_id=tool_id,
            ))
    # 轮次用尽后禁用工具
    reply = await model.ainvoke(messages + [HumanMessage(content="检索轮次已用尽，请基于现有证据直接输出结论 JSON。")])
    return _parse_cards(cid, getattr(reply, "content", ""))

async def _run_channel_agent(cid: str, profile: dict, material: str, ctx: "PipelineContext",
                             degradation: list[str]) -> tuple[str, list[dict], list[dict]]:
    channel = CHANNELS[cid]
    ctx.channel(cid, "running")
    material_slice = _slice_material(material, channel["material_keywords"], ctx.settings.material_slice_limit)
    evidence: list[dict] = []
    seen_ids: set[str] = set()
    model = get_chat_model(temperature=0.15) if llm_configured() else None

    async def fetch(query: str, round_index: int) -> list[dict]:
        added: list[dict] = []
        for item in await ctx.gateway.retrieve(cid, channel["domain"], query, round_index=round_index):
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                evidence.append(item)
                added.append(item)
        return added

    # 首轮使用固定查询检索
    for query in channel["retrieval_queries"][:2]:
        await fetch(query, 0)

    cards: list[dict] | None = None
    if model is not None and ctx.settings.tool_calling:
        try:
            cards = await _tool_agent(cid, channel, profile, material_slice, evidence, fetch)
        except Exception as exc:  # 模型不支持 tools 时回退 JSON 循环
            degradation.append(f"{cid} tool calling 失败，回退 JSON 循环（{type(exc).__name__}）")
            cards = None
    for round_index in range(1, 4):
        if model is None or cards is not None:
            break
        parsed = await invoke_json(
            model,
            [SystemMessage(content=prompts.CHANNEL_SYSTEM),
             HumanMessage(content=prompts.channel_prompt(
                 channel, profile, profile["agenda"].get(cid, []), material_slice, evidence, round_index))],
            f"channel_scan:{cid}:r{round_index}", ctx.tracer)
        if not isinstance(parsed, dict):
            break
        cards = _risk_cards(cid, parsed.get("risks"))
        requests = parsed.get("more_evidence")
        if round_index >= 3 or not isinstance(requests, list) or not requests:
            break  # 证据充足或轮次用尽
        added = 0
        for req in requests[:2]:
            query = str(req.get("query", "") if isinstance(req, dict) else req).strip()
            if query:
                added += len(await fetch(query, round_index))
        if added == 0:
            break  # 无新增证据时停止

    if cards is None:
        cards = [_fallback_card(cid, material)]
        if model is not None:
            degradation.append(f"{cid} LLM 输出解析失败，使用规则兜底")

    kept_evidence = evidence[: ctx.settings.evidence_top_n * 2]
    ctx.channel(cid, "done", len(kept_evidence))
    return cid, cards, kept_evidence

async def channel_scan(state: PipelineState, ctx: "PipelineContext") -> dict:
    t = ctx.tracer.node_start("channel_scan")
    degradation = list(state.get("degradation", []))
    results = await asyncio.gather(*(
        _run_channel_agent(cid, state["profile"], state["material_text"], ctx, degradation)
        for cid in state["channels"]))

    drafts: list[dict] = []
    channel_evidence: dict[str, list] = {}
    for cid, cards, evidence in results:
        drafts.extend(cards)
        channel_evidence[cid] = evidence

    ctx.tracer.node_end("channel_scan", t, {"channels": len(state["channels"]), "drafts": len(drafts)})
    return {"channel_evidence": channel_evidence, "drafts": drafts, "degradation": degradation}