from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.trace_store import TraceStore


def _default_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _build_trace_store(base_dir: Path) -> TraceStore:
    audit_log_path = base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"
    return TraceStore(str(audit_log_path))


def _find_trace(trace_store: TraceStore, trace_id: int):
    for trace in trace_store.all():
        if trace.id == trace_id:
            return trace
    raise HTTPException(status_code=404, detail="Trace not found")


def _trace_to_audit_entry(trace) -> dict:
    decision = trace.decision.value if isinstance(trace.decision, Decision) else trace.decision
    return {
        "tool": trace.tool_requested,
        "taint": trace.taint,
        "decision": decision,
        "rule": trace.rule_hit,
    }


def create_app(base_dir: Optional[Path] = None, executor: Optional[Executor] = None) -> FastAPI:
    resolved_base_dir = base_dir or _default_base_dir()
    app = FastAPI(title="safe-mcp-proxy API")
    app.state.trace_store = _build_trace_store(resolved_base_dir)
    app.state.executor = executor or build_executor(resolved_base_dir)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _ui_path = Path(__file__).resolve().parent.parent / "ui" / "index.html"

    @app.get("/", response_class=HTMLResponse)
    async def serve_ui():
        return HTMLResponse(content=_ui_path.read_text(encoding="utf-8"))

    @app.get("/traces")
    async def list_traces(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
        traces = app.state.trace_store.last(limit)
        return {"traces": [trace.as_dict() for trace in traces]}

    @app.get("/traces/{trace_id}")
    async def get_trace(trace_id: int) -> dict:
        return _find_trace(app.state.trace_store, trace_id).as_dict()

    @app.post("/replay/{trace_id}")
    async def replay_trace(trace_id: int) -> dict:
        trace = _find_trace(app.state.trace_store, trace_id)
        replay = app.state.executor.replay(_trace_to_audit_entry(trace))
        return {
            "trace_id": trace.id,
            **replay,
            "diverged": not replay["matches"],
        }

    @app.get("/stats")
    async def get_stats() -> dict:
        counts = Counter(trace.decision for trace in app.state.trace_store.all())
        # Future interaction semantics are tracked in GitHub:
        #   - #77: ASK decision and approval workflow
        #   - #78: execution modes (INTERACTIVE and BACKGROUND)
        decision_counts = {
            decision.value: counts.get(decision, 0)
            for decision in Decision
        }
        return {
            "total": sum(decision_counts.values()),
            "counts": decision_counts,
        }

    return app


app = create_app()
