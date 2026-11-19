// 应用外壳：hash 路由、报告列表、评估弹窗、toast
import { useCallback, useEffect, useRef, useState } from "react";
import Appbar from "./components/Appbar";
import NewAssessmentModal from "./components/NewAssessmentModal";
import Dashboard from "./views/Dashboard";
import DetailView from "./views/DetailView";
import KnowledgePage from "./views/KnowledgePage";
import { api } from "./lib/api";
import type { ReportDetail, ReportSummary } from "./lib/types";

function useHashRoute() {
  const [route, setRoute] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setRoute(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export default function App() {
  const route = useHashRoute();
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [view, setView] = useState<"dashboard" | "detail">("dashboard");
  const [modalOpen, setModalOpen] = useState(false);
  const [toastMsg, setToastMsg] = useState("");
  const toastTimer = useRef<number | null>(null);

  const toast = useCallback((message: string) => {
    setToastMsg(message);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToastMsg(""), 3200);
  }, []);

  const loadReports = useCallback(async () => {
    try {
      setReports(await api("/api/reports"));
    } catch (error: any) {
      toast(error.message);
    }
  }, [toast]);

  useEffect(() => { loadReports(); }, [loadReports]);

  const openReport = async (reportId: string): Promise<ReportDetail | null> => {
    try {
      const detail: ReportDetail = await api(`/api/reports/${reportId}`);
      setReport(detail);
      setView("detail");
      return detail;
    } catch (error: any) {
      toast(error.message);
      return null;
    }
  };

  // 切换视图后滚动到顶部
  useEffect(() => {
    document.getElementById(view === "dashboard" ? "view-dashboard" : "view-detail")?.scrollTo({ top: 0 });
  }, [view]);

  useEffect(() => {
    if (!route.startsWith("#/knowledge")) setView("dashboard");
  }, [route]);

  if (route.startsWith("#/knowledge")) {
    return (
      <>
        <KnowledgePage toast={toast} />
        <div className={"toast" + (toastMsg ? " show" : "")}>{toastMsg}</div>
      </>
    );
  }

  return (
    <>
      <Appbar onNewAssessment={() => setModalOpen(true)} />
      <main className="main">
        <section className={"view" + (view === "dashboard" ? " active" : "")} id="view-dashboard">
          <Dashboard
            reports={reports}
            onOpenReport={openReport}
            onDeleted={() => { loadReports(); setReport(null); setView("dashboard"); }}
            toast={toast}
          />
        </section>
        <section className={"view" + (view === "detail" ? " active" : "")} id="view-detail">
          <DetailView key={report?.report_id || "none"} report={report} reports={reports} onBack={() => setView("dashboard")} />
        </section>
      </main>
      {modalOpen && (
        <NewAssessmentModal
          onClose={() => { setModalOpen(false); loadReports(); }}
          onFinished={async (reportId) => {
            setModalOpen(false);
            const detail = await openReport(reportId);
            await loadReports();
            if (detail) toast(`「${detail.companyName || "企业"}」评估完成`);
          }}
          toast={toast}
        />
      )}
      <div className={"toast" + (toastMsg ? " show" : "")}>{toastMsg}</div>
    </>
  );
}
