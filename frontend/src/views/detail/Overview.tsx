// 概览：结论、严重度分布、指标、Top 风险
import { SEVERITY_TEXT } from "../../lib/constants";
import { findingCounts, severityColor, sortFindings } from "../../lib/model";
import type { ReportDetail } from "../../lib/types";

export default function Overview({ report, gotoTab }: { report: ReportDetail; gotoTab: (tab: string) => void }) {
  const findings = report.findings || [];
  const top = sortFindings(findings)[0] || null;
  const counts = findingCounts(findings);
  const obligationViolations = report.obligationViolations || 0;
  const l1 = findings.reduce((sum, f) => sum + (f.evidence || []).filter((e) => e.grade === "L1").length, 0);
  const l3 = findings.reduce((sum, f) => sum + (f.evidence || []).filter((e) => e.grade === "L3").length, 0);
  const top5 = sortFindings(findings).slice(0, 5);

  const sevText = (sev: string) => SEVERITY_TEXT[sev] || "—";

  return (
    <div className="overview-layout">
      <div className="overview-main">
        <div className={"card conclusion-card " + (top ? severityColor(top.severity) : "")}>
          <div className="conclusion-label">首要风险结论</div>
          <div className="conclusion-title">{top?.title || "本次评估未发现风险项"}</div>
          <div className="conclusion-desc">{top?.statement || ""}</div>
          <div className="conclusion-foot">
            <span className={"badge " + (top ? severityColor(top.severity) : "green")}>{top ? sevText(top.severity) : "—"}</span>
            {obligationViolations ? <span className="conclusion-baseline">确认违法 {obligationViolations} 项</span> : null}
          </div>
        </div>

        <div className="card">
          <div className="card-title-row">
            <h3>发现严重度分布</h3>
            <button className="link-btn" onClick={() => gotoTab("findings")}>查看全部发现 →</button>
          </div>
          <div className="risk-level-bars">
            <div className="level-row red"><span>高风险</span><div className="level-bar"><i style={{ width: (findings.length ? (counts.high / findings.length) * 100 : 0) + "%" }}></i></div><b>{counts.high}</b></div>
            <div className="level-row yellow"><span>中风险</span><div className="level-bar"><i style={{ width: (findings.length ? (counts.medium / findings.length) * 100 : 0) + "%" }}></i></div><b>{counts.medium}</b></div>
            <div className="level-row green"><span>低风险</span><div className="level-bar"><i style={{ width: (findings.length ? (counts.low / findings.length) * 100 : 0) + "%" }}></i></div><b>{counts.low}</b></div>
          </div>
        </div>

        <div className="card">
          <div className="card-title-row"><h3>关键指标</h3></div>
          <div className="key-metrics">
            <div><b>{obligationViolations}</b><span>确认违法</span></div>
            <div><b>{l1}</b><span>L1 直接证据</span></div>
            <div><b>{l3}</b><span>待核查项</span></div>
            <div><b>{(report.followups || []).length}</b><span>追问事项</span></div>
          </div>
        </div>
      </div>

      <div className="overview-side">
        <div className="card">
          <div className="card-title-row"><h3>Top 风险</h3></div>
          <div className="top-risk-list">
            {findings.length ? top5.map((f) => (
              <div className="top-risk-row" key={f.id} onClick={() => gotoTab("findings")}>
                <span className={"light-dot " + severityColor(f.severity)}></span>
                <div className="top-risk-title">{f.title}</div>
                <b className={severityColor(f.severity)}>{sevText(f.severity)}</b>
              </div>
            )) : <p className="empty-sub">无发现</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
