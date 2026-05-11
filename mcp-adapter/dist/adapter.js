import * as fs from "node:fs";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema, } from "@modelcontextprotocol/sdk/types.js";
import { validateManifest, validateUpstreamConfig, projectUpstreamToolsWithManifest, planToolCallWithManifest, } from "./adapterManifest.js";
import { evaluateAdapterConstraints, ConstraintViolationError, } from "./adapterConstraints.js";
function errorResponse(message) {
    return {
        content: [{ type: "text", text: message }],
        isError: true,
    };
}
export async function runAdapterStdio(config) {
    // Load and validate configs
    let manifestRaw;
    let upstreamRaw;
    try {
        manifestRaw = JSON.parse(fs.readFileSync(config.manifestPath, "utf-8"));
    }
    catch (e) {
        throw new Error(`Failed to load manifest from '${config.manifestPath}': ${e}`);
    }
    try {
        upstreamRaw = JSON.parse(fs.readFileSync(config.upstreamPath, "utf-8"));
    }
    catch (e) {
        throw new Error(`Failed to load upstream config from '${config.upstreamPath}': ${e}`);
    }
    const manifest = validateManifest(manifestRaw);
    const upstreamConfig = validateUpstreamConfig(upstreamRaw);
    // Connect to upstream as a client via subprocess
    const clientTransport = new StdioClientTransport({
        command: upstreamConfig.command,
        args: upstreamConfig.args,
        env: upstreamConfig.env,
    });
    const client = new Client({ name: "mcp-adapter-client", version: "1.0.0" }, { capabilities: {} });
    await client.connect(clientTransport);
    // Expose ourselves as an MCP server over this process's stdio
    const server = new Server({ name: "mcp-adapter", version: "1.0.0" }, { capabilities: { tools: {} } });
    server.setRequestHandler(ListToolsRequestSchema, async () => {
        const result = await client.listTools();
        const upstreamTools = result.tools;
        const exposed = projectUpstreamToolsWithManifest(upstreamTools, manifest, config.routingKey);
        return { tools: exposed };
    });
    server.setRequestHandler(CallToolRequestSchema, async (request) => {
        const { name, arguments: hostArgs = {} } = request.params;
        const typedHostArgs = hostArgs;
        // Need upstream tool list for planning
        const listResult = await client.listTools();
        const upstreamTools = listResult.tools;
        const plan = planToolCallWithManifest(name, typedHostArgs, manifest, upstreamTools, config.routingKey);
        switch (plan.decision) {
            case "absent":
                return errorResponse("Tool is not available");
            case "deny":
                return errorResponse("Tool is not permitted");
            case "ask":
                return errorResponse("Tool requires approval");
            case "simulate":
                return {
                    content: [
                        {
                            type: "text",
                            text: `[SIMULATED] Tool was called with args: ${JSON.stringify(plan.translatedArgs)}`,
                        },
                    ],
                    isError: false,
                };
            case "allow": {
                try {
                    evaluateAdapterConstraints(plan.constraints, plan.translatedArgs);
                }
                catch (e) {
                    if (e instanceof ConstraintViolationError) {
                        return errorResponse(e.message);
                    }
                    throw e;
                }
                const result = await client.callTool({
                    name: plan.upstreamToolName,
                    arguments: plan.translatedArgs,
                });
                return result;
            }
        }
    });
    const serverTransport = new StdioServerTransport();
    await server.connect(serverTransport);
    const shutdown = async () => {
        await client.close();
        process.exit(0);
    };
    process.on("SIGINT", shutdown);
    process.on("SIGTERM", shutdown);
}
