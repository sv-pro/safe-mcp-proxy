from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

import safe_mcp_proxy.scenarios as _scenarios
from safe_mcp_proxy.compiler import compile_world_manifest
from safe_mcp_proxy.decision import Decision
from safe_mcp_proxy.executor import Executor
from safe_mcp_proxy.integrations.gemini_adapter import GeminiAdapter, GeminiAdapterError
from safe_mcp_proxy.integrations.gemini_proxy import GeminiProxy
from safe_mcp_proxy.main import build_executor
from safe_mcp_proxy.provenance import Provenance
from safe_mcp_proxy.trace_store import TraceStore
from safe_mcp_proxy.world_controller import WorldController, WorldNotFoundError


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


async def _sse_stream(audit_path: Path):
    """Async generator: tails audit_path, yields SSE-formatted lines."""
    offset = audit_path.stat().st_size if audit_path.exists() else 0
    idle_ticks = 0
    while True:
        await asyncio.sleep(0.5)
        if not audit_path.exists():
            idle_ticks += 1
            if idle_ticks % 30 == 0:
                yield ": keepalive\n\n"
            continue
        size = audit_path.stat().st_size
        if size > offset:
            with open(audit_path, encoding="utf-8") as f:
                f.seek(offset)
                for line in f:
                    line = line.strip()
                    if line:
                        yield f"data: {line}\n\n"
            offset = size
            idle_ticks = 0
        else:
            idle_ticks += 1
            if idle_ticks % 30 == 0:
                yield ": keepalive\n\n"


_DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>safe-mcp-proxy — dashboard</title>
<style>
  *, *::before, *::after { box-sizing: border-box; }
  body   { font-family: monospace; background: #0d0d0d; color: #c8c8c8;
           margin: 0; padding: 16px 20px; font-size: 13px; }
  header { display: flex; align-items: center; gap: 14px;
           margin-bottom: 12px; flex-wrap: wrap; }
  h1     { font-size: 0.85rem; color: #555; margin: 0;
           letter-spacing: 0.08em; flex-shrink: 0; }
  #status      { font-size: 0.75rem; color: #444; }
  #status.ok   { color: #4caf50; }
  #status.err  { color: #bb4444; }
  select { margin-left: auto; background: #161616; color: #777;
           border: 1px solid #2e2e2e; font-family: monospace; font-size: 0.75rem;
           padding: 3px 8px; cursor: pointer; border-radius: 3px; }
  /* ── stats bar ─────────────────────────────────────── */
  #stats-bar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
               padding: 6px 6px 10px; border-bottom: 1px solid #1a1a1a;
               margin-bottom: 10px; }
  .stat-item { display: flex; align-items: center; gap: 5px; font-size: 0.78rem; }
  .stat-dec  { padding: 1px 6px; border-radius: 3px; font-weight: bold;
               font-size: 0.7rem; white-space: nowrap; }
  .stat-cnt  { color: #888; min-width: 18px; }
  .stat-alert { color: #e07050 !important; font-weight: bold; }
  .stat-total { margin-left: auto; font-size: 0.75rem; color: #555; }
  /* ── tool surface ──────────────────────────────────── */
  details#surface { margin-bottom: 10px; }
  details#surface > summary { font-size: 0.78rem; color: #555; cursor: pointer;
    padding: 3px 6px; user-select: none; list-style: none; }
  details#surface > summary::-webkit-details-marker { display: none; }
  details#surface > summary::before { content: '▶  '; }
  details#surface[open] > summary::before { content: '▼  '; }
  #surface-tools { display: flex; flex-wrap: wrap; gap: 6px;
                   padding: 6px 6px 4px; }
  .tool-tag { font-size: 0.75rem; padding: 1px 8px; border: 1px solid #333;
              border-left-width: 3px; border-radius: 3px; color: #888; }
  /* ── feed ──────────────────────────────────────────── */
  #feed { list-style: none; padding: 0; margin: 0; }
  #feed li { display: grid;
             grid-template-columns: 76px 84px minmax(80px,1fr) minmax(120px,2fr) 72px 18px;
             gap: 8px; align-items: center; padding: 3px 6px; margin-bottom: 2px;
             border-left: 3px solid var(--row-accent, #222); }
  #feed li:hover { background: #111; }
  .chip  { display: inline-block; padding: 1px 6px; border-radius: 3px;
           font-size: 0.7rem; font-weight: bold; text-align: center; white-space: nowrap; }
  .ts    { color: #555; font-size: 0.72rem; }
  .tool  { color: #aaa; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .rule  { color: #666; font-size: 0.75rem; overflow: hidden;
           text-overflow: ellipsis; white-space: nowrap; }
  .src   { color: #555; font-size: 0.72rem; }
  .taint { font-size: 0.85rem; text-align: center; }
</style>
</head>
<body>
<header>
  <h1>safe-mcp-proxy / audit dashboard</h1>
  <span id="status">connecting…</span>
  <select id="pal" title="Color palette" aria-label="Color palette">
    <option value="traffic">palette: traffic</option>
    <option value="accessible">palette: accessible</option>
  </select>
</header>
<div id="stats-bar"></div>
<details id="surface">
  <summary id="surface-title">world: — — tools</summary>
  <div id="surface-tools"></div>
</details>
<ul id="feed"></ul>
<script>
const PALETTES = {
  traffic: {
    ALLOW:    { bg: '#388e3c', fg: '#fff' },
    DENY:     { bg: '#c62828', fg: '#fff' },
    ABSENT:   { bg: '#424242', fg: '#aaa' },
    ASK:      { bg: '#e65100', fg: '#fff' },
    SIMULATE: { bg: '#1565c0', fg: '#fff' },
  },
  accessible: {
    ALLOW:    { bg: '#0077bb', fg: '#fff' },
    DENY:     { bg: '#ee7733', fg: '#000' },
    ABSENT:   { bg: '#555555', fg: '#ccc' },
    ASK:      { bg: '#aa3377', fg: '#fff' },
    SIMULATE: { bg: '#009988', fg: '#000' },
  },
};
const DECISIONS = ['ALLOW', 'DENY', 'ABSENT', 'ASK', 'SIMULATE'];
const SE_COLORS = { read: '#1565c0', internal: '#555', external: '#e65100' };
const MAX = 200;
let palette = localStorage.getItem('smp-palette') || 'traffic';

const statusEl = document.getElementById('status');
const feed     = document.getElementById('feed');
const palSel   = document.getElementById('pal');
palSel.value   = palette;

function colors(decision) {
  return (PALETTES[palette] || PALETTES.traffic)[decision] || { bg: '#333', fg: '#aaa' };
}

function applyChip(chip) {
  const c = colors(chip.dataset.decision);
  chip.style.background = c.bg;
  chip.style.color = c.fg;
}

function repaintChips() {
  feed.querySelectorAll('.chip').forEach(applyChip);
  feed.querySelectorAll('li').forEach(li => {
    const c = colors(li.dataset.decision);
    li.style.setProperty('--row-accent', c.bg + '66');
  });
  document.querySelectorAll('.stat-dec').forEach(dec => {
    const item = dec.closest('.stat-item');
    if (!item) return;
    const c = colors(item.dataset.decision);
    dec.style.background = c.bg;
    dec.style.color = c.fg;
  });
}

palSel.addEventListener('change', () => {
  palette = palSel.value;
  localStorage.setItem('smp-palette', palette);
  repaintChips();
});

// ── Stats bar ──────────────────────────────────────────────────────────
function buildStatsBar() {
  const bar = document.getElementById('stats-bar');
  bar.innerHTML = '';
  DECISIONS.forEach(d => {
    const item = document.createElement('span');
    item.className = 'stat-item';
    item.dataset.decision = d;
    const c = colors(d);
    const dec = document.createElement('span');
    dec.className = 'stat-dec';
    dec.dataset.decision = d;
    dec.style.background = c.bg;
    dec.style.color = c.fg;
    dec.textContent = d;
    const cnt = document.createElement('span');
    cnt.className = 'stat-cnt';
    cnt.id = 'cnt-' + d;
    cnt.textContent = '—';
    item.append(dec, cnt);
    bar.appendChild(item);
  });
  const tot = document.createElement('span');
  tot.className = 'stat-total';
  tot.innerHTML = 'total <b id="cnt-total">—</b>';
  bar.appendChild(tot);
}

async function refreshStats() {
  const data = await fetch('/stats').then(r => r.json()).catch(() => null);
  if (!data) return;
  DECISIONS.forEach(d => {
    const el = document.getElementById('cnt-' + d);
    if (!el) return;
    el.textContent = data.counts[d] ?? 0;
    el.className = (d === 'DENY' && (data.counts[d] ?? 0) > 0)
      ? 'stat-cnt stat-alert' : 'stat-cnt';
  });
  const tot = document.getElementById('cnt-total');
  if (tot) tot.textContent = data.total;
}

// ── Tool surface ───────────────────────────────────────────────────────
async function loadSurface() {
  const data = await fetch('/worlds/current').then(r => r.json()).catch(() => null);
  if (!data) return;
  document.getElementById('surface-title').textContent =
    'world: ' + (data.world_id || '?') + ' — ' + data.tools.length + ' tools';
  const toolsDiv = document.getElementById('surface-tools');
  toolsDiv.innerHTML = '';
  data.tools.forEach(t => {
    const span = document.createElement('span');
    span.className = 'tool-tag';
    span.title = 'side_effect: ' + t.side_effect_type;
    span.style.borderLeftColor = SE_COLORS[t.side_effect_type] || '#444';
    span.textContent = t.name;
    toolsDiv.appendChild(span);
  });
}

// ── Feed rows ──────────────────────────────────────────────────────────
function fmtTs(iso) {
  try { return new Date(iso).toLocaleTimeString(); } catch { return iso || ''; }
}

function addRow(e) {
  const dec = e.decision || 'UNKNOWN';
  const c   = colors(dec);
  const li  = document.createElement('li');
  li.dataset.decision = dec;
  li.style.setProperty('--row-accent', c.bg + '66');

  const ts   = Object.assign(document.createElement('span'), { className: 'ts',   textContent: fmtTs(e.timestamp) });
  const chip = Object.assign(document.createElement('span'), { className: 'chip', textContent: dec });
  chip.dataset.decision = dec;
  chip.style.background = c.bg;
  chip.style.color      = c.fg;
  const tool  = Object.assign(document.createElement('span'), { className: 'tool',  textContent: e.tool  || '—', title: e.tool  || '' });
  const rule  = Object.assign(document.createElement('span'), { className: 'rule',  textContent: e.rule  || '',       title: e.rule  || '' });
  const src   = Object.assign(document.createElement('span'), { className: 'src',   textContent: e.source_channel || '' });
  const taint = Object.assign(document.createElement('span'), { className: 'taint', textContent: e.taint ? '⚠' : '' });
  if (e.taint) taint.style.color = c.bg;

  li.append(ts, chip, tool, rule, src, taint);
  feed.prepend(li);
  if (feed.children.length > MAX) feed.lastElementChild.remove();
}

// ── Init ───────────────────────────────────────────────────────────────
buildStatsBar();
refreshStats();
setInterval(refreshStats, 5000);
loadSurface();

const es = new EventSource('/events');
es.onopen    = () => { statusEl.textContent = 'live'; statusEl.className = 'ok'; };
es.onerror   = () => { statusEl.textContent = 'disconnected'; statusEl.className = 'err'; };
es.onmessage = (ev) => {
  try { addRow(JSON.parse(ev.data)); }
  catch { console.warn('bad SSE payload:', ev.data); }
};
</script>
</body>
</html>
"""


def create_app(base_dir: Optional[Path] = None, executor: Optional[Executor] = None) -> FastAPI:
    resolved_base_dir = base_dir or _default_base_dir()
    _seed_if_empty(resolved_base_dir)
    app = FastAPI(title="safe-mcp-proxy API")
    app.state.trace_store = _build_trace_store(resolved_base_dir)
    app.state.executor = executor or build_executor(resolved_base_dir)
    # Expose the WorldController directly on app.state so switch endpoints can use it.
    app.state.world_controller = getattr(app.state.executor, "world_controller", None)
    app.state.gemini_proxy = GeminiProxy(app.state.executor)

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

    # ------------------------------------------------------------------
    # Dashboard (EPIC 14)
    # ------------------------------------------------------------------

    @app.get("/events")
    async def sse_events():
        """Server-Sent Events stream: tails audit.jsonl, emits each new entry."""
        audit_path = resolved_base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"

        return StreamingResponse(
            _sse_stream(audit_path),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard():
        """Minimal audit dashboard — live decision feed via SSE."""
        return HTMLResponse(content=_DASHBOARD_HTML)

    @app.get("/worlds/current")
    async def worlds_current() -> dict:
        """Return active world_id and its exposed tool surface."""
        wc: Optional[WorldController] = app.state.world_controller
        if wc is not None:
            tool_list = wc.list_tools()
            wid = wc.current_id()
        else:
            tool_list = [
                {"name": t.name, "capability": t.capability, "side_effect_type": t.side_effect_type}
                for t in app.state.executor.registry.list_exposed()
            ]
            wid = app.state.executor.world_id
        return {"world_id": wid, "tools": tool_list}

    # ------------------------------------------------------------------
    # Dynamic world switching (EPIC dynamic-world-switching)
    # ------------------------------------------------------------------

    def _write_world_switch_event(diff: dict) -> None:
        """Append a WORLD_SWITCH event to audit.jsonl."""
        import json as _json
        from datetime import datetime, timezone
        audit_path = resolved_base_dir / "safe_mcp_proxy" / "logs" / "audit.jsonl"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "event": "WORLD_SWITCH",
            "diff": diff,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with audit_path.open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(event, sort_keys=True) + "\n")

    @app.post("/world/switch")
    async def world_switch(world_id: str = Query(...), reason: str = Query(default="")) -> dict:
        """Switch the active world and return a diff of appeared/vanished tools."""
        wc: Optional[WorldController] = app.state.world_controller
        if wc is None:
            raise HTTPException(status_code=501, detail="WorldController not available")
        try:
            diff = wc.switch(world_id, reason=reason)
        except WorldNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        _write_world_switch_event(diff)
        return diff

    @app.get("/world/current")
    async def world_current() -> dict:
        """Return the active world_id and the full switch history."""
        wc: Optional[WorldController] = app.state.world_controller
        if wc is None:
            return {"world_id": app.state.executor.world_id, "history": []}
        return {"world_id": wc.current_id(), "history": wc.history}

    # ------------------------------------------------------------------
    # Approval endpoints (DS7.1)
    # ------------------------------------------------------------------

    @app.get("/approvals/{token}")
    async def get_approval_status(token: str) -> dict:
        entry = app.state.executor.approval_store.get(token)
        if entry is None:
            raise HTTPException(status_code=404, detail="Approval token not found")
        return {
            "token": entry.token,
            "tool_name": entry.tool_name,
            "status": entry.status,
            "created_at": entry.created_at,
        }

    @app.post("/approvals/{token}/approve")
    async def approve_tool(token: str) -> dict:
        entry = app.state.executor.approval_store.get(token)
        if entry is None:
            raise HTTPException(status_code=404, detail="Approval token not found")
        if entry.status != "pending":
            raise HTTPException(status_code=409, detail=f"Token is already {entry.status}")
        app.state.executor.approval_store.approve(token)
        return app.state.executor.execute_approved(token)

    @app.post("/approvals/{token}/reject")
    async def reject_tool(token: str) -> dict:
        entry = app.state.executor.approval_store.get(token)
        if entry is None:
            raise HTTPException(status_code=404, detail="Approval token not found")
        if entry.status != "pending":
            raise HTTPException(status_code=409, detail=f"Token is already {entry.status}")
        return app.state.executor.reject_approval(token)

    # ------------------------------------------------------------------
    # Atlassian MCP passthrough (EPIC 9 / M1)
    # ------------------------------------------------------------------

    from safe_mcp_proxy.atlassian.config import AtlassianProxyConfig
    from safe_mcp_proxy.atlassian.passthrough import MCPPassthrough
    from safe_mcp_proxy.atlassian.policy import ManifestPolicyEngine

    _atlassian_log = resolved_base_dir / "safe_mcp_proxy" / "logs" / "atlassian_requests.jsonl"

    @app.post("/atlassian/mcp")
    async def atlassian_mcp(request: Any = Body(...)) -> dict:
        """MCP JSON-RPC passthrough to Atlassian MCP (list_tools / call_tool)."""
        config = AtlassianProxyConfig.from_env()
        policy = ManifestPolicyEngine.from_yaml(config.manifest_path) if config.manifest_path else None
        return MCPPassthrough(config, _atlassian_log, policy).forward(request)

    @app.get("/atlassian/config")
    async def atlassian_config() -> dict:
        """Show active Atlassian proxy config (no secrets)."""
        cfg = AtlassianProxyConfig.from_env()
        return {
            "mode": cfg.mode,
            "upstream_configured": bool(cfg.upstream_url),
            "timeout": cfg.timeout,
            "manifest_configured": cfg.manifest_path is not None,
            "source_channel": cfg.source_channel,
        }

    # ------------------------------------------------------------------
    # Gemini integration (EPIC 8 / Phase 1 passthrough)
    # ------------------------------------------------------------------

    @app.get("/integrations/gemini/tools/list")
    async def gemini_list_tools() -> dict:
        """Return the manifest-filtered tool surface in Gemini function-declaration format."""
        return app.state.gemini_proxy.list_tools()

    @app.post("/integrations/gemini/tools/execute")
    async def gemini_execute(request: Any = Body(...)) -> dict:
        """Accept a Gemini functionCall request and route it through the proxy."""
        try:
            return app.state.gemini_proxy.execute(request)
        except GeminiAdapterError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    return app


app = create_app()
