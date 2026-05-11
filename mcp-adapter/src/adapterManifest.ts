// Types

export type ToolDecision = "allow" | "ask" | "deny" | "simulate" | "absent";

export type AdapterArgExpression =
  | { from: string }
  | { const: unknown }
  | { template: string }
  | { object: Record<string, AdapterArgExpression> }
  | { array: AdapterArgExpression[] };

export type AdapterConstraint = {
  kind: "path_within";
  arg: string;
  base: string;
};

export type AdapterManifestToolRow = {
  upstream_routing_key: string;
  upstream_tool: string;
  exposed_as: string;
  decision: ToolDecision;
  expose?: {
    description?: string;
    inputSchema?: Record<string, unknown>;
    annotations?: Record<string, unknown>;
    title?: string;
  };
  call?: { args?: Record<string, AdapterArgExpression> };
  constraints?: AdapterConstraint[];
};

export type AdapterManifest = {
  version: 1;
  default_decision: ToolDecision;
  tools: AdapterManifestToolRow[];
};

export type UpstreamConfig = {
  command: string;
  args?: string[];
  env?: Record<string, string>;
};

export type UpstreamTool = {
  name: string;
  description?: string;
  inputSchema: Record<string, unknown>;
  annotations?: Record<string, unknown>;
};

export type ExposedTool = {
  name: string;
  description?: string;
  inputSchema: Record<string, unknown>;
  annotations?: Record<string, unknown>;
};

export type ToolCallPlan = {
  decision: ToolDecision;
  upstreamToolName: string;
  translatedArgs: Record<string, unknown>;
  constraints: AdapterConstraint[];
};

// Validation

const VALID_DECISIONS = new Set<string>(["allow", "ask", "deny", "simulate", "absent"]);

function isValidDecision(v: unknown): v is ToolDecision {
  return typeof v === "string" && VALID_DECISIONS.has(v);
}

export function validateManifest(data: unknown): AdapterManifest {
  if (typeof data !== "object" || data === null) throw new Error("manifest must be an object");
  const d = data as Record<string, unknown>;
  if (d["version"] !== 1) throw new Error("manifest.version must be 1");
  if (!isValidDecision(d["default_decision"]))
    throw new Error(`manifest.default_decision must be one of: ${[...VALID_DECISIONS].join(", ")}`);
  if (!Array.isArray(d["tools"])) throw new Error("manifest.tools must be an array");

  const tools: AdapterManifestToolRow[] = (d["tools"] as unknown[]).map((row, i) => {
    if (typeof row !== "object" || row === null)
      throw new Error(`manifest.tools[${i}] must be an object`);
    const r = row as Record<string, unknown>;
    if (typeof r["upstream_tool"] !== "string" || !r["upstream_tool"])
      throw new Error(`manifest.tools[${i}].upstream_tool must be a non-empty string`);
    if (typeof r["exposed_as"] !== "string" || !r["exposed_as"])
      throw new Error(`manifest.tools[${i}].exposed_as must be a non-empty string`);
    if (!isValidDecision(r["decision"]))
      throw new Error(`manifest.tools[${i}].decision must be one of: ${[...VALID_DECISIONS].join(", ")}`);
    return {
      upstream_routing_key:
        typeof r["upstream_routing_key"] === "string" && r["upstream_routing_key"]
          ? r["upstream_routing_key"]
          : "default",
      upstream_tool: r["upstream_tool"] as string,
      exposed_as: r["exposed_as"] as string,
      decision: r["decision"] as ToolDecision,
      expose: r["expose"] as AdapterManifestToolRow["expose"],
      call: r["call"] as AdapterManifestToolRow["call"],
      constraints: Array.isArray(r["constraints"])
        ? (r["constraints"] as AdapterConstraint[])
        : undefined,
    };
  });

  return {
    version: 1,
    default_decision: d["default_decision"] as ToolDecision,
    tools,
  };
}

export function validateUpstreamConfig(data: unknown): UpstreamConfig {
  if (typeof data !== "object" || data === null)
    throw new Error("upstream config must be an object");
  const d = data as Record<string, unknown>;
  if (typeof d["command"] !== "string" || !d["command"])
    throw new Error("upstream.command must be a non-empty string");
  if (d["args"] !== undefined && !Array.isArray(d["args"]))
    throw new Error("upstream.args must be an array if provided");
  if (d["args"] !== undefined) {
    for (const a of d["args"] as unknown[]) {
      if (typeof a !== "string") throw new Error("upstream.args entries must be strings");
    }
  }
  if (d["env"] !== undefined) {
    if (typeof d["env"] !== "object" || d["env"] === null)
      throw new Error("upstream.env must be an object if provided");
    for (const v of Object.values(d["env"] as Record<string, unknown>)) {
      if (typeof v !== "string") throw new Error("upstream.env values must be strings");
    }
  }
  // Filter empty-string env values
  const env: Record<string, string> = {};
  if (d["env"]) {
    for (const [k, v] of Object.entries(d["env"] as Record<string, string>)) {
      if (v !== "") env[k] = v;
    }
  }
  return {
    command: d["command"] as string,
    args: d["args"] as string[] | undefined,
    env: Object.keys(env).length > 0 ? env : undefined,
  };
}

// Projection

export function projectUpstreamToolsWithManifest(
  upstreamTools: UpstreamTool[],
  manifest: AdapterManifest,
  routingKey: string
): ExposedTool[] {
  const result: ExposedTool[] = [];
  for (const tool of upstreamTools) {
    const rows = manifest.tools.filter(
      (r) => r.upstream_routing_key === routingKey && r.upstream_tool === tool.name
    );
    if (rows.length === 0) {
      if (manifest.default_decision !== "absent") {
        result.push({
          name: tool.name,
          description: tool.description,
          inputSchema: tool.inputSchema,
          annotations: tool.annotations,
        });
      }
    } else {
      for (const row of rows) {
        if (row.decision !== "absent") {
          result.push({
            name: row.exposed_as,
            description: row.expose?.description ?? tool.description,
            inputSchema:
              (row.expose?.inputSchema as Record<string, unknown>) ?? tool.inputSchema,
            annotations:
              (row.expose?.annotations as Record<string, unknown>) ?? tool.annotations,
          });
        }
      }
    }
  }
  return result;
}

// Call planning

function getByPath(obj: unknown, dotPath: string): unknown {
  return dotPath.split(".").reduce((cur: unknown, key: string) => {
    if (cur === null || cur === undefined || typeof cur !== "object") return undefined;
    return (cur as Record<string, unknown>)[key];
  }, obj);
}

function resolveExpression(
  expr: AdapterArgExpression,
  hostArgs: Record<string, unknown>
): unknown {
  if ("from" in expr) {
    return getByPath(hostArgs, expr.from);
  }
  if ("const" in expr) {
    return expr.const;
  }
  if ("template" in expr) {
    return expr.template.replace(
      /\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}/g,
      (_: string, key: string) => {
        const val = getByPath(hostArgs, key);
        if (typeof val !== "string" && typeof val !== "number" && typeof val !== "boolean") {
          throw new Error(
            `Template variable '${key}' is not a string, number, or boolean (got ${typeof val})`
          );
        }
        return String(val);
      }
    );
  }
  if ("object" in expr) {
    return Object.fromEntries(
      Object.entries(expr.object).map(([k, v]) => [k, resolveExpression(v, hostArgs)])
    );
  }
  if ("array" in expr) {
    return expr.array.map((item) => resolveExpression(item, hostArgs));
  }
  throw new Error("Unknown AdapterArgExpression shape");
}

function translateArgs(
  hostArgs: Record<string, unknown>,
  callConfig: AdapterManifestToolRow["call"] | undefined
): Record<string, unknown> {
  if (!callConfig?.args) return hostArgs;
  return Object.fromEntries(
    Object.entries(callConfig.args).map(([key, expr]) => [
      key,
      resolveExpression(expr, hostArgs),
    ])
  );
}

export function planToolCallWithManifest(
  exposedName: string,
  hostArgs: Record<string, unknown>,
  manifest: AdapterManifest,
  upstreamTools: UpstreamTool[],
  routingKey: string
): ToolCallPlan {
  // Step 1: find manifest row by exposed_as + routing key
  const row = manifest.tools.find(
    (r) => r.exposed_as === exposedName && r.upstream_routing_key === routingKey
  );

  if (row) {
    const translatedArgs = translateArgs(hostArgs, row.call);
    return {
      decision: row.decision,
      upstreamToolName: row.upstream_tool,
      translatedArgs,
      constraints: row.constraints ?? [],
    };
  }

  // Step 2: no row — does upstream even know this tool?
  const upstreamTool = upstreamTools.find((t) => t.name === exposedName);
  if (!upstreamTool) {
    return { decision: "absent", upstreamToolName: exposedName, translatedArgs: hostArgs, constraints: [] };
  }

  // Step 3: upstream knows it — is it hidden from tools/list?
  const upstreamRows = manifest.tools.filter(
    (r) => r.upstream_tool === exposedName && r.upstream_routing_key === routingKey
  );
  const isHidden =
    (upstreamRows.length === 0 && manifest.default_decision === "absent") ||
    (upstreamRows.length > 0 && upstreamRows.every((r) => r.decision === "absent"));

  if (isHidden) {
    return { decision: "absent", upstreamToolName: exposedName, translatedArgs: hostArgs, constraints: [] };
  }

  // Step 4: visible as itself, apply default_decision, no translation
  return {
    decision: manifest.default_decision,
    upstreamToolName: exposedName,
    translatedArgs: hostArgs,
    constraints: [],
  };
}
