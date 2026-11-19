// 顶栏：品牌、状态灯、知识库入口、新建评估
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Health } from "../lib/types";

export default function Appbar({ onNewAssessment }: { onNewAssessment: () => void }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  // 每 30 秒轮询一次健康状态
  useEffect(() => {
    const check = () => {
      api("/api/health")
        .then((payload) => {
          setHealth(payload);
          setApiOk(true);
        })
        .catch(() => setApiOk(false));
    };
    check();
    const timer = window.setInterval(check, 30000);
    return () => window.clearInterval(timer);
  }, []);

  const llmOk = Boolean(health?.llm?.configured);
  const embOk = Boolean(health?.embedding?.available);
  const rerankOk = Boolean(health?.reranker?.configured);

  return (
    <header className="appbar">
      <button className="brand" onClick={() => { window.location.hash = "#/"; }}>
        <span className="brand-mark">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3 L20 7 v6 c0 4.5-3.4 7.2-8 8.5-4.6-1.3-8-4-8-8.5 V7 Z" /><path d="M8.5 12.5 11 15l4.5-5" /></svg>
        </span>
        <span className="brand-text"><b>知险有据</b><small>科创企业风险智能评估平台</small></span>
      </button>
      <div className="appbar-status">
        <span className={"status-dot" + (apiOk === true ? " ok" : apiOk === false ? " bad" : "")}></span>
        <span id="apiStatus">{apiOk === null ? "连接中" : apiOk ? "服务正常" : "服务异常"}</span>
        <span className={"status-tag" + (llmOk ? " ok" : " warn")}>{llmOk ? health?.llm?.model : "LLM 未配置"}</span>
        <span className={"status-tag" + (embOk ? " ok" : " warn")}>{embOk ? "EMB 就绪" : "离线向量"}</span>
        <span className={"status-tag" + (rerankOk ? " ok" : " warn")}>{rerankOk ? "RERANK 就绪" : "RERANK 兜底"}</span>
      </div>
      <a className="btn" href="#/knowledge">知识库</a>
      <button className="btn btn-primary" onClick={onNewAssessment}>＋ 新建评估</button>
    </header>
  );
}
