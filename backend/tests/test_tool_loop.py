import asyncio

from app.pipeline import nodes


class _Reply:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class _Scripted:
    def __init__(self, replies):
        self.replies = list(replies)

    async def ainvoke(self, messages):
        return self.replies.pop(0)


class _FakeModel:
    def __init__(self, replies, final=None):
        self.bound = _Scripted(replies)
        self.final = _Scripted(final or [_Reply('{"risks": [{"title": "收尾", "statement": "s"}]}')])

    def bind_tools(self, tools):
        return self.bound

    async def ainvoke(self, messages):
        return await self.final.ainvoke(messages)


def _run(monkeypatch, model, fetch):
    monkeypatch.setattr(nodes.scan, "get_chat_model", lambda temperature=0.1: model)
    channel = {"name": "技术与研发", "checklist": ["技术路线"], "retrieval_queries": ["技术"]}
    return asyncio.run(nodes._tool_agent("tech", channel, {"agenda": {}}, "材料", [], fetch))


def test_tool_call_triggers_search(monkeypatch):
    model = _FakeModel([
        _Reply(tool_calls=[{"name": "search_evidence", "args": {"query": "数据出境"}, "id": "c1"}]),
        _Reply(content='{"risks": [{"title": "出境未评估", "statement": "s", "evidence": [], "recommendation": "r"}]}'),
    ])
    seen = []

    async def fetch(query, round_index):
        seen.append((query, round_index))
        return [{"source_name": "法规A", "article": "第1条", "content": "原文"}]

    cards = _run(monkeypatch, model, fetch)
    assert seen == [("数据出境", 1)]
    assert cards and cards[0]["title"] == "出境未评估"


def test_rounds_exhausted_forces_conclusion(monkeypatch):
    replies = [
        _Reply(tool_calls=[{"name": "search_evidence", "args": {"query": f"q{i}"}, "id": f"c{i}"}])
        for i in range(3)
    ]
    model = _FakeModel(replies, final=[_Reply('{"risks": [{"title": "收尾", "statement": "s"}]}')])
    seen = []

    async def fetch(query, round_index):
        seen.append(query)
        return [{"source_name": "法规", "article": "", "content": "原文"}]

    cards = _run(monkeypatch, model, fetch)
    assert len(seen) == 3
    assert cards and cards[0]["title"] == "收尾"
