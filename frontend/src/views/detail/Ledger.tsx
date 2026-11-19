// 历史对比：评估历史与台账差异
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { formatDate } from "../../lib/format";
import { SEVERITY_TEXT } from "../../lib/constants";
import { severityColor, topSeverity } from "../../lib/model";
import type { ReportDetail, ReportSummary } from "../../lib/types";

export default function Ledger({ report, reports }: { report: ReportDetail; reports: ReportSummary[] }) {
  const [historyLimit, setHistoryLimit] = useState(10);
  const [compareReportId, setCompareReportId] = useState<string | null>(null);
  const [diff, setDiff] = useState<any>(null);
  const [diffHint, setDiffHint] = useState("");
  const [diffError, setDiffError] = useState("");

  const company = report.companyName || "未命名企业";
  const companyReports = reports
    .filter((r) => (r.companyName || "未命名企业") === company)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  // 默认基准为该企业最新记录
  useEffect(() => {
    const other = companyReports.find((r) => r.report_id !== report.report_id);
    setCompareReportId(other?.report_id || null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report.report_id]);

  // 拉取差异
  useEffect(() => {
    if (compareReportId === null) {
      setDiffHint("");
      setDiff(null);
      setDiffError("");
      return;
    }
    let cancelled = false;
    setDiffHint("对比中…");
    setDiffError("");
    api(`/api/reports/${report.report_id}/diff?against=${encodeURIComponent(compareReportId)}`)
      .then((payload) => {
        if (cancelled) return;
        const base = companyReports.find((r) => r.report_id === compareReportId);
        setDiffHint(base ? `对比基准：${formatDate(base.created_at)}` : "对比已完成");
        setDiff(payload.diff || {});
      })
      .catch((error) => {
        if (!cancelled) setDiffError(error.message);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compareReportId, report.report_id]);

  const visibleReports = companyReports.slice(0, historyLimit);

  const rows = diff
    ? [
        ...(diff.added || []).map((item: any) => ({ ...item, kind: "added" })),
        ...(diff.changed || []).map((item: any) => ({ ...item, kind: "changed" })),
        ...(diff.resolved || []).map((item: any) => ({ ...item, kind: "resolved" })),
      ]
    : [];
  const KIND: Record<string, JSX.Element> = {
    added: <span className="badge red">新增</span>,
    changed: <span className="badge yellow">变化</span>,
    resolved: <span className="badge green">解除</span>,
  };

  return (
    <div className="ledger-layout">
      <div className="card ledger-companies">
        <div className="card-title-row"><h3>评估历史</h3><span className="card-hint">{companyReports.length} 次记录</span></div>
        <div className="report-list">
          {visibleReports.map((item) => (
            <button key={item.report_id}
              className={"report-item" + (item.report_id === report.report_id ? " current" : "") + (item.report_id === compareReportId ? " active" : "")}
              onClick={() => setCompareReportId(item.report_id)}>
              <div className="report-item-title">
                <span>{formatDate(item.created_at)}</span>
                {item.report_id === report.report_id ? <span className="badge">当前</span> : null}
              </div>
              <div className="report-item-meta">
                <span className={"record-light light-" + severityColor(topSeverity(item))}>{SEVERITY_TEXT[topSeverity(item)]}</span>
              </div>
            </button>
          ))}
          {companyReports.length > visibleReports.length ? (
            <button className="btn ledger-more" onClick={() => setHistoryLimit((n) => n + 10)}>加载更多历史</button>
          ) : null}
        </div>
      </div>
      <div className="ledger-main">
        <div className="card">
          <div className="card-title-row"><h3>台账差异</h3><span className="card-hint">{diffHint}</span></div>
          {compareReportId === null ? (
            <div className="empty-row">这是该企业的首次评估，后续评估将自动生成差异。</div>
          ) : diffError ? (
            <div className="empty-row">{diffError}</div>
          ) : !diff ? (
            <p className="empty-sub">加载中…</p>
          ) : rows.length === 0 ? (
            <div className="empty-row">两次评估的发现一致，无差异。</div>
          ) : (
            <div className="table-wrap">
              <table className="ledger-table">
                <thead><tr><th>类型</th><th>领域</th><th>发现</th><th>严重度</th></tr></thead>
                <tbody>
                  {rows.map((row: any, idx: number) => (
                    <tr key={idx}>
                      <td>{KIND[row.kind]}</td>
                      <td>{row.domain || ""}</td>
                      <td className="wrap">{row.title || ""}</td>
                      <td>{row.severity || ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
