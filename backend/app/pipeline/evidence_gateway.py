# 证据网关
import time


class EvidenceGateway:
    def __init__(self, run_id: str, tracer):
        self.run_id = run_id
        self.tracer = tracer

    async def retrieve(self, agent: str, domain: str, query: str,
                       round_index: int = 0, top_n: int | None = None) -> list[dict]:
        """代理一次法规检索并登记台账：调用方（各分析/复核 agent）不得绕过本网关直连检索。"""
        started = time.time()
        items: list[dict] = []
        error = ""
        try:
            from ..rag import retriever
            items = await retriever.retrieve(domain, query, top_n=top_n)
        except Exception as exc:  # noqa: BLE001 检索失败时返回空结果
            error = str(exc)[:120]
        entry = {
            "agent": agent, "domain": domain, "round": round_index,
            "query": query, "returned": len(items),
            "latency_ms": round((time.time() - started) * 1000, 1),
        }
        if error:
            entry["error"] = error
        self.tracer.log("evidence_request", **entry)
        return items
