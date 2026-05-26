import type { ToolCall, PolicyResult, TraceEntry } from "./types.js";

/** Collects execution traces during a scenario run */
export class ExecutionObserver {
  private entries: TraceEntry[] = [];

  record(call: ToolCall, result: PolicyResult): void {
    this.entries.push({
      timestamp: new Date().toISOString(),
      toolName: call.toolName,
      decision: result.decision,
      rule: result.rule,
      sourceChannel: call.provenance.sourceChannel,
      tainted: call.provenance.tainted,
    });
  }

  getEntries(): readonly TraceEntry[] {
    return this.entries;
  }

  clear(): void {
    this.entries = [];
  }
}
