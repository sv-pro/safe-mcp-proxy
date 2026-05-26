import type { PolicyResult, Verdict } from "./types.js";

/**
 * Computes a Verdict by comparing baseline (unprotected) and protected
 * policy outcomes for the same scenario.
 */
export class VerdictEngine {
  evaluate(
    scenarioId: string,
    baselineDecisions: PolicyResult[],
    protectedDecisions: PolicyResult[]
  ): Verdict {
    const attackSucceeded = baselineDecisions.some(
      (d) => d.decision === "ALLOW"
    );
    const demoPass = protectedDecisions.every(
      (d) => d.decision === "DENY" || d.decision === "ABSENT"
    );

    const summary = demoPass
      ? `[PASS] Proxy blocked the attack (${scenarioId})`
      : `[FAIL] Attack succeeded through the proxy (${scenarioId})`;

    return {
      scenarioId,
      attackSucceeded,
      demoPass,
      baselineDecisions,
      protectedDecisions,
      summary,
    };
  }
}
