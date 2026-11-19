// 报告数据整理：排序、证据映射、台账统计
import { SEVERITY_COLOR } from "./constants";
import type { Finding, ReportSummary } from "./types";

/** 严重度 → CSS 色系（red/yellow/green），未知按低风险处理。 */
export function severityColor(severity: string): string {
  return SEVERITY_COLOR[severity] || "green";
}

/**
 * 发现单证据 → 展示视图：补默认等级；gap_check（否定式陈述）与 article（法条定位）
 * 透传给徽标与来源行，demoted_from 折算为 demoted 布尔（自报 L1 被核验降级）。
 */
export function findingEvidence(finding: Finding | null) {
  return (finding?.evidence || []).map((entry) => ({
    id: entry.id || "",
    text: entry.text || "",
    grade: entry.grade || "L3",
    source: entry.source || null,
    article: entry.article || null,
    gap_check: Boolean(entry.gap_check),
    demoted: Boolean(entry.demoted_from),
  }));
}

/** 各严重度发现条数统计（只认 high/medium/low）。 */
export function findingCounts(findings: Finding[]) {
  const counts = { high: 0, medium: 0, low: 0 };
  for (const finding of findings || []) {
    if (counts[finding.severity] != null) counts[finding.severity] += 1;
  }
  return counts;
}

/** 记录的整体严重度：有高取高，其次中，再次低。 */
export function topSeverity(summary: ReportSummary): string {
  const counts = summary.severityCounts || {};
  if ((counts.high || 0) > 0) return "high";
  if ((counts.medium || 0) > 0) return "medium";
  return "low";
}

/** 发现按严重度降序排序（高→中→低），返回新数组不改动原列表。 */
export function sortFindings(findings: Finding[]): Finding[] {
  const order: Record<string, number> = { high: 0, medium: 1, low: 2 };
  return [...(findings || [])].sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
}

/** 报告的最高严重度发现（排序后第一条），无发现返回 null。 */
export function topFinding(report: { findings: Finding[] }): Finding | null {
  return sortFindings(report.findings)[0] || null;
}
