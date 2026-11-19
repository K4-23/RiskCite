from typing import TYPE_CHECKING
from langchain_core.messages import HumanMessage, SystemMessage
from ..channels import CHANNELS, all_agents
from ...core.llm import get_chat_model, invoke_json, llm_configured
from .. import prompts
from ..state import PipelineState
from .common import _detect_stage, _pick_company_name, _pick_industry

if TYPE_CHECKING:
    from ..graph import PipelineContext


async def entry_analysis(state: PipelineState, ctx: "PipelineContext") -> dict:
    t = ctx.tracer.node_start("entry_analysis")
    material = state["material_text"]
    channels = all_agents()
    # 企业名称优先取自表单
    user_name = (state.get("company_name") or "").strip()
    material_name = _pick_company_name(material, "")
    profile = {
        "companyName": user_name or material_name or "未命名企业",
        "industry": _pick_industry(material) or "材料未明确说明",
        "lifeStage": _detect_stage(material),
        "stageReason": "规则关键词判定",
        "agenda": {cid: CHANNELS[cid]["checklist"][:2] for cid in channels},
    }
    degradation = list(state.get("degradation", []))

    if llm_configured():
        parsed = await invoke_json(
            get_chat_model(temperature=0.0),
            [SystemMessage(content=prompts.ENTRY_SYSTEM),
             HumanMessage(content=prompts.entry_prompt(state["company_name"], channels, material[:15000]))],
            "entry_analysis", ctx.tracer)
        if isinstance(parsed, dict):
            extracted = str(parsed.get("companyName") or "").strip()
            profile = {
                "companyName": user_name or extracted or profile["companyName"],
                "industry": parsed.get("industry") or profile["industry"],
                "lifeStage": parsed["lifeStage"] if parsed.get("lifeStage") in ("seed", "growth", "mature") else profile["lifeStage"],
                "stageReason": parsed.get("stageReason") or profile["stageReason"],
                "agenda": {cid: (parsed.get("agenda") or {}).get(cid) or profile["agenda"].get(cid, [])
                           for cid in channels},
            }
        else:
            degradation.append("入口分析 LLM 输出解析失败，使用规则兜底")
    else:
        degradation.append("LLM 未启用，入口分析使用规则兜底")

    ctx.tracer.node_end("entry_analysis", t, {"stage": profile["lifeStage"], "channels": channels})
    return {"profile": profile, "channels": channels, "degradation": degradation}