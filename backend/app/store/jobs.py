# 进度存于内存，同时写入 SQLite
import uuid
from datetime import datetime

from .models import JobRow, SessionLocal

JOBS: dict[str, dict] = {}


def _persist(job_id: str) -> None:
    job = JOBS.get(job_id)
    if not job:
        return
    try:
        with SessionLocal() as session:
            row = session.get(JobRow, job_id)
            if not row:
                row = JobRow(job_id=job_id)
                session.add(row)
            row.status = job["status"]
            row.stage = job["stage"]
            row.progress = job["progress"]
            row.error = job["error"]
            row.report_id = job["report_id"]
            session.commit()
    except Exception:
        pass  # 落库失败不影响进度


def create_job() -> str:
    job_id = uuid.uuid4().hex[:16]
    JOBS[job_id] = {"job_id": job_id, "status": "running", "stage": "排队中",
                    "progress": 5, "error": "", "report_id": "", "created_at": datetime.utcnow().isoformat()}
    _persist(job_id)
    return job_id


def set_stage(job_id: str, stage: str, progress: int) -> None:
    job = JOBS.get(job_id)
    if job:
        job.update(stage=stage, progress=progress)
        _persist(job_id)


def set_channel(job_id: str, channel_id: str, status: str, evidence: int = 0) -> None:
    job = JOBS.get(job_id)
    if job:
        job.setdefault("channels", {})[channel_id] = {"status": status, "evidence": evidence}


def complete_job(job_id: str, report_id: str) -> None:
    job = JOBS.get(job_id)
    if job:
        job.update(status="done", stage="完成", progress=100, report_id=report_id)
        _persist(job_id)


def fail_job(job_id: str, error: str) -> None:
    job = JOBS.get(job_id)
    if job:
        job.update(status="failed", error=error[:500])
        _persist(job_id)


def get_job(job_id: str) -> dict | None:
    return JOBS.get(job_id)
