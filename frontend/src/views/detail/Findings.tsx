// 发现清单：严重度与领域筛选，左侧列表右侧详情
import { useMemo, useState } from "react";
import { CHANNELS, GRADE_TEXT, SEVERITY_TEXT, VERDICT_TEXT } from "../../lib/constants";
import { findingEvidence, severityColor, sortFindings } from "../../lib/model";
import type { Evidence, Finding, ReportDetail } from "../../lib/types";

function domainName(id: string) {
  return CHANNELS.find((c) => c.id === id)?.name || id;
}

function EvidenceBadge({ e }: { e: Evidence }) {
  if (e.gap_check) return <span className="grade-badge grade-L3">材料核对 · 未见相关描述</span>;
  return <span className={"grade-badge grade-" + e.grade}>{GRADE_TEXT[e.grade]}</span>;
}

function FindingDetail({ f, report }: { f: Finding; report: ReportDetail }) {
  const evidence = findingEvidence(f);
  const obIndex: Record<string, any> = {};
  (report.obligationResults || []).forEach((r) => { obIndex[r.id] = r; });

  return (
    <div className="card finding-detail">
      <div className="card-title-row">
        <h3>{f.title}</h3>
        <span className={"badge " + severityColor(f.severity)}>{SEVERITY_TEXT[f.severity]}</span>
      </div>
      <p className="finding-statement">{f.statement || ""}</p>
      <p className="finding-meta-line">领域：{domainName(f.domain)} ｜ 严重度依据：{f.severity_reason || ""}{f.fallback ? " ｜ 规则兜底产出" : ""}</p>

      <div className="card-title-row sub"><h4>证据链</h4>{evidence.length >= 2 ? <span className="card-hint">{evidence.length} 条</span> : null}</div>
      {evidence.length ? evidence.map((e, idx) => (
        <div className="evidence-row" key={idx}>
          <div className="evidence-head">
            <EvidenceBadge e={e} />
            {e.source && !e.gap_check ? (
              <span className="evidence-source">来源：{e.source}{e.article ? " · " + e.article : ""}</span>
            ) : null}
            {e.demoted ? <span className="tag warn">自报 L1 已降级</span> : null}
          </div>
          <div className="evidence-text">{e.text}</div>
        </div>
      )) : <p className="empty-sub">无证据引用</p>}

      {(f.obligations || []).length ? (
        <>
          <div className="card-title-row sub"><h4>违法情形核查</h4></div>
          {f.obligations!.map((id) => {
            const r = obIndex[id];
            if (!r) return <div className="evidence-row" key={id}><span className="tag danger">{id}</span></div>;
            const vLabel = r.verdict === "violation" ? "确认违法" : r.verdict === "suspect" ? "疑似" : "未发现";
            return (
              <div className={"evidence-row" + (r.verdict === "violation" ? " danger" : "")} key={id}>
                <div className="evidence-head">
                  <span className={"tag " + (r.verdict === "violation" ? "danger" : "")}>{id} · {vLabel}</span>
                  <b>{r.obligation}</b>
                </div>
                <div className="evidence-text">依据：{r.document || ""}{r.article || ""}</div>
                {r.evidence ? <div className="evidence-text">材料原句：{r.evidence}</div> : null}
              </div>
            );
          })}
        </>
      ) : null}

      {f.recommendation ? (
        <>
          <div className="card-title-row sub"><h4>建议行动</h4></div>
          <p className="finding-recommendation">{f.recommendation}</p>
        </>
      ) : null}

      {f.review?.comment ? (
        <>
          <div className="card-title-row sub"><h4>复核意见</h4></div>
          <p className="finding-review">{f.review.comment}（{VERDICT_TEXT[f.review.verdict || ""] || f.review.verdict || ""}）</p>
        </>
      ) : null}
    </div>
  );
}

export default function Findings({ report }: { report: ReportDetail }) {
  const [severityFilter, setSeverityFilter] = useState("all");
  const [domainFilter, setDomainFilter] = useState("all");

  const all = useMemo(() => sortFindings(report.findings), [report]);
  const counts: Record<string, number> = { high: 0, medium: 0, low: 0 };
  const domainCounts: Record<string, number> = {};
  for (const f of all) {
    counts[f.severity] = (counts[f.severity] || 0) + 1;
    domainCounts[f.domain] = (domainCounts[f.domain] || 0) + 1;
  }
  const domains = Object.keys(domainCounts);
  const filtered = all.filter((f) =>
    (severityFilter === "all" || f.severity === severityFilter) &&
    (domainFilter === "all" || f.domain === domainFilter));
  // 手动选择优先，缺省取筛选结果第一条
  const [manualSelected, setManualSelected] = useState<string | null>(null);
  const selectedFinding: Finding | null = filtered.find((f) => f.id === manualSelected) || filtered[0] || all[0] || null;

  const sevOptions: [string, string][] = [
    ["all", `全部严重度（${all.length}）`],
    ["high", `高风险（${counts.high}）`],
    ["medium", `中风险（${counts.medium}）`],
    ["low", `低风险（${counts.low}）`],
  ];
  const domainOptions: [string, string][] = [
    ["all", `全部领域（${all.length}）`],
    ...domains.map((d): [string, string] => [d, `${domainName(d)}（${domainCounts[d]}）`]),
  ];

  return (
    <div className="risks-layout">
      <div className="risks-list-col">
        <div className="list-filters">
          <select title="按严重度筛选" value={severityFilter}
            onChange={(e) => { setSeverityFilter(e.target.value); setManualSelected(null); }}>
            {sevOptions.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
          <select title="按领域筛选" value={domainFilter}
            onChange={(e) => { setDomainFilter(e.target.value); setManualSelected(null); }}>
            {domainOptions.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
        </div>
        <div className="risks-list">
          {filtered.length ? filtered.map((f) => (
            <button className={"risk-item" + (selectedFinding && selectedFinding.id === f.id ? " active" : "")}
              key={f.id} onClick={() => setManualSelected(f.id)}>
              <div className="risk-item-head">
                <span className={"light-dot " + severityColor(f.severity)}></span>
                <span className="risk-item-title" title={f.title}>{f.title}</span>
              </div>
              <div className="risk-item-meta">{domainName(f.domain)} · {SEVERITY_TEXT[f.severity]}{f.obligation_verdict === "violation" ? " · 确认违法" : f.obligation_verdict === "suspect" ? " · 疑似情形" : ""}</div>
            </button>
          )) : <div className="empty-state compact"><p>当前筛选下没有发现</p></div>}
        </div>
      </div>
      <div className="risks-detail-col">
        {selectedFinding ? <FindingDetail f={selectedFinding} report={report} /> : null}
      </div>
    </div>
  );
}
