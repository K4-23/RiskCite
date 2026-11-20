# 规则测试
from app.rules.evidence import grade_evidence
from app.rules.evidence import locate_article, split_law_chunks
from app.rules.evidence import is_negative_evidence, weighted_overlap
from app.rules.obligations import recall_obligations
from app.rules.severity import classify


def test_obligation_recall_hit():
    text = "我们提供对话式AI服务，尚未备案，用户量增长很快。"
    hits = recall_obligations(text)
    ids = {h["id"] for h in hits}
    assert "OB-001" in ids
    ob = next(h for h in hits if h["id"] == "OB-001")
    assert "对话式AI" in ob["evidence_line"]


def test_obligation_recall_exempt():
    text = "我们的生成式AI服务已依法完成备案，备案编号已公示。"
    hits = recall_obligations(text)
    assert not any(h["id"] == "OB-001" for h in hits)


def test_obligation_recall_multi():
    hits = recall_obligations("基于爬取的用户数据训练大模型，且关键部件依赖断供风险高的进口设备。")
    ids = {h["id"] for h in hits}
    assert "OB-011" in ids and "OB-015" in ids


def test_evidence_l1_from_candidates():
    candidates = [{"id": "c1", "content": "处理敏感个人信息应当取得个人的单独同意。", "source_name": "个保法.md"}]
    graded = grade_evidence([{"text": "处理敏感个人信息应当取得个人的单独同意"}], candidates, "")
    assert graded[0]["grade"] == "L1" and graded[0]["source"] == "个保法.md"


def test_evidence_l1_from_company_text():
    company = "我们基于爬取的用户数据训练大模型，数据来源为公开网络。"
    graded = grade_evidence([{"text": "基于爬取的用户数据训练大模型"}], [], company)
    assert graded[0]["grade"] == "L1" and graded[0]["source"] == "企业材料"


def test_evidence_l1_demoted_when_unmatched():
    graded = grade_evidence([{"text": "这句话在材料与法规里都找不到", "grade": "L1"}], [], "完全无关的企业材料内容")
    assert graded[0]["grade"] == "L2" and graded[0].get("demoted_from") == "L1"


def test_claimed_source_not_propagated_on_unverified():
    graded = grade_evidence([{"text": "一句无法核实的断言。", "source": "regulation"}], [], "")
    assert graded[0]["grade"] == "L3" and graded[0]["source"] is None
    graded2 = grade_evidence([{"text": "另一句无法核实的断言。", "source": "material"}], [], "与该断言无关的材料文本。")
    assert graded2[0]["grade"] == "L3" and graded2[0]["source"] is None


def test_evidence_l3_needs_check():
    graded = grade_evidence([{"text": "完全没有任何匹配的句子"}], [], "完全无关的企业材料内容")
    assert graded[0]["grade"] == "L3"


def _finding(**kw):
    base = {"id": "F-1", "domain": "tech", "title": "t", "statement": "", "evidence": [], "obligations": []}
    base.update(kw)
    return base


def test_severity_sl1_obligation_violation():
    severity, reason = classify(_finding(obligations=["OB-001"], obligation_verdict="violation"))
    assert severity == "high" and "SL-1" in reason


def test_severity_suspect_not_high():
    suspect = _finding(obligations=["OB-001"], obligation_verdict="suspect",
                       evidence=[{"grade": "L1"}])
    severity, reason = classify(suspect)
    assert severity != "high" and "SL-1" not in reason

    no_evidence = _finding(obligations=["OB-001"], obligation_verdict="suspect",
                           evidence=[{"grade": "L3"}])
    assert classify(no_evidence)[0] == "low"


def test_severity_sl2_l1_survival():
    f = _finding(evidence=[{"grade": "L1"}], statement="关键部件断供将导致停产")
    severity, reason = classify(f)
    assert severity == "high" and "SL-2" in reason


def test_severity_sl3_medium():
    severity, _ = classify(_finding(evidence=[{"grade": "L2"}]))
    assert severity == "medium"


def test_severity_sl4_low():
    severity, _ = classify(_finding(evidence=[{"grade": "L3"}]))
    assert severity == "low"


LAW_SAMPLE = """第一条 为了规范处理活动。
第二条 本法适用于个人信息处理。
第三条 敏感信息须单独同意。
第四条 出境须安全评估。
第五条 违者依法处罚。
第六条 附则。"""


def test_split_law_chunks_by_article():
    chunks = split_law_chunks(LAW_SAMPLE)
    assert chunks and len(chunks) >= 6
    labels = [c[0] for c in chunks]
    assert any(c[0] == "第三条" for c in chunks)


def test_split_law_chunks_too_few_articles_returns_none():
    assert split_law_chunks("这不是法规，没有条文结构。") is None


def test_locate_article_in_chunk():
    chunk = """第十二条 个人信息处理者应当履行下列义务：不得超出授权范围处理。
第十三条 处理敏感个人信息应当取得个人的单独同意，并采取严格保护措施。
第十四条 任何组织不得非法收集使用个人信息。"""
    assert locate_article(chunk, "处理敏感个人信息应当取得个人的单独同意") == "第十三条"


def test_evidence_article_from_metadata_and_location():
    meta_cand = [{"id": "c1", "content": "第十三条 处理敏感个人信息应当取得个人的单独同意并严格保护。",
                  "source_name": "个保法", "article": "第十三条"}]
    graded = grade_evidence([{"text": "应当取得个人的单独同意并严格保护"}], meta_cand, "")
    assert graded[0]["article"] == "第十三条"

    no_meta = [{"id": "c2", "content": "第十三条 处理敏感个人信息应当取得个人的单独同意并严格保护。",
                "source_name": "个保法"}]
    graded2 = grade_evidence([{"text": "应当取得个人的单独同意并严格保护"}], no_meta, "")
    assert graded2[0]["article"] == "第十三条"


def test_negative_evidence_not_l1():
    cand = [{"id": "c1", "content": "企业材料相关段落中未包含关于智能电视端合作模式的描述",
             "source_name": "企业材料"}]
    graded = grade_evidence([{"text": "企业材料相关段落中未包含关于智能电视端合作模式、技术集成方案的任何描述"}],
                            cand, "企业材料相关段落中未包含关于智能电视端合作模式的描述")
    assert graded[0]["grade"] == "L3" and graded[0].get("gap_check") is True
    assert graded[0]["source"] == "材料核对"


def test_positive_evidence_still_l1():
    company = "公司已建立数据授权台账并完成算法备案。"
    graded = grade_evidence([{"text": "公司已建立数据授权台账并完成算法备案"}], [], company)
    assert graded[0]["grade"] == "L1"


def test_is_negative_evidence_hints():
    assert is_negative_evidence("当前未提供任何高并发压力测试报告")
    assert is_negative_evidence("材料中未提及该事项")
    assert is_negative_evidence("TRL成熟度无法验证")
    assert not is_negative_evidence("公司已取得算法备案编号")


def test_weighted_overlap_chinese_threshold():
    assert weighted_overlap("个人信息保护规定", "个人信息保护规定") == 8
    assert weighted_overlap("个人信息保护法", "个人信息保护法") == 7


def test_weighted_overlap_english_threshold():
    assert weighted_overlap("personal data must be", "personal data must be") == 8
    assert weighted_overlap("personal data must", "personal data must") == 6


def test_weighted_overlap_mixed():
    assert weighted_overlap("用户 data 的 privacy 保护", "用户 data 的 privacy 保护") == 9
    assert weighted_overlap("privacy policy 未披露", "privacy policy 未披露") == 7


def test_english_quote_matches_source():
    source = "We process personal data must be handled lawfully."
    graded = grade_evidence([{"text": "personal data must be"}],
                            [{"id": "c1", "content": source, "source_name": "law.md"}], "")
    assert graded[0]["grade"] == "L1"


def test_short_english_fragment_not_enough():
    source = "We process personal data must be handled lawfully."
    graded = grade_evidence([{"text": "personal data must"}],
                            [{"id": "c1", "content": source, "source_name": "law.md"}], "")
    assert graded[0]["grade"] == "L3"
