// 知识库页：上传与来源管理
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { RISK_DOMAIN_OPTIONS } from "../lib/constants";
import type { KbSource } from "../lib/types";

type Kb = "regulations" | "standards" | "cases";

const SEGMENTS: { key: Kb; label: string }[] = [
  { key: "regulations", label: "法规库" },
  { key: "standards", label: "标准库" },
  { key: "cases", label: "案例库" },
];

function sourceNumber(source: KbSource) {
  const m = (source.original_name || "").match(/^(\d+)/);
  return m ? parseInt(m[1], 10) : 9999;
}

function delUrl(kb: Kb, sourceId: string) {
  return kb === "cases" ? `/api/cases/${sourceId}` : `/api/kb/sources/${sourceId}`;
}

function cleanTitle(name: string) {
  return (name || "")
    .replace(/\.(md|markdown|txt|pdf|csv|json|log)$/i, "")
    .replace(/^案例\d+-/, "")
    .replace(/^\d+-/, "");
}

export default function KnowledgePage({ toast }: { toast: (msg: string) => void }) {
  const [kb, setKb] = useState<Kb>("regulations");
  const [sources, setSources] = useState<KbSource[]>([]);
  const [page, setPage] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [meta, setMeta] = useState({ domain: "", docType: "law", industryStd: "" });

  const loadSources = async () => {
    const [regSources, caseSources] = await Promise.all([api("/api/kb/sources"), api("/api/cases")]);
    setSources([...regSources, ...caseSources]);
  };

  useEffect(() => {
    loadSources().catch((error) => toast(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isCases = kb === "cases";
  const isStd = kb === "standards";

  const all = sources.filter((s) => s.kb === kb).sort((a, b) => sourceNumber(a) - sourceNumber(b));
  const pageSize = 10;
  const totalPages = Math.max(1, Math.ceil(all.length / pageSize));
  const current = Math.min(Math.max(page, 1), totalPages);
  const rows = all.slice((current - 1) * pageSize, current * pageSize);

  const handleUpload = async () => {
    if (!file) {
      toast("请先选择要上传的文档");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    setUploading(true);
    try {
      if (kb === "cases") {
        await api("/api/cases/upload", { method: "POST", body: form });
        toast("案例已入库，风险域与年份已自动识别");
      } else {
        form.append("kb", kb);
        form.append("domain", meta.domain);
        if (kb === "standards") form.append("industry", meta.industryStd || "");
        if (kb === "regulations") form.append("doc_type", meta.docType);
        const payload = await api("/api/kb/upload", { method: "POST", body: form });
        toast(`已入库：${payload.chunk_count} 个分片`);
      }
      setFile(null);
      setUploadOpen(false);
      await loadSources();
    } catch (error: any) {
      toast(error.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (source: KbSource) => {
    if (!window.confirm("删除该来源将同步清理原文、元数据与向量，确认？")) return;
    try {
      await api(delUrl(kb, source.source_id), { method: "DELETE" });
      toast("来源已删除");
      await loadSources();
    } catch (error: any) {
      toast(error.message);
    }
  };

  return (
    <main className="main">
      <section className="view active">
        <div className="kb-toolbar-row">
          <a className="kb-back" href="#/">← 返回工作台</a>
          <div className="knowledge-toolbar">
            <div className="segmented">
              {SEGMENTS.map((seg) => (
                <button key={seg.key} className={"segment" + (kb === seg.key ? " active" : "")}
                  onClick={() => { setKb(seg.key); setPage(1); setFile(null); }}>{seg.label}</button>
              ))}
            </div>
            <button className="btn btn-primary" onClick={() => setUploadOpen(true)}>＋ 上传文档</button>
          </div>
        </div>

        <div className="card knowledge-sources-card">
          <div className="card-title-row">
            <h3>{isCases ? "案例库来源" : isStd ? "标准库来源" : "法规库来源"}</h3>
            <span className="card-hint">共 {all.length} 个文档</span>
          </div>
          <div className="source-list">
            {!all.length ? (
              <div className="empty-row">{isCases
                ? "案例库为空。上传真实案例文档即可，风险域、年份、结局由系统从内容自动识别"
                : "库为空。上传文档后分析线即可引用依据原文"}</div>
            ) : rows.map((source) => {
              const metaText = isCases
                ? [source.domain, source.year, source.outcome].filter(Boolean).join(" · ")
                : isStd
                  ? (source.industry || "所属行业未识别")
                  : (source.domain || "");
              return (
                <div className="source-row" key={source.source_id}>
                  <div className="source-main">
                    <div className="source-title">{cleanTitle(source.original_name)}</div>
                    <div className="source-meta">{metaText}</div>
                  </div>
                  <div className="row-actions">
                    <button className="btn btn-sm" onClick={() => handleDelete(source)}>删除</button>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="kb-pagination">
            {totalPages > 1 ? (
              <>
                <button className="btn btn-sm" disabled={current <= 1} onClick={() => setPage(current - 1)}>上一页</button>
                <span className="kb-page-info">第 {current} / {totalPages} 页</span>
                <button className="btn btn-sm" disabled={current >= totalPages} onClick={() => setPage(current + 1)}>下一页</button>
              </>
            ) : null}
          </div>
        </div>
      </section>

      {uploadOpen && (
        <div className="modal-backdrop">
          <div className="modal">
            <div className="modal-head">
              <h2>上传到{isCases ? "案例库" : isStd ? "标准库" : "法规库"}</h2>
              <button className="icon-btn" aria-label="关闭" onClick={() => setUploadOpen(false)}>×</button>
            </div>
            <label className={"drop-zone" + (file ? " has-file" : "")}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); const dropped = e.dataTransfer.files?.[0]; if (dropped) setFile(dropped); }}>
              <input type="file" accept=".pdf,.docx,.xlsx,.txt,.md,.markdown,.csv,.json,.log" hidden
                onChange={(e) => setFile(e.target.files?.[0] || null)} />
              <div className="drop-inner">
                <svg viewBox="0 0 24 24" width="26" height="26"><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>
                <div className="drop-title">{file ? file.name : isCases ? "拖入案例文档，或点击选择" : "拖入法规/标准文档，或点击选择"}</div>
                <div className="drop-hint">上传后自动切块、向量化并进入检索库</div>
              </div>
            </label>

            {!isCases && (
              <div className="form-section">
                <div className="form-label">风险域标签</div>
                <select value={meta.domain} onChange={(e) => setMeta({ ...meta, domain: e.target.value })}>
                  <option value="">（未分类）</option>
                  {RISK_DOMAIN_OPTIONS.map((d) => <option key={d} value={d}>{d}</option>)}
                </select>
                {!isStd && (
                  <>
                    <div className="form-label">文档类型</div>
                    <select value={meta.docType} onChange={(e) => setMeta({ ...meta, docType: e.target.value })}>
                      <option value="law">法规</option>
                      <option value="standard">标准</option>
                      <option value="playbook">方法清单</option>
                    </select>
                  </>
                )}
                {isStd && (
                  <>
                    <div className="form-label">所属行业（选填，未填则按文件名自动识别）</div>
                    <input type="text" placeholder="例：人工智能 / 半导体 / 医药"
                      value={meta.industryStd} onChange={(e) => setMeta({ ...meta, industryStd: e.target.value })} />
                  </>
                )}
              </div>
            )}

            <div className="modal-actions">
              <button className="btn btn-primary" disabled={!file || uploading} onClick={handleUpload}>
                {uploading ? "入库中…" : "入库"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
