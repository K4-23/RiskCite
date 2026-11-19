from . import store
from .retriever import hybrid_ranked_lists, rrf_fuse


def _where(conds: dict) -> dict | None:
    if not conds:
        return None
    if len(conds) == 1:
        return dict(conds)
    return {"$and": [{k: v} for k, v in conds.items()]}


async def search_cases(domain: str = "", industry: str = "", stage: str = "",
                       query: str = "", top_n: int = 3) -> list[dict]:
    """检索同类案例。过滤条件逐级放宽：全条件 → 去行业 → 去阶段 → 去域。"""
    coll_name = "cases"
    if store.collection_count(coll_name) == 0:
        return []

    base: dict = {}
    if domain:
        base["domain"] = domain
    if stage:
        base["stage"] = stage
    if industry:
        base["industry"] = industry
    conditions: list[dict | None] = [_where(base)]
    keys = list(base.keys())
    for drop in ("industry", "stage", "domain"):
        if drop in base:
            keys = [k for k in keys if k != drop]
            conditions.append(_where({k: base[k] for k in keys}))
    conditions.append(None)

    data = {}
    for where in conditions:
        data = store.get_all(coll_name, where=where)
        if data["ids"]:
            break
    if not data["ids"]:
        return []

    candidates: dict[str, dict] = {
        cid: {"id": cid, "content": doc or "",
              "source_name": (meta or {}).get("source_name", "unknown"),
              "domain": (meta or {}).get("domain", ""), "stage": (meta or {}).get("stage", ""),
              "industry": (meta or {}).get("industry", ""), "outcome": (meta or {}).get("outcome", "")}
        for cid, doc, meta in zip(data["ids"], data["documents"] or [], data["metadatas"] or [])
    }

    ranked_lists = await hybrid_ranked_lists(
        coll_name, query, set(candidates.keys()), vector_where=conditions[0])
    fused = rrf_fuse(ranked_lists)[:top_n] if ranked_lists else list(candidates.keys())[:top_n]
    return [candidates[i] for i in fused]
