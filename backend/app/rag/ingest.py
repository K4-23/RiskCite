# 文档入库：解析、切块、向量化
import hashlib
import re
import shutil
import uuid
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..core.config import settings
from ..core.llm import embedding_available, get_embeddings
from ..store.models import SourceRow, SessionLocal
from ..rules.evidence import split_law_chunks
from . import store

SPLITTER = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=180)
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".md", ".markdown", ".csv", ".json", ".log"}


def _parse_docx(path: Path) -> list[str]:
    from docx import Document
    doc = Document(str(path))
    parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" ｜ ".join(cells))
    return ["\n".join(parts)] if parts else [""]


def _parse_xlsx(path: Path) -> list[str]:
    from openpyxl import load_workbook
    wb = load_workbook(str(path), data_only=True, read_only=True)
    sheets = []
    for ws in wb.worksheets:
        lines = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(v).strip() for v in row if v is not None and str(v).strip()]
            if cells:
                lines.append(" ｜ ".join(cells))
        body = "\n".join(lines)
        sheets.append(f"【工作表：{ws.title}】\n{body}" if body else f"【工作表：{ws.title}】")
    wb.close()
    return sheets


def parse_file(path: Path) -> list[str]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        return [page.extract_text() or "" for page in reader.pages]
    if ext == ".docx":
        return _parse_docx(path)
    if ext in (".xlsx", ".xlsm"):
        return _parse_xlsx(path)
    return [path.read_text(encoding="utf-8", errors="ignore")]


def extract_text(path: Path, limit: int) -> str:
    return "\n\n".join(parse_file(path))[:limit]


ALL_DOMAINS = ["技术与研发", "算法与模型", "数据合规与隐私", "网络安全与系统", "知识产权",
               "商业化与市场", "融资与现金流", "供应链与地缘", "伦理与治理", "组织与人才"]


def collection_for(kb: str) -> str:
    return "cases" if kb == "cases" else "regulations"


def _enrich_case_metadata(full_text: str, domain: str, year: str, outcome: str):
    found = [d for d in ALL_DOMAINS if d in full_text]
    if found:
        domain = "、".join(found)
    if not year:
        m_year = re.search(r"(19|20)\d{2}", full_text)
        if m_year:
            year = m_year.group()
    if not outcome:
        m_out = re.search(r"结局[:：]?\s*(.+)", full_text)
        if m_out:
            outcome = m_out.group(1).strip()[:120]
    return domain, year, outcome, (found or [domain or ""])


async def ingest_source(kb: str, original_name: str, tmp_path: Path,
                        domain: str = "", doc_type: str = "law",
                        industry: str = "", stage: str = "", year: str = "", outcome: str = "") -> dict:
    if kb not in ("regulations", "cases"):
        raise ValueError(f"未知知识库：{kb}")
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型：{ext}")

    source_id = uuid.uuid4().hex[:16]
    stored_dir = settings.uploads_path / kb
    stored_dir.mkdir(parents=True, exist_ok=True)
    stored_path = stored_dir / f"{source_id}{ext}"
    shutil.copyfile(tmp_path, stored_path)

    pages = parse_file(stored_path)
    full_text = "\n".join(p for p in pages if p.strip())
    if kb == "cases":
        domain, year, outcome, case_domains = _enrich_case_metadata(full_text, domain, year, outcome)

    chunks: list[str] = []
    metadatas: list[dict] = []

    def _add(piece: str, section: str, article: str | None = None, domain_tag: str | None = None) -> None:
        meta = {
            "kb": kb, "domain": domain_tag or domain, "doc_type": doc_type,
            "source_name": original_name, "section": section,
            "chunk_index": len(chunks),
        }
        if article:
            meta["article"] = article
        if kb == "cases":
            meta.update({"industry": industry, "stage": stage, "year": year, "outcome": outcome})
        chunks.append(piece)
        metadatas.append(meta)

    # 法规按条文切分
    law_chunks = split_law_chunks(full_text) if kb == "regulations" else None
    if law_chunks:
        for label, piece in law_chunks:
            _add(piece, label, article=label if label != "文件头" else None)
    elif kb == "cases":
        # 案例涉及多个风险域时按域各存一份
        for d in case_domains:
            for i, page in enumerate(pages):
                if not page.strip():
                    continue
                for piece in SPLITTER.split_text(page):
                    _add(piece, f"page-{i + 1}", domain_tag=d)
    else:
        for i, page in enumerate(pages):
            if not page.strip():
                continue
            for piece in SPLITTER.split_text(page):
                _add(piece, f"page-{i + 1}")
    if not chunks:
        raise ValueError("切块结果为空")

    embeddings = await get_embeddings().aembed_documents(chunks)
    embed_by = "api" if embedding_available() else "hash"

    store.upsert_chunks(collection_for(kb), source_id, chunks, metadatas, embeddings)
    _invalidate_bm25(kb)

    sha256 = hashlib.sha256(stored_path.read_bytes()).hexdigest()
    with SessionLocal() as session:
        session.add(SourceRow(
            source_id=source_id, kb=kb, domain=domain, doc_type=doc_type,
            original_name=original_name, stored_path=str(stored_path),
            sha256=sha256, chunk_count=len(chunks),
            industry=industry, stage=stage, year=year, outcome=outcome,
        ))
        session.commit()

    return {"source_id": source_id, "chunk_count": len(chunks), "embedded_by": embed_by}


def _invalidate_bm25(kb: str) -> None:
    from . import retriever
    retriever.invalidate_cache(collection_for(kb))


def delete_source(source_id: str) -> bool:
    with SessionLocal() as session:
        row = session.get(SourceRow, source_id)
        if not row:
            return False
        removed = store.delete_source(source_id, coll_names=(collection_for(row.kb),))
        _invalidate_bm25(row.kb)
        path = Path(row.stored_path)
        if path.exists():
            path.unlink()
        session.delete(row)
        session.commit()
    return True
