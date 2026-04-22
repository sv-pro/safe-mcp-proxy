#!/usr/bin/env bash
# create_demo_surface_issues.sh
# Creates milestones, labels, and 20 GitHub issues for the Demo Surface Layer roadmap.
# Usage: bash scripts/create_demo_surface_issues.sh
# Requires: gh CLI authenticated with write access to sv-pro/safe-mcp-proxy
set -euo pipefail
REPO="sv-pro/safe-mcp-proxy"

echo "=== Creating Milestones ==="
for title in \
  "DS0 — Data Plumbing" \
  "DS1 — Trace Viewer" \
  "DS2 — Scenario Switcher" \
  "DS3 — World Diff Mode" \
  "DS4 — Visual Pipeline Explanation" \
  "DS5 — Export & Sharing" \
  "DS6 — Demo Polish"
do
  gh api repos/$REPO/milestones \
    --method POST \
    -f title="$title" \
    -f state="open" \
    --silent && echo "  ✓ $title" || echo "  ~ already exists: $title"
done

echo ""
echo "=== Creating Labels ==="

# Epic labels
declare -A EPIC_COLORS=(
  ["epic/ds0-data-plumbing"]="0075ca"
  ["epic/ds1-trace-viewer"]="e4e669"
  ["epic/ds2-scenario-switcher"]="d93f0b"
  ["epic/ds3-world-diff"]="0052cc"
  ["epic/ds4-visual-pipeline"]="5319e7"
  ["epic/ds5-export-sharing"]="006b75"
  ["epic/ds6-demo-polish"]="1d76db"
)
for label in "${!EPIC_COLORS[@]}"; do
  gh label create "$label" --color "${EPIC_COLORS[$label]}" --repo "$REPO" --force
  echo "  ✓ $label"
done

# Type labels
declare -A TYPE_COLORS=(
  ["type/feature"]="a2eeef"
  ["type/chore"]="e4e669"
  ["type/content"]="c5def5"
)
for label in "${!TYPE_COLORS[@]}"; do
  gh label create "$label" --color "${TYPE_COLORS[$label]}" --repo "$REPO" --force
  echo "  ✓ $label"
done

# Priority labels
declare -A PRI_COLORS=(
  ["priority/high"]="b60205"
  ["priority/medium"]="e99695"
  ["priority/low"]="f9d0c4"
)
for label in "${!PRI_COLORS[@]}"; do
  gh label create "$label" --color "${PRI_COLORS[$label]}" --repo "$REPO" --force
  echo "  ✓ $label"
done

echo ""
echo "=== Fetching milestone IDs ==="
MS_JSON=$(gh api repos/$REPO/milestones --paginate)
get_ms_id() {
  local target="$1"
  echo "$MS_JSON" | python3 -c "
import json, sys
ms = json.load(sys.stdin)
for m in ms:
    if m['title'] == '$target':
        print(m['number'])
        break
"
}

DS0=$(get_ms_id "DS0 — Data Plumbing")
DS1=$(get_ms_id "DS1 — Trace Viewer")
DS2=$(get_ms_id "DS2 — Scenario Switcher")
DS3=$(get_ms_id "DS3 — World Diff Mode")
DS4=$(get_ms_id "DS4 — Visual Pipeline Explanation")
DS5=$(get_ms_id "DS5 — Export & Sharing")
DS6=$(get_ms_id "DS6 — Demo Polish")

echo "  DS0=$DS0 DS1=$DS1 DS2=$DS2 DS3=$DS3 DS4=$DS4 DS5=$DS5 DS6=$DS6"

echo ""
echo "=== Creating Issues ==="

create_issue() {
  local title="$1"; local body="$2"; local labels="$3"; local ms="$4"
  gh issue create --repo "$REPO" \
    --title "$title" \
    --body "$body" \
    --label "$labels" \
    --milestone "$ms"
  echo "  ✓ $title"
}

# ── DS0 — Data Plumbing ───────────────────────────────────────────────────────

create_issue \
  "DS0.1 — Implement TraceStore (read-only over JSONL)" \
  "## Goal
Make audit log queryable and reproducible.

## Tasks
- [ ] Create \`trace_store.py\`
- [ ] Read \`logs/audit.jsonl\` line by line
- [ ] Normalize records into a stable format:
  - \`id\`, \`timestamp\`, \`input\` (optional), \`source_channel\`, \`taint\`
  - \`tool_requested\`, \`decision\` (ALLOW|DENY|ABSENT|SIMULATE), \`rule_hit\`, \`descriptor_hash\`
- [ ] Add filters: by decision, by tool, by time range

## Acceptance criteria
- Can retrieve last N records
- Format is stable and versioned" \
  "epic/ds0-data-plumbing,type/feature,priority/high" \
  "$DS0"

create_issue \
  "DS0.2 — Expose HTTP API (FastAPI)" \
  "## Goal
Serve audit traces over HTTP.

## Endpoints
- \`GET /traces?limit=N\`
- \`GET /traces/{id}\`
- \`GET /stats\` (counts by decision)

## Tasks
- [ ] Spin up FastAPI app in \`api/main.py\`
- [ ] Wire TraceStore (DS0.1)
- [ ] Add CORS for local dev

## Acceptance criteria
- curl/browser returns JSON
- Latency < 100 ms for last 100 records" \
  "epic/ds0-data-plumbing,type/feature,priority/high" \
  "$DS0"

create_issue \
  "DS0.3 — Deterministic Replay Endpoint" \
  "## Goal
Prove decisions are deterministic.

## Endpoint
\`POST /replay/{id}\`

## Tasks
- [ ] Fetch record from audit by id
- [ ] Re-run decision through current policy_engine
- [ ] Compare result with stored outcome

## Acceptance criteria
- Same input → same decision
- Mismatch → separate flag in response (\`diverged: true\`)" \
  "epic/ds0-data-plumbing,type/feature,priority/medium" \
  "$DS0"

# ── DS1 — Trace Viewer ────────────────────────────────────────────────────────

create_issue \
  "DS1.1 — Minimal UI scaffold" \
  "## Goal
Single-page observable trace viewer.

## Tasks
- [ ] One HTML page (\`ui/index.html\`)
- [ ] No heavy frameworks — HTMX / Vanilla / Alpine
- [ ] Layout: left = trace list, right = trace detail

## Acceptance criteria
- Page opens locally
- Data loaded from \`/traces\`" \
  "epic/ds1-trace-viewer,type/feature,priority/high" \
  "$DS1"

create_issue \
  "DS1.2 — Trace List Panel" \
  "## Goal
Show recent traces at a glance.

## Tasks
- [ ] Display last N traces
- [ ] Columns: time, tool, decision, source_channel
- [ ] Neutral color badges (not red/green)

## Acceptance criteria
- Click on row opens detail panel" \
  "epic/ds1-trace-viewer,type/feature,priority/high" \
  "$DS1"

create_issue \
  "DS1.3 — Trace Detail Panel" \
  "## Goal
Show full context of a single trace.

## Tasks
- [ ] Display: input (if any), source_channel, taint, tool_requested, descriptor_hash, decision, rule_hit
- [ ] Pipeline section: Provenance → Registry → Policy → Execution

## Acceptance criteria
- User can see exactly where the decision was made" \
  "epic/ds1-trace-viewer,type/feature,priority/high" \
  "$DS1"

create_issue \
  "DS1.4 — Decision Semantics Highlight" \
  "## Goal
Make ABSENT vs DENY immediately readable.

## Tasks
- [ ] ABSENT → \"Action does not exist in this world\"
- [ ] DENY → \"Action exists but blocked by policy\"
- [ ] ALLOW → \"Action executed\"
- [ ] SIMULATE → \"Action simulated (no side effects)\"

## Acceptance criteria
- Distinction legible without explanation" \
  "epic/ds1-trace-viewer,type/feature,priority/high" \
  "$DS1"

# ── DS2 — Scenario Switcher ───────────────────────────────────────────────────

create_issue \
  "DS2.1 — Scenario registry" \
  "## Goal
Turn examples into managed, replayable cases.

## Tasks
- [ ] Create \`scenarios/\` package with:
  - \`benign_flow\`, \`prompt_injection\`, \`poisoned_descriptor\`, \`absent_tool\`
- [ ] Each scenario: input, source_channel, expected outcome
- [ ] Scenarios callable programmatically

## Acceptance criteria
- Scenarios invokable via Python API" \
  "epic/ds2-scenario-switcher,type/feature,priority/high" \
  "$DS2"

create_issue \
  "DS2.2 — API to run scenario" \
  "## Goal
Trigger scenarios over HTTP.

## Endpoint
\`POST /scenarios/{name}/run\`

## Tasks
- [ ] Execute scenario
- [ ] Record trace
- [ ] Return trace id

## Acceptance criteria
- Scenario runnable from UI and API" \
  "epic/ds2-scenario-switcher,type/feature,priority/high" \
  "$DS2"

create_issue \
  "DS2.3 — UI Scenario Switcher" \
  "## Goal
One-click scenario execution in UI.

## Tasks
- [ ] Dropdown or buttons: Benign, Injection, Poisoned, Absent
- [ ] On click: run scenario, open resulting trace

## Acceptance criteria
- One click → full case display" \
  "epic/ds2-scenario-switcher,type/feature,priority/high" \
  "$DS2"

# ── DS3 — World Diff Mode ─────────────────────────────────────────────────────

create_issue \
  "DS3.1 — Support multiple world manifests" \
  "## Goal
Same agent, different world → different decisions.

## Tasks
- [ ] Add \`config/worlds/\`: world_a.yaml, world_b.yaml, world_c.yaml
- [ ] Support \`world_id\` switching at runtime

## Acceptance criteria
- Different worlds produce different decisions for same input" \
  "epic/ds3-world-diff,type/feature,priority/medium" \
  "$DS3"

create_issue \
  "DS3.2 — World comparison API" \
  "## Goal
Compare outcomes across worlds in one call.

## Endpoint
\`POST /compare\`

## Input
\`{ \"scenario\": \"...\", \"worlds\": [\"world_a\", \"world_b\"] }\`

## Output
Decisions per world

## Acceptance criteria
- One input → different outcomes visible side by side" \
  "epic/ds3-world-diff,type/feature,priority/medium" \
  "$DS3"

create_issue \
  "DS3.3 — UI World Diff Panel" \
  "## Goal
Visualize policy variance across worlds.

## Tasks
- [ ] Table: world A → decision, world B → decision, world C → decision
- [ ] Highlight differences

## Acceptance criteria
- ABSENT vs DENY vs ALLOW visible at a glance" \
  "epic/ds3-world-diff,type/feature,priority/medium" \
  "$DS3"

# ── DS4 — Visual Pipeline Explanation ────────────────────────────────────────

create_issue \
  "DS4.1 — Pipeline visualization" \
  "## Goal
Make the execution flow understandable without words.

## Tasks
- [ ] Steps: Input → Provenance (taint) → Registry (visible tools) → Policy → Decision
- [ ] Show which step produced the outcome

## Acceptance criteria
- User sees execution flow for each trace" \
  "epic/ds4-visual-pipeline,type/feature,priority/medium" \
  "$DS4"

create_issue \
  "DS4.2 — Rule explanation layer" \
  "## Goal
Explain why a rule fired.

## Tasks
- [ ] For each rule_hit: short human-readable explanation
- [ ] Link to rule definition

## Acceptance criteria
- Clear why DENY/ABSENT, not just the label" \
  "epic/ds4-visual-pipeline,type/feature,priority/medium" \
  "$DS4"

# ── DS5 — Export & Sharing ────────────────────────────────────────────────────

create_issue \
  "DS5.1 — Export trace as JSON" \
  "## Goal
Make traces portable.

## Tasks
- [ ] Export button in UI
- [ ] Download trace as \`.json\`

## Acceptance criteria
- Single trace exportable from UI" \
  "epic/ds5-export-sharing,type/feature,priority/medium" \
  "$DS5"

create_issue \
  "DS5.2 — Generate shareable demo bundle" \
  "## Goal
Full reproducible demo as a single artifact.

## Tasks
- [ ] Bundle: scenario + manifest + trace
- [ ] Playback possible from bundle alone

## Acceptance criteria
- Bundle can be shared and replayed offline" \
  "epic/ds5-export-sharing,type/feature,priority/low" \
  "$DS5"

# ── DS6 — Demo Polish ─────────────────────────────────────────────────────────

create_issue \
  "DS6.1 — Seed demo data" \
  "## Goal
UI is never empty on first launch.

## Tasks
- [ ] Pre-generate traces covering all 4 decision types (ALLOW, DENY, ABSENT, SIMULATE)
- [ ] Include in repo under \`seeds/\` or auto-load on startup

## Acceptance criteria
- UI shows meaningful data without running any scenario first" \
  "epic/ds6-demo-polish,type/chore,priority/high" \
  "$DS6"

create_issue \
  "DS6.2 — One-click demo script" \
  "## Goal
Zero-friction demo startup.

## Tasks
- [ ] \`python run_demo.py\` starts API + UI
- [ ] Opens browser automatically

## Acceptance criteria
- New user can see working demo in < 30 seconds" \
  "epic/ds6-demo-polish,type/feature,priority/high" \
  "$DS6"

create_issue \
  "DS6.3 — GIF / screen recording" \
  "## Goal
Visual proof for README and sales deck.

## Tasks
- [ ] Record: injection → DENY
- [ ] Record: absent tool → \"does not exist\"
- [ ] Record: world diff comparison

## Acceptance criteria
- GIF embeddable in README, < 5 MB" \
  "epic/ds6-demo-polish,type/content,priority/high" \
  "$DS6"

echo ""
echo "=== Done! 20 issues created across 7 milestones ==="
