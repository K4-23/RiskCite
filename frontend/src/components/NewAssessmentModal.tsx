// 新建评估弹窗：表单、管线进度、完成面板
import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { Job } from "../lib/types";
import { CHANNELS, PIPELINE_STAGES, runningGroupOf } from "../lib/constants";

type Stage = "form" | "running" | "done";

export default function NewAssessmentModal({
  onClose,
  onFinished,
  toast,
}: {
  onClose: () => void;
  onFinished: (reportId: string) => void;
  toast: (msg: string) => void;
}) {
  const [stage, setStage] = useState<Stage>("form");
  const [file, setFile] = useState<File | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [displayCursor, setDisplayCursor] = useState(0);
  const [pendingReportId, setPendingReportId] = useState<string | null>(null);

  const jobRef = useRef<Job | null>(null);
  const pollRef = useRef<number | null>(null);
  const walkRef = useRef<number | null>(null);

  const stopTimers = () => {
    if (pollRef.current) { window.clearInterval(pollRef.current); pollRef.current = null; }
    if (walkRef.current) { window.clearInterval(walkRef.current); walkRef.current = null; }
  };

  useEffect(() => () => stopTimers(), []);

  const startPolling = (jobId: string) => {
    pollRef.current = window.setInterval(async () => {
      try {
        const payload: Job = await api(`/api/jobs/${jobId}`);
        jobRef.current = payload;
        setJob(payload);
        if (payload.status === "failed") {
          stopTimers();
          setStage("form");
          toast(payload.error || "评估失败，请重试");
        }
      } catch {
        // 轮询容错
      }
    }, 700);

    // 展示游标每 1.5 秒前进一步
    walkRef.current = window.setInterval(() => {
      const current = jobRef.current;
      if (!current) return;
      const backendDone = current.status === "done";
      const floor = backendDone
        ? PIPELINE_STAGES.length
        : Math.min(PIPELINE_STAGES.length, runningGroupOf(current.stage || ""));
      setDisplayCursor((cursor) => (cursor < floor ? cursor + 1 : cursor));
    }, 1500);
  };

  // 游标走满后显示完成面板
  useEffect(() => {
    if (job && job.status === "done" && displayCursor >= PIPELINE_STAGES.length) {
      stopTimers();
      setPendingReportId(job.report_id || null);
      setStage("done");
    }
  }, [job, displayCursor]);

  const startAnalysis = async () => {
    if (!file) {
      toast("请先选择企业材料文件");
      return;
    }
    const form = new FormData();
    form.append("company_name", companyName.trim());
    form.append("sync", "0");
    form.append("files", file);
    setStage("running");
    setJob(null);
    setDisplayCursor(0);
    try {
      const payload = await api("/api/analyze", { method: "POST", body: form });
      startPolling(payload.job_id);
    } catch (error: any) {
      setStage("form");
      toast(error.message);
    }
  };

  const backendDone = job?.status === "done";
  const cursor = displayCursor;

  let stateText = "准备中";
  let stateSub = "正在读取材料";
  if (cursor >= PIPELINE_STAGES.length) {
    stateText = "评估完成";
    stateSub = "报告已生成，正在打开";
  } else if (cursor > 0) {
    stateText = PIPELINE_STAGES[cursor - 1].label;
    stateSub = "分析进行中";
  }

  const realChannels = job?.channels || null;

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <div className="modal-head">
          <div>
            <h2>{stage === "running" ? "评估进行中" : stage === "done" ? "评估完成" : "新建评估"}</h2>
          </div>
          <button className="icon-btn" aria-label="关闭" onClick={onClose}>×</button>
        </div>

        {stage === "form" && (
          <div>
            <div className="form-section">
              <div className="form-label">企业名称 <em>（选填）</em></div>
              <input value={companyName} onChange={(e) => setCompanyName(e.target.value)} type="text" placeholder="例：某某科技有限公司" />
            </div>
            <div className="form-section">
              <div className="form-label">企业材料</div>
              <label className={"drop-zone" + (file ? " has-file" : "")}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => { e.preventDefault(); const dropped = e.dataTransfer.files?.[0]; if (dropped) setFile(dropped); }}>
                <input type="file" accept=".pdf,.docx,.xlsx,.txt,.md,.markdown,.csv,.json,.log" hidden
                  onChange={(e) => setFile(e.target.files?.[0] || null)} />
                <div className="drop-inner">
                  <svg viewBox="0 0 24 24" width="28" height="28"><path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3" /></svg>
                  <div className="drop-title">{file ? file.name : "拖入文件，或点击选择"}</div>
                  <div className="drop-hint">Word / Excel / PDF / TXT / MD / CSV，≤ 50MB</div>
                </div>
              </label>
            </div>
            <div className="modal-actions">
              <button className="btn btn-primary btn-lg" onClick={startAnalysis}>开始评估</button>
            </div>
          </div>
        )}

        {stage === "running" && (
          <div id="analysisStageRunning">
            <div className="analysis-progress-head">
              <div className="analysis-progress-state">{stateText}</div>
              <div className="analysis-progress-sub">{stateSub}</div>
            </div>
            <div className="pipeline">
              {PIPELINE_STAGES.map((stageItem, index) => {
                let status = "pending";
                if (index < cursor) status = "done";
                if (index === cursor && !backendDone) status = "running";
                const marker = status === "done" ? "✓" : String(index + 1).padStart(2, "0");
                return (
                  <div className={"stage " + status} key={stageItem.label}>
                    <div className="stage-marker">{marker}</div>
                    <div className="stage-label">{stageItem.label}</div>
                  </div>
                );
              })}
            </div>
            <div className="role-grid">
              {CHANNELS.map((channel) => {
                const cs = realChannels && realChannels[channel.id];
                let status: string;
                if (cs) {
                  status = cs.status === "done" ? "done" : cs.status === "running" ? "running" : "waiting";
                } else if (backendDone || cursor > 2) {
                  status = "done";
                } else if (cursor === 2 && !backendDone) {
                  status = "running";
                } else {
                  status = "waiting";
                }
                const text = status === "done" ? "已完成" : status === "running" ? "执行中" : "待命";
                return (
                  <div className={"role-row " + status} key={channel.id}>
                    <div className="role-icon">{channel.code}</div>
                    <div className="role-main"><div className="role-name">{channel.name}</div></div>
                    <div className="role-state"><span className="state-dot"></span>{text}</div>
                  </div>
                );
              })}
            </div>
            <div className="modal-actions">
              <button className="btn" onClick={() => { stopTimers(); setStage("form"); }}>取消并返回</button>
            </div>
          </div>
        )}

        {stage === "done" && (
          <div id="analysisStageDone">
            <div className="done-box">
              <div className="done-icon">✓</div>
              <div className="done-title">评估完成</div>
              <div className="done-sub">报告已生成，可以查看了</div>
              <div className="done-actions">
                <button className="btn" onClick={onClose}>稍后查看</button>
                <button className="btn btn-primary" onClick={() => {
                  if (!pendingReportId) { onClose(); return; }
                  onFinished(pendingReportId);
                }}>查看报告</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
