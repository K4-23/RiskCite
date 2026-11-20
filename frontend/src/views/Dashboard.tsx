// 工作台：记录列表、搜索、筛选、删除
import { useMemo, useState } from "react";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import { SEVERITY_TEXT, SEVERITY_COLOR } from "../lib/constants";
import { topSeverity } from "../lib/model";
import type { ReportSummary } from "../lib/types";

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "high", label: "含高风险" },
  { key: "medium", label: "含中风险" },
  { key: "low", label: "含低风险" },
];

export default function Dashboard({
  reports,
  onOpenReport,
  onDeleted,
  toast,
}: {
  reports: ReportSummary[];
  onOpenReport: (reportId: string) => void;
  onDeleted: () => void;
  toast: (msg: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [limit, setLimit] = useState(20);

  const stats = useMemo(() => {
    const companies = new Set(reports.map((r) => r.companyName || "未命名企业"));
    const highCount = reports.filter((r) => topSeverity(r) === "high").length;
    return { companies: companies.size, total: reports.length, highCount };
  }, [reports]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return reports.filter((report) => {
      if (severity !== "all") {
        const counts = report.severityCounts || {};
        if (!(counts[severity] > 0)) return false;
      }
      if (q && !(report.companyName || "").toLowerCase().includes(q)) return false;
      return true;
    });
  }, [reports, query, severity]);

  const visible = rows.slice(0, limit);

  const handleDelete = async (reportId: string) => {
    if (!window.confirm("确定删除这份评估记录？删除后不可恢复。")) return;
    try {
      await api(`/api/reports/${reportId}`, { method: "DELETE" });
      toast("评估记录已删除");
      onDeleted();
    } catch (error: any) {
      toast(error.message);
    }
  };

  return (
    <>
      <div className="dashboard-head">
        <div><h1>评估工作台</h1></div>
        <div className="dashboard-stats">
          <div className="dash-stat"><b>{stats.companies}</b><span>评估企业</span></div>
          <div className="dash-stat"><b>{stats.total}</b><span>评估记录</span></div>
          <div className={"dash-stat" + (stats.highCount ? " red" : "")}><b>{stats.highCount}</b><span>含高风险</span></div>
        </div>
      </div>

      <div className="dashboard-toolbar">
        <input id="dashboardSearch" type="search" placeholder="搜索企业名称…" value={query}
          onChange={(e) => { setQuery(e.target.value); setLimit(20); }} />
        <div className="filter-chips">
          {FILTERS.map((f) => (
            <button key={f.key} className={"filter-chip" + (severity === f.key ? " active" : "")}
              onClick={() => { setSeverity(f.key); setLimit(20); }}>{f.label}</button>
          ))}
        </div>
      </div>

      <div className="record-list">
        {!visible.length ? (
          <div className="empty-state compact">
            <p>{reports.length ? "没有符合条件的评估记录" : "还没有评估记录"}</p>
            <p className="empty-sub">点击右上角「新建评估」开始第一份风险发现清单</p>
          </div>
        ) : visible.map((report) => {
          const sev = topSeverity(report);
          const counts = report.severityCounts || {};
          return (
            <div className="record-item" key={report.report_id} onClick={() => onOpenReport(report.report_id)}>
              <div className="record-main">
                <div className="record-company">{report.companyName || "未命名企业"}</div>
                <div className="record-meta">{formatDate(report.created_at)}</div>
              </div>
              <div className="record-metrics">
                <span className={"record-light light-" + SEVERITY_COLOR[sev]}>{SEVERITY_TEXT[sev]}</span>
                <span className="record-count">{counts.high || 0} 高 · {counts.medium || 0} 中 · {counts.low || 0} 低</span>
                <span className="record-count">确认违法 {report.obligationViolations || 0} 项</span>
              </div>
              <button className="record-del" onClick={(e) => { e.stopPropagation(); handleDelete(report.report_id); }}>删除</button>
            </div>
          );
        })}
      </div>

      {rows.length > visible.length && (
        <div className="load-more">
          <button className="btn" onClick={() => setLimit((n) => n + 20)}>加载更多（还剩 {rows.length - visible.length} 条）</button>
        </div>
      )}
    </>
  );
}
