# 混合检索：向量加 BM25，融合后重排
import jieba
from rank_bm25 import BM25Okapi

from ..core.config import settings
from ..core.llm import embedding_available, get_embeddings, rerank_documents
from . import store

_bm25_cache: dict[str, tuple[int, BM25Okapi, list[str], list[str], list[dict]]] = {}
_pool_cache: dict[tuple, dict] = {}


def _tokenize(text: str) -> list[str]:
    return [t for t in jieba.lcut(text or "") if t.strip()]


def _bm25_for(coll_name: str):
    coll = store.collection(coll_name)
    count = coll.count()
    cached = _bm25_cache.get(coll_name)
    if cached and cached[0] == count:
        return cached
    data = coll.get(include=["documents", "metadatas"])
    ids = data["ids"]
    docs = data["documents"] or []
    metas = data["metadatas"] or []
    corpus = [_tokenize(d) for d in docs]
    bm25 = BM25Okapi(corpus) if corpus else None
    entry = (count, bm25, ids, docs, metas)
    _bm25_cache[coll_name] = entry
    return entry


def _pool_for(coll_name: str, where: dict | None) -> dict:
    key = (coll_name, tuple(sorted((where or {}).items())))
    cached = _pool_cache.get(key)
    count = store.collection_count(coll_name)
    if cached and cached["count"] == count:
        return cached["data"]
    data = store.get_all(coll_name, where=where)
    _pool_cache[key] = {"count": count, "data": data}
    return data


def rrf_fuse(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item_id in enumerate(ranked):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank + 1)
    return [i for i, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]


async def hybrid_ranked_lists(coll_name: str, query: str, pool: set[str],
                              vector_where: dict | None = None) -> list[list[str]]:
    ranked_lists: list[list[str]] = []

    # BM25 词法检索路
    _, bm25, ids, _, _ = _bm25_for(coll_name)
    if bm25 and query:
        scores = bm25.get_scores(_tokenize(query))
        ranked = [i for _, i in sorted(zip(scores, ids), key=lambda p: p[0], reverse=True)]
        ranked_lists.append([i for i in ranked if i in pool][:20])

    # 向量语义路
    if embedding_available() and query:
        embedding = await get_embeddings().aembed_query(query)
        res = store.collection(coll_name).query(
            query_embeddings=[embedding], where=vector_where, n_results=min(20, len(pool)))
        for hit_ids in res["ids"]:
            ranked_lists.append([i for i in hit_ids if i in pool])
    return ranked_lists


def prebuild_bm25(coll_name: str = "regulations") -> int:
    entry = _bm25_for(coll_name)
    return entry[0]


def invalidate_cache(coll_name: str) -> None:
    _bm25_cache.pop(coll_name, None)
    for key in [k for k in _pool_cache if k[0] == coll_name]:
        _pool_cache.pop(key, None)


def clear_caches() -> None:
    _bm25_cache.clear()
    _pool_cache.clear()


async def retrieve(domain: str, query: str, top_n: int | None = None) -> list[dict]:
    """按风险域检索法规证据。返回 [{id, content, source_name, score}]。"""
    coll_name = "regulations"
    top_n = top_n or settings.evidence_top_n
    where = {"domain": domain} if domain else None

    data = _pool_for(coll_name, where)
    if not data["ids"] and domain:
        where = None  # 两路检索范围保持一致
        data = _pool_for(coll_name, where)  # 该域无文档时检索全库
    if not data["ids"]:
        return []

    candidates: dict[str, dict] = {
        cid: {"id": cid, "content": doc or "", "source_name": (meta or {}).get("source_name", "unknown"),
              "domain": (meta or {}).get("domain", ""), "article": (meta or {}).get("article")}
        for cid, doc, meta in zip(data["ids"], data["documents"] or [], data["metadatas"] or [])
    }

    ranked_lists = await hybrid_ranked_lists(coll_name, query, set(candidates.keys()), vector_where=where)

    fused = rrf_fuse(ranked_lists)[: settings.rerank_top_n]
    if not fused:
        return []

    fused_docs = [candidates[i]["content"] for i in fused]
    scores = await rerank_documents(query, fused_docs)
    if scores is None:
        scores = [1.0 / (rank + 1) for rank in range(len(fused))]

    ordered = sorted(zip(fused, scores), key=lambda p: p[1], reverse=True)[:top_n]
    return [
        {**candidates[i], "score": round(float(s), 4)}
        for i, s in ordered
    ]
