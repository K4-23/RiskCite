# API 测试
import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.rag import retriever

client = TestClient(app)

SAMPLE = """企业名称：星衡智能科技有限公司
我们基于爬取的用户数据训练大模型，提供对话式AI服务，尚未备案。
现金流紧张，runway 9个月，尚未盈利。"""

DOC = """《个人信息保护法》第十三条：符合下列情形之一的，个人信息处理者方可处理个人信息：
（一）取得个人的同意；（二）为订立、履行个人作为一方当事人的合同所必需……"""

TEXT_DOC = "企业数据合规指引：处理个人信息应当取得授权，敏感个人信息应当取得单独同意，数据出境应当通过安全评估。"


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "1.0"
    assert "regulations" in body["kb"]


def test_kb_upload_search_delete():
    resp = client.post("/api/kb/upload", files={"file": ("pipl.md", DOC.encode("utf-8"), "text/markdown")},
                       data={"domain": "数据合规与隐私", "doc_type": "law"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["chunk_count"] >= 1

    sources = client.get("/api/kb/sources").json()
    assert len(sources) == 1

    hits = asyncio.run(retriever.retrieve("数据合规与隐私", "个人信息 单独同意"))
    assert hits and "个人信息" in hits[0]["content"]

    source_id = sources[0]["source_id"]
    assert client.delete(f"/api/kb/sources/{source_id}").status_code == 200
    assert client.get("/api/kb/sources").json() == []


CASE_DOC = """某AI公司案例：2024年该公司在未取得授权的情况下使用爬取的用户数据训练模型，
被监管部门处罚，产品下架整改三个月，核心客户流失，最终经营困难。出事前征兆：数据授权链缺失、
对单一供应商依赖度高、runway 不足 12 个月。"""


def test_case_upload_and_pipeline_reference():
    resp = client.post("/api/cases/upload",
                       files={"file": ("case-1.md", CASE_DOC.encode("utf-8"), "text/markdown")},
                       data={"domain": "数据合规与隐私", "industry": "AI", "stage": "seed",
                             "year": "2024", "outcome": "处罚+经营困难"})
    assert resp.status_code == 200, resp.text
    cases = client.get("/api/cases").json()
    assert len(cases) == 1 and cases[0]["domain"] == "数据合规与隐私"

    resp = client.post("/api/analyze", files={"files": ("bp.txt", SAMPLE.encode("utf-8"), "text/plain")},
                       data={"company_name": "星衡智能", "sync": "1"})
    assert resp.status_code == 200
    md = client.get(f"/api/reports/{resp.json()['report_id']}/markdown").text
    assert "case-1.md" in md

    assert client.delete(f"/api/cases/{cases[0]['source_id']}").status_code == 200
    assert client.get("/api/cases").json() == []


def test_analyze_sync_and_reports():
    resp = client.post("/api/analyze", files={"files": ("bp.txt", SAMPLE.encode("utf-8"), "text/plain")},
                       data={"company_name": "星衡智能", "sync": "1"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["report_id"].startswith("R-")
    assert body["summary"]["severityCounts"]["high"] >= 1

    listed = client.get("/api/reports").json()
    assert any(r["report_id"] == body["report_id"] for r in listed)

    detail = client.get(f"/api/reports/{body['report_id']}").json()
    assert detail["findings"] and detail["findings"][0]["id"].startswith("F-")

    md = client.get(f"/api/reports/{body['report_id']}/markdown").text
    assert "风险发现清单" in md and "附录 A" in md

    diff = client.get(f"/api/reports/{body['report_id']}/diff").json()
    assert diff["report_id"] == body["report_id"]

    assert client.delete(f"/api/reports/{body['report_id']}").status_code == 200
    assert client.get(f"/api/reports/{body['report_id']}").status_code == 404
    assert client.delete(f"/api/reports/{body['report_id']}").status_code == 404


def test_kb_reingest_same_chunk_count_search():
    files_a = {"file": ("alpha.md", "独有标记词 alpha_unique 的测试句。".encode("utf-8"), "text/markdown")}
    files_b = {"file": ("beta.md", "独有标记词 beta_unique 的测试句。".encode("utf-8"), "text/markdown")}
    data = {"domain": "技术与研发", "doc_type": "law"}

    first = client.post("/api/kb/upload", files=files_a, data=data)
    assert first.status_code == 200 and first.json()["chunk_count"] == 1
    hits = asyncio.run(retriever.retrieve("技术与研发", "alpha_unique"))
    assert hits and "alpha_unique" in hits[0]["content"]

    source_a = client.get("/api/kb/sources").json()[0]["source_id"]
    assert client.delete(f"/api/kb/sources/{source_a}").status_code == 200

    second = client.post("/api/kb/upload", files=files_b, data=data)
    assert second.status_code == 200 and second.json()["chunk_count"] == 1
    hits = asyncio.run(retriever.retrieve("技术与研发", "beta_unique"))
    assert hits and "beta_unique" in hits[0]["content"], "等块数重灌后 BM25 缓存未失效，检索到陈旧索引"

    source_b = client.get("/api/kb/sources").json()[0]["source_id"]
    assert client.delete(f"/api/kb/sources/{source_b}").status_code == 200
    assert client.get("/api/kb/sources").json() == []


def test_analyze_empty_text_rejected():
    resp = client.post("/api/analyze", files={"files": ("empty.txt", b"", "text/plain")},
                       data={"company_name": "空材料测试", "sync": "1"})
    assert resp.status_code == 400
    assert "提取" in resp.json()["detail"]
