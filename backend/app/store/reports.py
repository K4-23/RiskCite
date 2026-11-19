# 报告持久化与台账 diff
import json
import uuid
from datetime import datetime

from sqlalchemy import delete, select

from .models import FindingRow, LedgerDiffRow, Report, SessionLocal


def _finding_key(f: dict) -> tuple[str, str]:
    return (f.get("domain", ""), (f.get("title") or "").strip())


def compute_diff(new_findings: list[dict], old_findings: list[dict]) -> dict:
    """台账差异：按 (领域, 标题) 对齐两次评估的发现，返回 {added, changed, resolved}。"""
    new_map = {_finding_key(f): f for f in new_findings}
    old_map = {_finding_key(f): f for f in old_findings}
    added, resolved, changed = [], [], []
    for key, f in new_map.items():
        if key not in old_map:
            added.append({"domain": key[0], "title": key[1], "severity": f["severity"]})
        else:
            old = old_map[key]
            if old["severity"] != f["severity"] or set(old.get("obligations", [])) != set(f.get("obligations", [])):
                changed.append({"domain": key[0], "title": key[1],
                                "severity": f"{old['severity']} → {f['severity']}",
                                "obligations": f"{old.get('obligations', [])} → {f.get('obligations', [])}"})
    for key, f in old_map.items():
        if key not in new_map:
            resolved.append({"domain": key[0], "title": key[1], "severity": f["severity"]})
    return {"added": added, "resolved": resolved, "changed": changed}


def _diff_section(diff: dict) -> str:
    lines = ["", "## 附录 C：与上次评估对比（台账）", ""]
    if not (diff["added"] or diff["resolved"] or diff["changed"]):
        lines.append("- 与上次评估无变化")
        return "\n".join(lines)
    if diff["added"]:
        lines.append("**新增发现**：")
        lines += [f"- [{f['domain']}] {f['title']}（{f['severity']}）" for f in diff["added"]]
    if diff["changed"]:
        lines.append("**变化**：")
        lines += [f"- [{f['domain']}] {f['title']}：{f['severity']}｜违法情形：{f['obligations']}" for f in diff["changed"]]
    if diff["resolved"]:
        lines.append("**解除**：")
        lines += [f"- [{f['domain']}] {f['title']}" for f in diff["resolved"]]
    return "\n".join(lines)


def save_report(result: dict) -> dict:
    """管线最终状态落库：报告 + 发现明细 + 与该企业上一次评估的台账差异。
    返回供接口响应的 {report_id, summary, diff, report_md, findings, followups}。"""
    report_id = f"R-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    company = result["profile"].get("companyName") or result["company_name"]

    with SessionLocal() as session:
        previous = session.execute(
            select(Report).where(Report.company_name == company).order_by(Report.created_at.desc())
        ).scalars().first()

        old_findings: list[dict] = []
        if previous:
            rows = session.execute(select(FindingRow).where(FindingRow.report_id == previous.report_id)).scalars().all()
            old_findings = [json.loads(r.finding_json) for r in rows]

        diff = compute_diff(result["findings"], old_findings)
        report_md = result["report_md"]
        if previous and (diff["added"] or diff["resolved"] or diff["changed"]):
            report_md += "\n" + _diff_section(diff)

        summary = {
            "companyName": company, "industry": result["profile"].get("industry", ""),
            "lifeStage": result["profile"].get("lifeStage", ""),
            "llmMode": result["llm_mode"], "channels": result.get("channels", []),
            "obligationViolations": sum(1 for r in result.get("compliance_results", []) if r.get("verdict") == "violation"),
            "obligationResults": result.get("compliance_results", []),
            "severityCounts": {
                "high": sum(1 for f in result["findings"] if f["severity"] == "high"),
                "medium": sum(1 for f in result["findings"] if f["severity"] == "medium"),
                "low": sum(1 for f in result["findings"] if f["severity"] == "low"),
            },
            "followupCount": len(result.get("followups", [])),
            "followups": result.get("followups", []),
            "degradation": result.get("degradation", []),
        }
        session.add(Report(report_id=report_id, company_name=company,
                           life_stage=result["profile"].get("lifeStage", ""), llm_mode=result["llm_mode"],
                           summary_json=json.dumps(summary, ensure_ascii=False),
                           report_md=report_md))
        for f in result["findings"]:
            session.add(FindingRow(report_id=report_id, finding_json=json.dumps(f, ensure_ascii=False)))
        if previous:
            session.add(LedgerDiffRow(report_id=report_id, base_report_id=previous.report_id,
                                      diff_json=json.dumps(diff, ensure_ascii=False)))
        session.commit()

    return {"report_id": report_id, "summary": summary, "diff": diff,
            "report_md": report_md, "findings": result["findings"], "followups": result.get("followups", [])}


def list_reports() -> list[dict]:
    heavy = ("obligationResults", "followups", "degradation")
    with SessionLocal() as session:
        rows = session.execute(select(Report).order_by(Report.created_at.desc())).scalars().all()
        return [{k: v for k, v in {**json.loads(r.summary_json), "report_id": r.report_id,
                 "created_at": r.created_at.isoformat()}.items() if k not in heavy}
                for r in rows]


def get_report(report_id: str) -> dict | None:
    with SessionLocal() as session:
        report = session.get(Report, report_id)
        if not report:
            return None
        findings = [json.loads(r.finding_json) for r in
                    session.execute(select(FindingRow).where(FindingRow.report_id == report_id)).scalars().all()]
        diff_row = session.get(LedgerDiffRow, report_id)
        return {
            "report_id": report_id,
            **json.loads(report.summary_json),
            "created_at": report.created_at.isoformat(),
            "findings": findings,
            "diff": json.loads(diff_row.diff_json) if diff_row else None,
        }


def get_report_markdown(report_id: str) -> str | None:
    with SessionLocal() as session:
        report = session.get(Report, report_id)
        return report.report_md if report else None


def delete_report(report_id: str) -> bool:
    with SessionLocal() as session:
        report = session.get(Report, report_id)
        if not report:
            return False
        session.execute(delete(FindingRow).where(FindingRow.report_id == report_id))
        session.execute(delete(LedgerDiffRow).where(LedgerDiffRow.report_id == report_id))
        session.execute(delete(LedgerDiffRow).where(LedgerDiffRow.base_report_id == report_id))
        session.delete(report)
        session.commit()
    return True
