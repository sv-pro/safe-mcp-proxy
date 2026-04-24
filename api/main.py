from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import safe_mcp_proxy.scenarios as _scenarios
from safe_mcp_proxy.compiler import compile_world_manifest
from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.trace_store import TraceStore


class CompareRequest(BaseModel):
    scenario: str
    worlds: List[str] = Field(min_length=1)


def _default_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _build_trace_store(base_dir: Path) -> TraceStore:
    audit_log_path = base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"
    return TraceStore(str(audit_log_path))


def _seed_if_empty(base_dir: Path) -> None:
    audit_path = base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"
    seed_path = base_dir / "seeds" / "demo.jsonl"
    if not seed_path.exists():
        return
    if audit_path.exists() and audit_path.stat().st_size > 0:
        return
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(seed_path.read_text(encoding="utf-8"), encoding="utf-8")


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
    _seed_if_empty(resolved_base_dir)
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

    @app.post("/replay/bundle")
    async def replay_bundle_endpoint(bundle: Any = Body(...)) -> dict:
        from safe_mcp_proxy.bundle_replay import replay_bundle
        try:
            return replay_bundle(bundle)
        except (KeyError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=f"Invalid bundle: {exc}")

    @app.post("/replay/{trace_id}")
    async def replay_trace(trace_id: int) -> dict:
        trace = _find_trace(app.state.trace_store, trace_id)
        replay = app.state.executor.replay(_trace_to_audit_entry(trace))
        return {
            "trace_id": trace.id,
            **replay,
            "diverged": not replay["matches"],
        }

    @app.post("/scenarios/{name}/run")
    async def run_scenario(name: str) -> dict:
        try:
            outcome = _scenarios.run(name, base_dir=resolved_base_dir)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        traces = app.state.trace_store.all()
        trace_id = traces[-1].id if traces else None
        return {
            "scenario": name,
            "trace_id": trace_id,
            "decision": outcome["result"]["decision"],
            "rule": outcome["result"]["rule"],
            "matches": outcome["matches"],
        }

    @app.post("/compare")
    async def compare_worlds(req: CompareRequest) -> dict:
        try:
            scenario = _scenarios.get(req.scenario)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        results = {}
        for world_id in req.worlds:
            try:
                executor = build_executor(resolved_base_dir, world_id=world_id)
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail=f"World not found: {world_id!r}")
            if scenario.setup is not None:
                scenario.setup(executor)
            provenance = Provenance.from_source(scenario.source_channel)
            outcome = executor.execute(scenario.tool, scenario.payload, provenance)
            results[world_id] = {
                "decision": outcome["decision"],
                "rule": outcome["rule"],
            }

        return {"scenario": req.scenario, "worlds": results}

    @app.get("/export/bundle")
    async def export_bundle(
        scenario: str = Query(...),
        trace_id: Optional[int] = Query(default=None),
    ) -> dict:
        try:
            scn = _scenarios.get(scenario)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc))

        manifest = compile_world_manifest(
            str(resolved_base_dir / "world_manifest.yaml")
        )

        if trace_id is not None:
            trace = _find_trace(app.state.trace_store, trace_id)
            trace_dicts = [trace.as_dict()]
        else:
            recent = app.state.trace_store.last(1)
            trace_dicts = [recent[0].as_dict()] if recent else []

        from datetime import datetime, timezone
        return {
            "schema_version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scenario": {
                "name": scn.name,
                "description": scn.description,
                "tool": scn.tool,
                "payload": scn.payload,
                "source_channel": scn.source_channel,
                "expected_decision": scn.expected_decision,
                "expected_rule": scn.expected_rule,
            },
            "manifest": manifest,
            "traces": trace_dicts,
        }

    @app.get("/stats")
    async def get_stats() -> dict:
        counts = Counter(trace.decision for trace in app.state.trace_store.all())
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
