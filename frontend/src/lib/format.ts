// 展示格式化工具

/**
 * ISO 时间 → "MM/DD HH:mm:ss"；空值返回 "-"。
 * 后端存的是无时区标记的 UTC 时间，必须按 UTC 解析再转本地时区显示，否则时间会偏移。
 */
export function formatDate(value: string | undefined): string {
  if (!value) return "-";
  const raw = /[Zz]$|[+-]\d{2}:?\d{2}$/.test(value) ? value : value + "Z";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(raw));
}
