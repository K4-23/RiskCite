// API 客户端：JSON 解析与错误提取

/** 请求后端接口。非 2xx 抛错，错误消息优先取 FastAPI 的 detail，其次业务 error 字段。 */
export async function api(path: string, options: RequestInit = {}): Promise<any> {
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `请求失败：${response.status}`);
  }
  return payload;
}
