import * as path from "node:path";
import * as fs from "node:fs";
export class ConstraintViolationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ConstraintViolationError";
    }
}
function nearestExistingPath(p) {
    let current = p;
    while (!fs.existsSync(current)) {
        const parent = path.dirname(current);
        if (parent === current)
            return current; // reached filesystem root
        current = parent;
    }
    return current;
}
function checkPathWithin(value, base) {
    const resolvedBase = path.resolve(base);
    const requested = path.isAbsolute(value)
        ? path.resolve(value)
        : path.resolve(resolvedBase, value);
    // Lexical check: no traversal above base
    const rel = path.relative(resolvedBase, requested);
    if (rel.startsWith("..") || path.isAbsolute(rel)) {
        throw new ConstraintViolationError(`Path '${value}' escapes base directory '${base}' (lexical check)`);
    }
    // Symlink check: resolve to real paths for symlink-attack prevention
    const baseReal = fs.realpathSync(resolvedBase);
    const existing = nearestExistingPath(requested);
    const existingReal = fs.realpathSync(existing);
    const rel2 = path.relative(baseReal, existingReal);
    if (rel2.startsWith("..") || path.isAbsolute(rel2)) {
        throw new ConstraintViolationError(`Path '${value}' resolves outside base directory '${base}' (symlink check)`);
    }
}
export function evaluateAdapterConstraints(constraints, translatedArgs) {
    for (const constraint of constraints) {
        if (constraint.kind === "path_within") {
            const value = translatedArgs[constraint.arg];
            if (typeof value !== "string") {
                throw new ConstraintViolationError(`Argument '${constraint.arg}' must be a string for path_within constraint (got ${typeof value})`);
            }
            checkPathWithin(value, constraint.base);
        }
        else {
            // future-proof: unknown constraint kinds are rejected
            throw new ConstraintViolationError(`Unknown constraint kind: '${constraint.kind}'`);
        }
    }
}
