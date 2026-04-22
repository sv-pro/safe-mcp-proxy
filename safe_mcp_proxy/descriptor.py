import hashlib
import json
from typing import Any, Dict


def normalize_schema(schema: Dict[str, Any]) -> str:
    """Return a deterministic JSON string for hashing."""
    return json.dumps(schema, sort_keys=True, separators=(",", ":"))


def compute_descriptor_hash(schema: Dict[str, Any]) -> str:
    normalized = normalize_schema(schema)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def descriptor_hash_valid(schema: Dict[str, Any], expected_hash: str) -> bool:
    return compute_descriptor_hash(schema) == expected_hash
