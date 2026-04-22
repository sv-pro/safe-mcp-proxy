from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.trace_store import TraceStore


def _default_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _build_trace_store(base_dir: Path) -> TraceStore:
    audit_log_path = base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"
    return TraceStore(str(audit_log_path))


def create_app(base_dir: Optional[Path] = None) -> FastAPI:
    resolved_base_dir = base_dir or _default_base_dir()
    app = FastAPI(title="safe-mcp-proxy API")
    app.state.trace_store = _build_trace_store(resolved_base_dir)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/traces")
    async def list_traces(limit: int = Query(default=100, ge=1, le=1000)) -> dict:
        traces = app.state.trace_store.last(limit)
        return {"traces": [trace.as_dict() for trace in traces]}

    @app.get("/traces/{trace_id}")
    async def get_trace(trace_id: int) -> dict:
        for trace in app.state.trace_store.all():
            if trace.id == trace_id:
                return trace.as_dict()
        raise HTTPException(status_code=404, detail="Trace not found")

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
