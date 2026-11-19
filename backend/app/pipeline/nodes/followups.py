from typing import TYPE_CHECKING
from ..channels import CHANNELS
from ..state import PipelineState
from .common import KEY_FIELD_CHECKS

if TYPE_CHECKING:
    from ..graph import PipelineContext


async def build_followups(state: PipelineState, ctx: "PipelineContext") -> dict:
    t = ctx.tracer.node_start("build_followups")
    followups: list[dict] = []
    material = state["material_text"]
    for res in state.get("compliance_results", []):
        if res["verdict"] in ("violation", "suspect"):
            followups.append({
                "question": f"关于违法情形「{res['obligation']}」（{res['document']}{res['article']}），请提供合规证明材料。",
                "target": res["id"], "importance": 1,
            })
    for finding in state["findings"]:
        if finding.get("fallback"):
            continue
        weak = [e for e in finding["evidence"] if e["grade"] == "L3"]
        if weak and len(weak) == len(finding["evidence"]):
            # 未知风险域跳过
            checklist = CHANNELS.get(finding["domain"], {}).get("checklist", [])
            if not checklist:
                continue
            hint = "；".join(checklist[:2])
            followups.append({
                "question": f"关于「{finding['title']}」，材料未提供充分证据，请补充：{hint}。",
                "target": finding["id"], "importance": 2,
            })
    for needle, question in KEY_FIELD_CHECKS:
        if needle not in material:
            followups.append({"question": question, "target": "material", "importance": 3})
    followups.sort(key=lambda f: f["importance"])
    ctx.tracer.node_end("build_followups", t, {"followups": len(followups)})
    return {"followups": followups}