# 运行轨迹写入 JSONL
import json
import time
from pathlib import Path


class RunTracer:
    """单次评估的事件记录器：节点起止、检索请求、LLM 异常等全部落 JSONL。"""

    def __init__(self, run_id: str, logs_dir: Path, llm_mode: str = "llm"):
        self.run_id = run_id
        self.llm_mode = llm_mode
        self.file = Path(logs_dir) / "runs" / f"{run_id}.jsonl"
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.events: list[dict] = []
        self._write({"event": "run_start", "run_id": run_id, "llm_mode": llm_mode, "ts": time.time()})

    def _write(self, event: dict) -> None:
        self.events.append(event)
        with self.file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def node_start(self, node: str) -> float:
        self._write({"event": "node_start", "node": node, "ts": time.time()})
        return time.time()

    def node_end(self, node: str, started: float, detail: dict | None = None) -> None:
        self._write({
            "event": "node_end", "node": node,
            "elapsed_ms": round((time.time() - started) * 1000),
            "detail": detail or {}, "ts": time.time(),
        })

    def log(self, event: str, **fields) -> None:
        self._write({"event": event, **fields, "ts": time.time()})
