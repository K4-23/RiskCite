# 管线测试
import asyncio

from app.pipeline.graph import run_pipeline

SAMPLE = """企业名称：星衡智能科技有限公司
我们是一家AI企业，基于爬取的用户数据训练大模型，提供对话式AI服务，尚未备案。
融资：天使轮，现金流紧张，runway 9个月。
核心团队来自高校，创始人持股70%，尚未盈利。
关键部件依赖进口GPU，存在断供风险。客户为2家试点客户，客户集中度高。"""


def _run():
    return asyncio.run(run_pipeline("星衡智能", SAMPLE))


def test_offline_pipeline_end_to_end():
    result = _run()
    profile = result["profile"]
    assert profile["companyName"] == "星衡智能"
    assert profile["lifeStage"] == "seed"
    assert len(result["channels"]) == 10
    assert len(result["findings"]) >= len(result["channels"])
    for f in result["findings"]:
        assert f["id"].startswith("F-") and f["severity"] in ("high", "medium", "low")
        assert f["severity_reason"].startswith("SL-")
        assert isinstance(f["evidence"], list)


def test_offline_compliance_suspect_findings():
    result = _run()
    results = {r["id"]: r for r in result["compliance_results"]}
    assert "OB-001" in results and "OB-011" in results
    assert results["OB-001"]["verdict"] == "suspect"
    assert not any(f.get("obligations") for f in result["findings"])
    assert not any(f["severity_reason"].startswith("SL-1") for f in result["findings"])


def test_report_structure():
    result = _run()
    md = result["report_md"]
    assert "# 星衡智能 · 风险发现清单" in md
    assert "## 附录 A：严重度规则表" in md
    assert "## 附录 B：风险域引用来源" in md
    assert "追问清单" in md
    assert "同类案例对照" in md and "案例库暂无数据" in md


def test_followups_present():
    result = _run()
    assert result["followups"]
    assert all("question" in f and "importance" in f for f in result["followups"])


def test_user_company_name_wins():
    import asyncio
    material = "我们做企业级数据服务，客户以银行为主。"
    result = asyncio.run(run_pipeline("测试用企业名称", material))
    assert result["profile"]["companyName"] == "测试用企业名称"
