// 后端数据结构

export interface Evidence {
  id?: string;
  text: string;
  grade?: string;
  source?: string | null;
  article?: string | null;
  demoted_from?: string;
  gap_check?: boolean;
}

export interface Finding {
  id: string;
  domain: string;
  title: string;
  statement?: string;
  severity: string;
  severity_reason?: string;
  evidence: Evidence[];
  obligations?: string[];
  /** 违法情形核查结论：violation（确认违法）| suspect（疑似）——决定列表徽标与报告标签 */
  obligation_verdict?: string;
  recommendation?: string;
  review?: { verdict?: string; comment?: string };
  fallback?: boolean;
}

export interface ObligationResult {
  id: string;
  domain?: string;
  obligation: string;
  question?: string;
  document?: string;
  article?: string;
  verdict: string;
  evidence?: string;
}

export interface ReportSummary {
  report_id: string;
  companyName?: string;
  created_at: string;
  lifeStage?: string;
  llmMode?: string;
  severityCounts?: Record<string, number>;
  obligationViolations?: number;
}

export interface ReportDetail extends ReportSummary {
  findings: Finding[];
  followups: { question: string; target?: string; importance?: number }[];
  obligationResults?: ObligationResult[];
  obligationViolations?: number;
  channels?: string[];
}

export interface Job {
  job_id: string;
  status: string;
  /** 最近完成的管线节点（中文标签）；正在运行的展示阶段由 STAGE_RUNNING_GROUP 映射 */
  stage: string;
  progress: number;
  error?: string;
  report_id?: string;
  /** 风险域 id → 实时状态（running/done + 证据数），仅评估进行中返回 */
  channels?: Record<string, { status: string; evidence?: number }>;
}

export interface Health {
  llm?: { model?: string; configured?: boolean };
  embedding?: { model?: string; available?: boolean };
  reranker?: { model?: string; configured?: boolean };
}

export interface KbSource {
  source_id: string;
  kb: string;
  domain?: string;
  doc_type?: string;
  industry?: string;
  original_name: string;
  chunk_count?: number;
  year?: string;
  outcome?: string;
  created_at?: string;
}
