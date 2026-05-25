import type { AttackScenario, ToolCall, PolicyResult, Verdict } from "./types.js";
import { ExecutionObserver } from "./observer.js";
import { VerdictEngine } from "./verdict.js";

/** Minimal policy gate interface — implement for baseline or protected runs */
export interface PolicyGate {
  evaluate(call: ToolCall): PolicyResult;
}

/** Baseline gate — allows everything (simulates an unprotected agent) */
export class BaselinePolicyGate implements PolicyGate {
  evaluate(_call: ToolCall): PolicyResult {
    return { decision: "ALLOW", rule: "baseline_allow_all" };
  }
}

/** Orchestrates a single scenario run against a given policy gate */
export class ScenarioRunner {
  private observer = new ExecutionObserver();
  private verdictEngine = new VerdictEngine();

  constructor(private readonly gate: PolicyGate) {}

  run(scenario: AttackScenario): PolicyResult[] {
    this.observer.clear();
    return scenario.steps.map((step) => {
      const result = this.gate.evaluate(step);
      this.observer.record(step, result);
      return result;
    });
  }

  compare(scenario: AttackScenario, protectedGate: PolicyGate): Verdict {
    const baselineRunner = new ScenarioRunner(new BaselinePolicyGate());
    const baselineResults = baselineRunner.run(scenario);
    const protectedResults = this.run(scenario);
    return this.verdictEngine.evaluate(
      scenario.id,
      baselineResults,
      protectedResults
    );
  }

  getObserver(): ExecutionObserver {
    return this.observer;
  }
}
