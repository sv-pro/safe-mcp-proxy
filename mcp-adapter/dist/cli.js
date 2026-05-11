#!/usr/bin/env node
import { runAdapterStdio } from "./adapter.js";
function parseArgs() {
    const argv = process.argv.slice(2);
    let manifestPath = process.env["MANIFEST_PATH"] ?? "";
    let upstreamPath = process.env["UPSTREAM_PATH"] ?? "";
    let routingKey = process.env["ROUTING_KEY"] ?? "default";
    for (let i = 0; i < argv.length; i++) {
        if (argv[i] === "--manifest" && argv[i + 1]) {
            manifestPath = argv[++i];
        }
        else if (argv[i] === "--upstream" && argv[i + 1]) {
            upstreamPath = argv[++i];
        }
        else if (argv[i] === "--routing-key" && argv[i + 1]) {
            routingKey = argv[++i];
        }
        else if (argv[i] === "--help" || argv[i] === "-h") {
            printUsage();
            process.exit(0);
        }
    }
    if (!manifestPath || !upstreamPath) {
        printUsage();
        process.exit(1);
    }
    return { manifestPath, upstreamPath, routingKey };
}
function printUsage() {
    process.stderr.write([
        "Usage: mcp-adapter --manifest <path> --upstream <path> [--routing-key <key>]",
        "",
        "Options:",
        "  --manifest <path>      Path to manifest.json (or set MANIFEST_PATH env var)",
        "  --upstream <path>      Path to upstream.json (or set UPSTREAM_PATH env var)",
        "  --routing-key <key>    Routing key to match manifest rows (default: \"default\")",
        "                         (or set ROUTING_KEY env var)",
        "  --help, -h             Show this help message",
        "",
    ].join("\n"));
}
const args = parseArgs();
runAdapterStdio(args).catch((err) => {
    process.stderr.write(`mcp-adapter error: ${err}\n`);
    process.exit(1);
});
