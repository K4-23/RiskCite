// 评估详情：四个 Tab
import { useState } from "react";
import { SEVERITY_TEXT } from "../lib/constants";
import { severityColor, topFinding } from "../lib/model";
import type { ReportDetail, ReportSummary } from "../lib/types";
import Overview from "./detail/Overview";
import Findings from "./detail/Findings";
import Followup from "./detail/Followup";
import Ledger from "./detail/Ledger";

const TABS = [
  { key: "overview", label: "概览" },
  { key: "findings", label: "发现清单" },
  { key: "followup", label: "追问与整改" },
  { key: "ledger", label: "历史对比" },
];

export default function DetailView({
  report,
  reports,
  onBack,
}: {
  report: ReportDetail | null;
  reports: ReportSummary[];
  onBack: () => void;
}) {
  const [tab, setTab] = useState("overview");

  if (!report) {
    return (
      <>
        <div className="empty-state">
          <div className="empty-icon"><svg viewBox="0 0 24 24"><path d="M6 3h9l5 5v13H6z" /><path d="M14 3v6h6M9 13h6M9 17h6" /></svg></div>
          <p>请先从工作台选择一份评估记录</p>
        </div>
      </>
    );
  }

  const top = topFinding(report);
  const switchTab = (next: string) => {
    setTab(next);
    // 滚动容器为外层 .view，切换 Tab 后滚动到顶部
    document.getElementById("view-detail")?.scrollTo({ top: 0 });
  };

  return (
    <>
      <div className="detail-sticky">
        <div className="detail-head">
          <button className="detail-back" title="返回工作台" onClick={onBack}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
          </button>
          <div className="detail-id">
            <div className="detail-company">{report.companyName || "未命名企业"}</div>
            <div className="detail-meta">{(report.created_at || "").slice(0, 10)}</div>
          </div>
          <div className="detail-top">
            <div className="detail-top-label">最高风险</div>
            <span className={"detail-top-badge " + (top ? severityColor(top.severity) : "green")}>
              {top ? SEVERITY_TEXT[top.severity] : "无发现"}
            </span>
          </div>
        </div>
        <nav className="detail-tabs">
          {TABS.map((t) => (
            <button key={t.key} className={"detail-tab" + (tab === t.key ? " active" : "")} onClick={() => switchTab(t.key)}>{t.label}</button>
          ))}
        </nav>
      </div>

      <div id="detailContent">
      {tab === "overview" && <Overview report={report} gotoTab={switchTab} />}
      {tab === "findings" && <Findings key={report.report_id} report={report} />}
      {tab === "followup" && <Followup report={report} />}
      {tab === "ledger" && <Ledger key={report.report_id} report={report} reports={reports} />}
      </div>
    </>
  );
}
