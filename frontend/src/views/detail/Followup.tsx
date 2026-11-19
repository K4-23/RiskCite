// 追问与整改清单
import type { ReportDetail } from "../../lib/types";

const IMPORTANCE_LABEL: Record<number, string> = { 1: "紧急", 2: "重要", 3: "补充" };

export default function Followup({ report }: { report: ReportDetail }) {
  const followups = report.followups || [];
  return (
    <div className="followup-page">
      <div className="card">
        <div className="card-title-row">
          <h3>追问清单</h3>
          <span className="card-hint">回答后可再次评估，系统将与本次结果自动对比</span>
        </div>
        {followups.length ? followups.map((item, index) => (
          <div className="evidence-row" key={index}>
            <div className="evidence-head">
              <span className="grade-badge">{String(index + 1).padStart(2, "0")}</span>
              <span className={"tag " + (item.importance === 1 ? "danger" : "")}>{IMPORTANCE_LABEL[item.importance || 3] || "补充"}</span>
            </div>
            <div className="evidence-text">{item.question}</div>
          </div>
        )) : <p className="empty-sub">本次无追问事项</p>}
      </div>
    </div>
  );
}
