# LangGraph 管线装配
import uuid

from langgraph.graph import END, START, StateGraph

from ..core.config import settings
from .trace import RunTracer
from . import nodes
from .compose import compose_report
from .state import PipelineState

STAGES = {
    "compliance_check": ("合规核查", 20), "entry_analysis": ("画像分析", 35),
    "channel_scan": ("风险域并行分析", 55), "review": ("复核修订", 70),
    "verify_evidence": ("证据核验", 80), "attach_obligations": ("违法情形并入", 85),
    "case_analysis": ("案例对照", 88), "build_followups": ("追问清单", 92),
    "compose_report": ("报告成文", 95),
}


class PipelineContext:
    """贯穿整个管线的运行期上下文：轨迹记录器、证据网关与进度回调（经 RunnableConfig 传入各节点）。"""

    def __init__(self, tracer: RunTracer, on_stage=None, on_channel=None):
        from .evidence_gateway import EvidenceGateway
        self.tracer = tracer
        self.settings = settings
        self.on_stage = on_stage
        self.on_channel = on_channel
        self.gateway = EvidenceGateway(tracer.run_id, tracer)

    def stage(self, node: str) -> None:
        if self.on_stage and node in STAGES:
            self.on_stage(STAGES[node][0], STAGES[node][1])

    def channel(self, channel_id: str, status: str, evidence: int = 0) -> None:
        if self.on_channel:
            self.on_channel(channel_id, status, evidence)


async def _compose_report(state, config):
    config["configurable"]["ctx"].stage("compose_report")
    return {"report_md": compose_report(state)}


def build_graph():
    graph = StateGraph(PipelineState)

    def wrapped(node_fn, node_name):
        async def runner(state, config):
            result = await node_fn(state, config["configurable"]["ctx"])
            config["configurable"]["ctx"].stage(node_name)
            return result
        return runner

    graph.add_node("compliance_check", wrapped(nodes.compliance_check, "compliance_check"))
    graph.add_node("entry_analysis", wrapped(nodes.entry_analysis, "entry_analysis"))
    graph.add_node("channel_scan", wrapped(nodes.channel_scan, "channel_scan"))
    graph.add_node("review", wrapped(nodes.review, "review"))
    graph.add_node("verify_evidence", wrapped(nodes.verify_evidence, "verify_evidence"))
    graph.add_node("attach_obligations", wrapped(nodes.attach_obligations, "attach_obligations"))
    graph.add_node("case_analysis", wrapped(nodes.case_analysis, "case_analysis"))
    graph.add_node("build_followups", wrapped(nodes.build_followups, "build_followups"))
    graph.add_node("compose_report", _compose_report)
    graph.add_edge(START, "compliance_check")
    graph.add_edge("compliance_check", "entry_analysis")
    graph.add_edge("entry_analysis", "channel_scan")
    graph.add_edge("channel_scan", "review")
    graph.add_edge("review", "verify_evidence")
    graph.add_edge("verify_evidence", "attach_obligations")
    graph.add_edge("attach_obligations", "case_analysis")
    graph.add_edge("case_analysis", "build_followups")
    graph.add_edge("build_followups", "compose_report")
    graph.add_edge("compose_report", END)
    return graph.compile()


_GRAPH = build_graph()


async def run_pipeline(company_name: str, material_text: str, on_stage=None, on_channel=None) -> dict:
    """执行一次评估，返回最终状态（含 report_md / findings / followups）。"""
    from ..core.llm import llm_configured

    run_id = uuid.uuid4().hex[:16]
    llm_mode = "llm" if llm_configured() else "rule-fallback"
    tracer = RunTracer(run_id, settings.logs_path, llm_mode)
    ctx = PipelineContext(tracer, on_stage, on_channel)

    initial = {
        "run_id": run_id, "company_name": company_name,
        "material_text": material_text,
        "llm_mode": llm_mode, "degradation": [],
    }
    result = await _GRAPH.ainvoke(initial, config={"configurable": {"ctx": ctx}})
    return result
