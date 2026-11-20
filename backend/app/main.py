# FastAPI 应用入口与路由
import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import REPO_ROOT, settings
from .store import jobs as jobstore
from .store import reports as reportstore
from .store.models import SessionLocal, SourceRow, JobRow, init_db
from .pipeline.graph import run_pipeline
from .rag import ingest


def create_app() -> FastAPI:
    """应用工厂：建表、注册路由、挂前端静态资源、后台预热 BM25 索引。"""
    init_db()
    # 启动时将遗留的 running 任务改为 interrupted
    with SessionLocal() as session:
        session.query(JobRow).filter(JobRow.status == "running").update(
            {"status": "interrupted"}, synchronize_session=False)
        session.commit()
    app = FastAPI(title=settings.app_name, version="1.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    async def _save_upload(file: UploadFile) -> Path:
        suffix = Path(file.filename or "").suffix
        tmp = settings.uploads_path / f"tmp-{uuid.uuid4().hex[:8]}{suffix}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("wb") as f:
            f.write(await file.read())
        return tmp

    async def _analyze_and_save(company_name: str, material_text: str,
                                job_id: str | None = None) -> dict:
        def on_stage(stage: str, progress: int) -> None:
            if job_id:
                jobstore.set_stage(job_id, stage, progress)

        def on_channel(channel_id: str, status: str, evidence: int = 0) -> None:
            if job_id:
                jobstore.set_channel(job_id, channel_id, status, evidence)
        try:
            result = await run_pipeline(company_name, material_text, on_stage, on_channel)
            saved = reportstore.save_report(result)
            if job_id:
                jobstore.complete_job(job_id, saved["report_id"])
            return saved
        except Exception as exc:  # noqa: BLE001 任务失败时需要记录状态
            if job_id:
                jobstore.fail_job(job_id, str(exc))
            raise

    @app.get("/api/health")
    async def health():
        """配置、模型与知识库状态（前端顶栏状态灯数据源）。"""
        from .core.llm import embedding_available, llm_configured
        from .rag import store
        return {
            "app": settings.app_name, "env": settings.app_env, "version": "1.0",
            "llm": {"model": settings.llm_model, "configured": llm_configured()},
            "embedding": {"model": settings.embedding_model, "available": embedding_available()},
            "reranker": {"model": settings.reranker_model, "configured": bool(settings.reranker_api_key)},
            "kb": {"regulations": store.collection_count("regulations"), "cases": store.collection_count("cases")},
        }

    @app.post("/api/analyze")
    async def analyze(
        files: list[UploadFile] = File(...),
        company_name: str = Form(""),
        sync: str = Form("0"),
    ):
        """上传企业材料发起评估。sync=1 同步等待结果；默认异步，返回 job_id 供轮询。"""
        texts = []
        for file in files:
            tmp = await _save_upload(file)
            try:
                texts.append(ingest.extract_text(tmp, settings.material_text_limit))
            finally:
                tmp.unlink(missing_ok=True)
        material_text = "\n\n".join(t for t in texts if t.strip())
        if not material_text.strip():
            raise HTTPException(400, "未能从上传文件中提取出文本")

        if sync == "1":
            return await _analyze_and_save(company_name, material_text)
        job_id = jobstore.create_job()
        asyncio.create_task(_analyze_and_save(company_name, material_text, job_id))
        return {"job_id": job_id}

    @app.get("/api/jobs/{job_id}")
    async def job_status(job_id: str):
        """任务进度：阶段、风险域实时状态、失败原因。"""
        job = jobstore.get_job(job_id)
        if not job:
            raise HTTPException(404, "任务不存在")
        return job

    @app.get("/api/reports")
    async def reports():
        return reportstore.list_reports()

    @app.get("/api/reports/{report_id}")
    async def report_detail(report_id: str):
        detail = reportstore.get_report(report_id)
        if not detail:
            raise HTTPException(404, "报告不存在")
        return detail

    @app.get("/api/reports/{report_id}/markdown")
    async def report_markdown(report_id: str):
        md = reportstore.get_report_markdown(report_id)
        if md is None:
            raise HTTPException(404, "报告不存在")
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(md)

    @app.delete("/api/reports/{report_id}")
    async def report_delete(report_id: str):
        if not reportstore.delete_report(report_id):
            raise HTTPException(404, "报告不存在")
        return {"deleted": report_id}

    @app.get("/api/reports/{report_id}/diff")
    async def report_diff(report_id: str, against: str = ""):
        """台账对比：against 指定基准报告则现算，否则返回入库时的存量 diff。"""
        detail = reportstore.get_report(report_id)
        if not detail:
            raise HTTPException(404, "报告不存在")
        if against:
            base = reportstore.get_report(against)
            if not base:
                raise HTTPException(404, "对比报告不存在")
            from .store.reports import compute_diff
            return {"report_id": report_id, "base_report_id": against,
                    "diff": compute_diff(detail["findings"], base["findings"])}
        return {"report_id": report_id, "diff": detail.get("diff")}

    @app.post("/api/kb/upload")
    async def kb_upload(file: UploadFile = File(...), domain: str = Form(""),
                        doc_type: str = Form("law")):
        """上传法规文档入库：解析 → 条文级切块 → 向量化 → 来源登记。"""
        tmp = await _save_upload(file)
        try:
            result = await ingest.ingest_source("regulations", file.filename or "document", tmp, domain, doc_type)
            return result
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        finally:
            tmp.unlink(missing_ok=True)

    @app.get("/api/kb/sources")
    async def kb_sources():
        """法规库来源列表（案例库走 /api/cases）。"""
        with SessionLocal() as session:
            from sqlalchemy import select
            rows = session.execute(
                select(SourceRow).where(SourceRow.kb == "regulations").order_by(SourceRow.created_at.desc())
            ).scalars().all()
            return [{"source_id": r.source_id, "kb": r.kb, "domain": r.domain, "doc_type": r.doc_type,
                     "original_name": r.original_name, "chunk_count": r.chunk_count,
                     "created_at": r.created_at.isoformat()} for r in rows]

    @app.delete("/api/kb/sources/{source_id}")
    async def kb_delete(source_id: str):
        if not ingest.delete_source(source_id):
            raise HTTPException(404, "来源不存在")
        return {"deleted": source_id}

    @app.post("/api/cases/upload")
    async def case_upload(
        file: UploadFile = File(...), domain: str = Form(""), industry: str = Form(""),
        stage: str = Form(""), year: str = Form(""), outcome: str = Form(""),
    ):
        """上传案例文档入库；风险域/年份/结局留空时自动从文档内容识别。"""
        tmp = await _save_upload(file)
        try:
            return await ingest.ingest_source(
                "cases", file.filename or "case", tmp, domain=domain, doc_type="case",
                industry=industry, stage=stage, year=year, outcome=outcome)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        finally:
            tmp.unlink(missing_ok=True)

    @app.get("/api/cases")
    async def case_list():
        from sqlalchemy import select
        with SessionLocal() as session:
            rows = session.execute(
                select(SourceRow).where(SourceRow.kb == "cases").order_by(SourceRow.created_at.desc())
            ).scalars().all()
            return [{"source_id": r.source_id, "kb": r.kb, "domain": r.domain, "industry": r.industry,
                     "stage": r.stage, "year": r.year, "outcome": r.outcome,
                     "original_name": r.original_name, "chunk_count": r.chunk_count,
                     "created_at": r.created_at.isoformat()} for r in rows]

    @app.delete("/api/cases/{source_id}")
    async def case_delete(source_id: str):
        if not ingest.delete_source(source_id):
            raise HTTPException(404, "案例不存在")
        return {"deleted": source_id}

    # 托管前端构建产物
    dist_dir = REPO_ROOT / "frontend" / "dist"
    if (dist_dir / "index.html").exists():
        class NoCacheStaticFiles(StaticFiles):
            """静态资源强制协商缓存（ETag 304），文件更新后普通刷新即生效，避免开发时模块缓存旧资源。"""

            def file_response(self, *args, **kwargs):
                response = super().file_response(*args, **kwargs)
                response.headers["Cache-Control"] = "no-store"
                return response

        app.mount("/", NoCacheStaticFiles(directory=str(dist_dir), html=True), name="ui")
    else:
        print(f"[提示] 未找到前端构建产物 {dist_dir}，页面接口将返回 404；请先执行 frontend/ 下的 npm install && npm run build")

    # 启动时在后台预热 BM25 索引
    import threading

    def _warmup_kb_index() -> None:
        try:
            from .rag import retriever, store
            for name in ("regulations", "cases"):
                if store.collection_count(name) > 0:
                    retriever.prebuild_bm25(name)
        except Exception:
            pass

    threading.Thread(target=_warmup_kb_index, daemon=True).start()

    return app


app = create_app()
