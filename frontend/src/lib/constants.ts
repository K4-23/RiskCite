// 展示常量：严重度、证据等级、风险域、阶段映射
export const SEVERITY_TEXT: Record<string, string> = { high: "高风险", medium: "中风险", low: "低风险" };
export const SEVERITY_COLOR: Record<string, string> = { high: "red", medium: "yellow", low: "green" };

export const GRADE_TEXT: Record<string, string> = { L1: "L1 原文核验", L2: "L2 间接佐证", L3: "L3 待核查" };
export const VERDICT_TEXT: Record<string, string> = { pass: "通过", revised: "已补证修订", needEvidence: "证据不足", misjudged: "判断不当" };

export const CHANNELS = [
  { id: "tech", name: "技术与研发", code: "01" },
  { id: "algorithm", name: "算法与模型", code: "02" },
  { id: "dataCompliance", name: "数据合规与隐私", code: "03" },
  { id: "cyber", name: "网络安全与系统", code: "04" },
  { id: "ip", name: "知识产权", code: "05" },
  { id: "commercial", name: "商业化与市场", code: "06" },
  { id: "finance", name: "融资与现金流", code: "07" },
  { id: "supplyChain", name: "供应链与地缘", code: "08" },
  { id: "ethics", name: "伦理与治理", code: "09" },
  { id: "talent", name: "组织与人才", code: "10" },
];

// 风险域选项
export const RISK_DOMAIN_OPTIONS = CHANNELS.map((c) => c.name);

export const PIPELINE_STAGES = [
  { label: "合规核查" },
  { label: "企业画像" },
  { label: "风险分析" },
  { label: "复核修订" },
  { label: "生成报告" },
];

// 后端 stage 与展示阶段的映射
export const STAGE_RUNNING_GROUP: Record<string, number> = {
  "排队中": 0,
  "合规核查": 1,
  "画像分析": 2,
  "风险域并行分析": 3, "复核修订": 3, "证据核验": 3,
  "违法情形并入": 4, "案例对照": 4, "追问清单": 4, "报告成文": 4,
};

export function runningGroupOf(stageLabel: string): number {
  const group = STAGE_RUNNING_GROUP[stageLabel];
  return group === undefined ? 0 : group;
}
