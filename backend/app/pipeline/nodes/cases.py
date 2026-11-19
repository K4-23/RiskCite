from typing import TYPE_CHECKING
from ..channels import CHANNELS
from ..state import PipelineState

if TYPE_CHECKING:
    from ..graph import PipelineContext


async def case_analysis(state: PipelineState, ctx: "PipelineContext") -> dict:
    t = ctx.tracer.node_start("case_analysis")
    from ...rag import cases as case_search
    profile = state["profile"]
    domains = list(dict.fromkeys(f["domain"] for f in state["findings"]))[:3]
    results: list[dict] = []
    seen: set[str] = set()
    for domain in domains:
        channel = CHANNELS.get(domain)
        query = (channel["retrieval_queries"][0] if channel else domain)
        try:
            hits = await case_search.search_cases(
                domain=channel["domain"] if channel else domain,
                industry=profile.get("industry", ""),
                stage=profile.get("lifeStage", ""),
                query=query, top_n=3)
        except Exception as exc:  # noqa: BLE001 案例检索失败时跳过
            ctx.tracer.log("case_search_error", error=str(exc)[:120])
            hits = []
        for hit in hits:
            # 同一案件涉及多个风险域时会分域各存一份，按来源去重
            key = hit.get("source_name") or hit["id"]
            if key not in seen:
                seen.add(key)
                results.append(hit)
        if len(results) >= 3:
            break
    results = results[:3]
    ctx.tracer.node_end("case_analysis", t, {"cases": len(results)})
    return {"cases": results}