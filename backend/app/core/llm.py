import asyncio
import hashlib
import json
import re

import httpx
from langchain_openai import ChatOpenAI

from .config import settings


def llm_configured() -> bool:
    return bool(settings.llm_api_key)


def get_chat_model(temperature: float = 0.1) -> ChatOpenAI:
    """新建 ChatOpenAI 实例（OpenAI 兼容端点；失败重试 1 次，超时 120s）。"""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or None,
        temperature=temperature,
        max_retries=1,
        timeout=120,
    )


def extract_json(text: str):
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fenced = re.findall(r"```(?:json)?\s*(.+?)```", text, flags=re.S)
    candidates = [c.strip() for c in fenced] + [text]
    for cand in candidates:
        for start, end in (("{", "}"), ("[", "]")):
            i, j = cand.find(start), cand.rfind(end)
            if 0 <= i < j:
                try:
                    return json.loads(cand[i:j + 1])
                except json.JSONDecodeError:
                    continue
    return None


async def invoke_json(model: ChatOpenAI, messages: list, node: str, tracer=None):
    """调用模型并解析 JSON；失败返回 None（由调用方走兜底）。"""
    try:
        response = await model.ainvoke(messages)
        content = response.content if isinstance(response.content, str) else "".join(
            p.get("text", "") for p in response.content if isinstance(p, dict))
        parsed = extract_json(content)
        if parsed is None and tracer:
            tracer.log("json_parse_failed", node=node, sample=content[:200])
        return parsed
    except Exception as exc:  # noqa: BLE001 模型调用失败时走兜底
        if tracer:
            tracer.log("llm_error", node=node, error=str(exc)[:200])
        return None



class HashEmbeddings:
    """离线哈希向量（单字+双字滑窗），仅用于 Embedding 不可用时的兼容占位。"""

    def __init__(self, dimensions: int = 384):
        self.dimensions = dimensions

    def _vec(self, text: str) -> list[float]:
        vec = [0.0] * self.dimensions
        text = (text or "").lower()
        tokens = [text[i:i + 2] for i in range(len(text) - 1)] + list(text)
        for token in tokens:
            digest = int(hashlib.md5(token.encode()).hexdigest()[:8], 16)
            vec[digest % self.dimensions] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    async def aembed_query(self, text: str) -> list[float]:
        return self._vec(text)


class DashScopeEmbeddings:
    """Embedding 客户端：原生多模态端点与 OpenAI 兼容端点二选一（按 base_url 自动判断）。"""

    def __init__(self):
        self.base_url = settings.embedding_base_url.rstrip("/")
        self.model = settings.embedding_model
        self.api_key = settings.embedding_api_key
        self.native = "multimodal-embedding" in self.base_url

    async def _post_native(self, texts: list[str]) -> list[list[float]]:
        contents = [{"text": t} for t in texts]
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": {"contents": contents}},
            )
            resp.raise_for_status()
            payload = resp.json()
            embeddings = payload.get("output", {}).get("embeddings", [])
            if len(embeddings) != len(texts):
                raise ValueError(f"embedding count mismatch: {len(embeddings)} != {len(texts)}")
            return [e["embedding"] for e in embeddings]

    async def _post_openai(self, texts: list[str]) -> list[list[float]]:
        url = self.base_url if self.base_url.endswith("/embeddings") else f"{self.base_url}/embeddings"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            return [item["embedding"] for item in data]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        batches = [texts[i:i + 10] for i in range(0, len(texts), 10)]
        results: list[list[float]] = []
        for batch in batches:
            results.extend(await (self._post_native(batch) if self.native else self._post_openai(batch)))
            await asyncio.sleep(0.2)
        return results

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]


def embedding_available() -> bool:
    return settings.embedding_provider != "offline" and bool(settings.embedding_api_key) and bool(settings.embedding_base_url)


def get_embeddings():
    # 配置不完整时使用哈希向量
    if not embedding_available():
        return HashEmbeddings()
    return DashScopeEmbeddings()



async def rerank_documents(query: str, documents: list[str]) -> list[float] | None:
    if not (settings.reranker_api_key and settings.reranker_base_url and documents):
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.reranker_base_url,
                headers={"Authorization": f"Bearer {settings.reranker_api_key}"},
                json={"model": settings.reranker_model, "input": {"query": query, "documents": documents}},
            )
            resp.raise_for_status()
            results = resp.json()["output"]["results"]
            scores = [0.0] * len(documents)
            for item in results:
                scores[item["index"]] = float(item.get("relevance_score", 0.0))
            return scores
    except Exception:  # noqa: BLE001 重排失败时忽略
        return None
