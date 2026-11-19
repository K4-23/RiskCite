import uuid
from typing import TYPE_CHECKING
from ..channels import DOMAIN_TO_ID
from ...rules.evidence import grade_evidence
from ...rules.severity import classify
from ..state import PipelineState

if TYPE_CHECKING:
    from ..graph import PipelineContext


async def attach_obligations(state: PipelineState, ctx: "PipelineContext") -> dict:
    t = ctx.tracer.node_start("attach_obligations")
    findings = state["findings"]
    for res in state.get("compliance_results", []):
        if res["verdict"] == "not_found":
            continue
        domain = DOMAIN_TO_ID.get(res["domain"], res["domain"])
        graded = grade_evidence([{"text": res["evidence"]}], [], state["material_text"])
        same_domain = [f for f in findings if f["domain"] == domain]
        if res["verdict"] == "violation":
            if same_domain:
                for finding in same_domain:
                    finding.setdefault("obligations", [])
                    if res["id"] not in finding["obligations"]:
                        finding["obligations"].append(res["id"])
                    finding["obligation_verdict"] = "violation"
            else:
                findings.append({
                    "id": f"F-{uuid.uuid4().hex[:6].upper()}", "domain": domain,
                    "title": res["obligation"], "statement": f"材料显示存在违法情形，{res['document']}{res['article']}要求：{res['obligation']}。",
                    "evidence": [dict(e, id=f"E{i + 1}") for i, e in enumerate(graded)],
                    "obligations": [res["id"]], "obligation_verdict": "violation",
                    "recommendation": res.get("action", "立即整改并补充合规证明材料"),
                    "review": {"verdict": "pass", "comment": "合规核查 agent 判定"}, "fallback": False,
                })
        else:  # suspect
            if not same_domain:
                findings.append({
                    "id": f"F-{uuid.uuid4().hex[:6].upper()}", "domain": domain,
                    "title": f"疑似未履行：{res['obligation']}", "statement": f"核查问题：{res['question']}（依据 {res['document']}{res['article']}）材料证据不足，待核查。",
                    "evidence": [dict(e, id=f"E{i + 1}") for i, e in enumerate(graded)],
                    "obligations": [res["id"]], "obligation_verdict": "suspect",
                    "recommendation": "补充相关合规证明材料",
                    "review": {"verdict": "needEvidence", "comment": "疑似，证据待核查"}, "fallback": False,
                })
    for finding in findings:
        severity, reason = classify(finding)
        finding["severity"] = severity
        finding["severity_reason"] = reason
    ctx.tracer.node_end("attach_obligations", t, {"findings": len(findings)})
    return {"findings": findings}