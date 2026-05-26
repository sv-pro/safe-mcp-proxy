/** Core decision outcomes — mirrors Python Decision enum */
export type Decision = "ALLOW" | "DENY" | "ABSENT" | "ASK" | "SIMULATE";

/** Execution context — mirrors Python ExecutionMode */
export type ExecutionMode = "INTERACTIVE" | "BACKGROUND";

/** Source channel taint classification */
export type SourceChannel = "cli" | "email" | "web" | "tool_output";

/** Provenance attached to every tool invocation */
export interface Provenance {
  sourceChannel: SourceChannel;
  tainted: boolean;
  executionMode: ExecutionMode;
  parentSources: SourceChannel[];
}

/** A single tool invocation request */
export interface ToolCall {
  toolName: string;
  payload: Record<string, unknown>;
  provenance: Provenance;
}

/** Policy evaluation result */
export interface PolicyResult {
  decision: Decision;
  rule: string;
}

/** Attack scenario definition */
export interface AttackScenario {
  id: string;
  type: "email_injection" | "tool_chain" | "mcp_poison";
  description: string;
  steps: ToolCall[];
}

/** Verdict for a single scenario run */
export interface Verdict {
  scenarioId: string;
  attackSucceeded: boolean;
  demoPass: boolean;
  baselineDecisions: PolicyResult[];
  protectedDecisions: PolicyResult[];
  summary: string;
}

/** Trace entry appended to the audit log */
export interface TraceEntry {
  timestamp: string;
  toolName: string;
  decision: Decision;
  rule: string;
  sourceChannel: SourceChannel;
  tainted: boolean;
}
