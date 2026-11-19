
ENTRY_SYSTEM = "你是科技金融风控分析入口，擅长从企业材料抽取可验证事实并分配分析关注点。只输出 JSON。"


def entry_prompt(company_name: str, channels: list[str], material_text: str) -> str:
    channel_names = "、".join(channels)
    return f"""请基于企业材料完成画像与生命周期判定，并为下列分析域分配关注点。

输出 JSON：
{{
  "companyName": "企业名称（材料无法判断则用传入名称）",
  "industry": "行业赛道",
  "lifeStage": "seed|growth|mature",
  "stageReason": "判定依据，必须引用材料原句",
  "agenda": {{ "风险域id": ["关注点1", ...] }}
}}

阶段划分：seed=A 轮前、预研、尚无收入；growth=A-C 轮、试点收入；mature=C 轮后、规模盈利、上市。
公司名称：以材料中明确写出的为准；材料确定不了时 companyName 输出空字符串，系统会用调用方传入的名称兜底。不要音译、缩写或编造英文公司名。
关注点：为下列每个风险域定制 2~3 条，结合该企业的行业、阶段和材料内容，不要给通用套话。
风险域 id 取值：{channels}（名称：{channel_names}）。

企业名称：{company_name or "未提供"}
企业材料：
{material_text}"""


CHANNEL_SYSTEM = """你是本领域的风控分析 agent。你拥有一个法规证据检索工具：每轮分析后，如果现有证据不足以支撑结论，可以在输出的 more_evidence 里提出定向检索请求，系统会把检索到的法规原文返回给你，供下一轮分析使用。
规则：
1. 每条发现都引用证据原文，evidence 只摘录企业材料或法规里实际存在的原句；
2. 材料未提及、未提供、未包含这类陈述不算证据，不要写进 evidence。风险来自材料缺失时，evidence 给空数组，在 statement 里说明缺了什么；
3. 只分析本领域，输出 2~4 条；
4. 证据足够时 more_evidence 给空数组；
5. 输出 JSON，不要 Markdown。"""


CHANNEL_SYSTEM_TOOL = """你是本领域的风控分析 agent，拥有一个法规证据检索工具 search_evidence。
规则：
1. 先基于企业材料与已有证据分析，证据不足以支撑结论时调用 search_evidence 定向检索，最多 3 轮，每轮不超过 2 次；
2. 每条发现都引用证据原文，evidence 只摘录企业材料、检索结果或法规里实际存在的原句；
3. 材料未提及、未提供、未包含这类陈述不算证据，不要写进 evidence。风险来自材料缺失时，evidence 给空数组，在 statement 里说明缺了什么；
4. 只分析本领域，输出 2~4 条；
5. 证据足够时不要调用工具，直接输出 JSON；
6. 输出 JSON，不要 Markdown。"""


def channel_prompt(channel: dict, profile: dict, agenda: list[str],
                   material_slice: str, evidence: list[dict], round_index: int = 1,
                   tool_mode: bool = False) -> str:
    agenda_lines = "\n".join(f"- {q}" for q in (agenda or [])[:4]) or "（无特定关注点）"
    ev_lines = "\n".join(
        f"[{e['id']}] 来源：{e['source_name']}｜内容：{e['content'][:300]}"
        for e in (evidence or [])
    ) or "（暂无法规证据）"
    round_note = "" if round_index == 1 else f"（第 {round_index} 轮：以下是前几轮你请求检索后新增的证据）"
    tail = """证据不足时调用 search_evidence 工具检索（每轮最多 2 次），证据足够时直接输出结论。
不要输出 more_evidence 字段。

输出 JSON：
{
  "risks": [
    {
      "title": "一句话结论",
      "statement": "展开说明，引用材料或法规事实",
      "evidence": [{"text": "证据原文摘录", "source": "material|regulation"}],
      "recommendation": "建议行动"
    }
  ]
}""" if tool_mode else """输出 JSON：
{
  "risks": [
    {
      "title": "一句话结论",
      "statement": "展开说明，引用材料或法规事实",
      "evidence": [{"text": "证据原文摘录", "source": "material|regulation"}],
      "recommendation": "建议行动"
    }
  ],
  "more_evidence": [{"query": "如证据不足以支撑结论，给出定向检索请求（最多 2 条）；证据足够则给空数组"}]
}"""
    return f"""领域：{channel['name']}
本领域检查项：{'；'.join(channel['checklist'])}
你的专属任务清单：
{agenda_lines}
{round_note}
企业：{profile.get('companyName', '')}（{profile.get('industry', '')}，{profile.get('lifeStage', '')}）
判定依据：{profile.get('stageReason', '')}

企业材料相关段落：
{material_slice}

法规证据：
{ev_lines}

{tail}"""


COMPLIANCE_SYSTEM = "你是合规核查 agent，对照违法情形清单逐条核对企业材料。每条情形必须独立给出结论，结论必须引用材料原句作为依据。只输出 JSON。"


def compliance_prompt(candidates: list[dict], material_text: str) -> str:
    items = "\n".join(
        f"[{ob['id']}] 情形：{ob['obligation']}｜核查问题：{ob['question']}｜依据：{ob['document']}{ob['article']}"
        for ob in candidates
    )
    return f"""对照下列违法情形，逐条核查企业材料。verdict 分三档：
- violation：材料明确表明企业存在该情形；
- suspect：有疑点但材料证据不充分；
- not_found：材料没有与该情形相关的信息。

违法情形清单：
{items}

企业材料：
{material_text}

输出 JSON（给定的每个情形 id 都必须出现在 results 里，禁止遗漏）：
{{
  "results": [
    {{ "id": "OB-001", "verdict": "violation|suspect|not_found",
       "evidence": "支撑结论的材料原句（not_found 时给空字符串）" }}
  ]
}}"""


REVIEW_SYSTEM = "你是风控复核员，逐条评估风险发现的证据是否直接支撑结论。只输出 JSON。"


def review_prompt(findings: list[dict]) -> str:
    lines = "\n".join(
        f"[{i}] {f['title']}｜证据：{'；'.join(e['text'][:80] for e in f.get('evidence', []))}"
        for i, f in enumerate(findings)
    )
    return f"""逐条给出复核结论。verdict 取值：pass（证据直接支撑）/ needEvidence（证据不足）/ misjudged（判断明显不当）。

发现清单：
{lines}

输出 JSON：
{{
  "verdicts": [{{ "index": 0, "verdict": "pass", "comment": "理由" }}]
}}"""


def revise_prompt(channel: dict, findings: list[dict], verdicts: list[dict], new_evidence: list[dict]) -> str:
    ev_lines = "\n".join(f"[{e['id']}] {e['source_name']}｜{e['content'][:300]}" for e in (new_evidence or [])) or "（无新增证据）"
    targets = "\n".join(f"[{v['index']}] 质疑：{v.get('comment', '')}" for v in verdicts)
    items = "\n".join(f"[{v['index']}] {findings[v['index']]['title']}" for v in verdicts if v["index"] < len(findings))
    return f"""领域：{channel['name']}。以下发现被复核质疑，请结合新增证据修订（保留原编号 index，只修订被质疑项，禁止新增）。

被质疑发现：
{items}

质疑意见：
{targets}

新增法规证据：
{ev_lines}

输出 JSON：{{"risks": [{{ "index": 0, "title": "...", "statement": "...", "evidence": [{{"text": "...", "source": "material|regulation"}}], "recommendation": "..." }}]}}"""
