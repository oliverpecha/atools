"""In-tree Draft 2020-12 JSON Schema validator (never imports jsonschema)."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = REPO_ROOT / "schemas"

VALID_KINDS = (
    "common",
    "state",
    "sprint",
    "sprint-proposal",
    "closure",
    "ev",
    "qual",
    "contract",
    "oracle-decision",
    "prior_attempt",
    "meta",
    "attempt",
)

_SUPPORTED = frozenset(
    {
        "$schema",
        "$id",
        "$defs",
        "$ref",
        "type",
        "enum",
        "const",
        "pattern",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "prefixItems",
        "anyOf",
        "oneOf",
        "allOf",
        "if",
        "then",
        "else",
        "not",
        "description",
        "title",
        "default",
        "examples",
    }
)
# $defs is intentional; listed above

_schema_cache: dict[str, Any] = {}


@dataclass
class StepResult:
    id: str
    cmd: str
    exit_code: int
    output_sha256: str
    output_tail: str = ""
    duration_ms: int = 0
    failing_line: str | None = None

    def to_ev_step(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cmd": self.cmd,
            "exit_code": self.exit_code,
            "output_sha256": self.output_sha256,
        }


def _escape(tok: str) -> str:
    return tok.replace("~", "~0").replace("/", "~1")


def _child(parent: str, tok: str) -> str:
    esc = _escape(tok)
    if parent == "/":
        return f"/{esc}"
    return f"{parent}/{esc}"


def _is_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _is_number(x: Any) -> bool:
    if isinstance(x, bool):
        return False
    if isinstance(x, int):
        return True
    if isinstance(x, float):
        return not (math.isnan(x) or math.isinf(x))
    return False


def _load_schema_file(name: str) -> Any:
    if name not in _schema_cache:
        path = SCHEMAS_DIR / name
        if not path.is_file():
            raise ValueError(f"Schema file missing: {name}")
        doc = json.loads(path.read_text(encoding="utf-8"))
        _check_supported(doc, name)
        _schema_cache[name] = doc
    return _schema_cache[name]


def _check_supported(node: Any, where: str, *, as_schema: bool = True) -> None:
    if isinstance(node, dict):
        if as_schema:
            for k in node:
                if k.startswith("$"):
                    if k not in ("$schema", "$id", "$defs", "$ref"):
                        raise ValueError(f"Unsupported schema keyword {k!r} in {where}")
                elif k not in _SUPPORTED:
                    raise ValueError(f"Unsupported schema keyword {k!r} in {where}")
            for k, v in node.items():
                if k in ("properties", "$defs", "patternProperties", "dependentSchemas"):
                    # keys under these maps are names, not keywords
                    if isinstance(v, dict):
                        for sub in v.values():
                            _check_supported(sub, where, as_schema=True)
                    else:
                        _check_supported(v, where, as_schema=True)
                elif k in ("allOf", "anyOf", "oneOf", "prefixItems"):
                    if isinstance(v, list):
                        for sub in v:
                            _check_supported(sub, where, as_schema=True)
                elif k in (
                    "items",
                    "additionalProperties",
                    "not",
                    "if",
                    "then",
                    "else",
                    "contains",
                    "propertyNames",
                ):
                    if isinstance(v, (dict, list)):
                        _check_supported(v, where, as_schema=True)
                # primitive keyword values (type/enum/const/...) need no recursion
        else:
            for v in node.values():
                _check_supported(v, where, as_schema=True)
    elif isinstance(node, list):
        for v in node:
            _check_supported(v, where, as_schema=as_schema)


def _resolve_ref(ref: str, current_doc: Any, doc_name: str) -> tuple[Any, Any, str]:
    if ref.startswith("#"):
        return _resolve_pointer(current_doc, ref[1:] or "/"), current_doc, doc_name
    if "#" in ref:
        file_part, frag = ref.split("#", 1)
    else:
        file_part, frag = ref, ""
    target_name = file_part if file_part.endswith(".json") else file_part
    if "/" in target_name:
        target_name = Path(target_name).name
    doc = _load_schema_file(target_name)
    return _resolve_pointer(doc, frag or "/"), doc, target_name


def _resolve_pointer(doc: Any, pointer: str) -> Any:
    if pointer in ("", "/"):
        return doc
    if not pointer.startswith("/"):
        pointer = "/" + pointer
    cur: Any = doc
    for raw in pointer.lstrip("/").split("/"):
        tok = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            if tok not in cur:
                raise ValueError(f"Unresolved $ref pointer: {pointer}")
            cur = cur[tok]
        else:
            raise ValueError(f"Unresolved $ref pointer: {pointer}")
    return cur


def _type_ok(val: Any, t: str) -> bool:
    if t == "object":
        return isinstance(val, dict)
    if t == "array":
        return isinstance(val, list)
    if t == "string":
        return isinstance(val, str)
    if t == "integer":
        return _is_int(val)
    if t == "number":
        return _is_number(val)
    if t == "boolean":
        return isinstance(val, bool)
    if t == "null":
        return val is None
    return False


def _validate_schema(
    instance: Any,
    schema: Any,
    ptr: str,
    errors: list[dict[str, str]],
    current_doc: Any,
    doc_name: str,
) -> None:
    if not isinstance(schema, dict):
        return

    if "$ref" in schema:
        target, new_doc, new_name = _resolve_ref(schema["$ref"], current_doc, doc_name)
        _validate_schema(instance, target, ptr, errors, new_doc, new_name)
        # other keywords alongside $ref are ignored in older drafts; Draft 2020-12
        # allows sibling keywords — apply remaining keywords too
        rest = {k: v for k, v in schema.items() if k != "$ref"}
        if rest:
            _validate_schema(instance, rest, ptr, errors, current_doc, doc_name)
        return

    if "type" in schema:
        types = schema["type"]
        type_list = types if isinstance(types, list) else [types]
        if not any(_type_ok(instance, t) for t in type_list):
            errors.append({"path": ptr, "message": f"Type mismatch, expected {types}"})
            return

    if "const" in schema:
        if instance != schema["const"]:
            errors.append({"path": ptr, "message": f"Expected const {schema['const']!r}"})

    if "enum" in schema:
        if instance not in schema["enum"]:
            errors.append({"path": ptr, "message": f"Value not in enum: {instance!r}"})

    if isinstance(instance, str):
        if "pattern" in schema:
            if re.search(schema["pattern"], instance) is None:
                # JSON Schema pattern is unanchored; fixtures use ^...$ so search == fullmatch
                errors.append({"path": ptr, "message": f"Pattern mismatch: {schema['pattern']}"})
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append({"path": ptr, "message": f"String shorter than minLength {schema['minLength']}"})
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append({"path": ptr, "message": f"String longer than maxLength {schema['maxLength']}"})

    if _is_number(instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append({"path": ptr, "message": f"Value below minimum {schema['minimum']}"})
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append({"path": ptr, "message": f"Value above maximum {schema['maximum']}"})
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append({"path": ptr, "message": f"Value not above exclusiveMinimum {schema['exclusiveMinimum']}"})
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append({"path": ptr, "message": f"Value not below exclusiveMaximum {schema['exclusiveMaximum']}"})

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append({"path": ptr, "message": f"Array shorter than minItems {schema['minItems']}"})
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append({"path": ptr, "message": f"Array longer than maxItems {schema['maxItems']}"})
        if "prefixItems" in schema:
            for i, sub in enumerate(schema["prefixItems"]):
                if i < len(instance):
                    _validate_schema(instance[i], sub, _child(ptr, str(i)), errors, current_doc, doc_name)
        if "items" in schema:
            items_schema = schema["items"]
            start = len(schema.get("prefixItems", []))
            for i in range(start, len(instance)):
                _validate_schema(instance[i], items_schema, _child(ptr, str(i)), errors, current_doc, doc_name)

    if isinstance(instance, dict):
        props = schema.get("properties") or {}
        if "required" in schema:
            for prop in schema["required"]:
                if prop not in instance:
                    errors.append(
                        {
                            "path": _child(ptr, prop),
                            "message": f"Missing required property: {prop}",
                        }
                    )
        for k, v in instance.items():
            if k in props:
                _validate_schema(v, props[k], _child(ptr, k), errors, current_doc, doc_name)
            elif "additionalProperties" in schema:
                add = schema["additionalProperties"]
                if add is False:
                    errors.append(
                        {
                            "path": _child(ptr, k),
                            "message": f"Additional property not allowed: {k}",
                        }
                    )
                elif isinstance(add, dict):
                    _validate_schema(v, add, _child(ptr, k), errors, current_doc, doc_name)

    if "allOf" in schema:
        for sub in schema["allOf"]:
            _validate_schema(instance, sub, ptr, errors, current_doc, doc_name)

    if "anyOf" in schema:
        branch_errs: list[list[dict[str, str]]] = []
        matched = False
        for sub in schema["anyOf"]:
            be: list[dict[str, str]] = []
            _validate_schema(instance, sub, ptr, be, current_doc, doc_name)
            if not be:
                matched = True
                break
            branch_errs.append(be)
        if not matched:
            errors.append({"path": ptr, "message": "anyOf: no branch matched"})

    if "oneOf" in schema:
        matches = 0
        best_errs: list[dict[str, str]] = []
        for sub in schema["oneOf"]:
            be = []
            _validate_schema(instance, sub, ptr, be, current_doc, doc_name)
            if not be:
                matches += 1
            elif isinstance(instance, dict) and isinstance(sub, dict):
                looks_object = (
                    sub.get("type") == "object"
                    or (isinstance(sub.get("type"), list) and "object" in sub["type"])
                    or "properties" in sub
                    or "required" in sub
                )
                if looks_object and (not best_errs or len(be) <= len(best_errs)):
                    best_errs = be
        if matches != 1:
            if matches == 0 and best_errs:
                errors.extend(best_errs)
            else:
                errors.append(
                    {"path": ptr, "message": f"oneOf: expected 1 match, got {matches}"}
                )

    if "not" in schema:
        be = []
        _validate_schema(instance, schema["not"], ptr, be, current_doc, doc_name)
        if not be:
            errors.append({"path": ptr, "message": "not: schema matched unexpectedly"})

    if "if" in schema:
        be = []
        _validate_schema(instance, schema["if"], ptr, be, current_doc, doc_name)
        if not be:
            if "then" in schema:
                _validate_schema(instance, schema["then"], ptr, errors, current_doc, doc_name)
        else:
            if "else" in schema:
                _validate_schema(instance, schema["else"], ptr, errors, current_doc, doc_name)


def validate(kind: str, obj: Any) -> list[dict[str, str]]:
    if kind not in VALID_KINDS:
        raise ValueError(f"Unknown schema kind: {kind}")
    if not isinstance(obj, dict):
        return [{"path": "/", "message": "Root value must be a JSON object"}]
    schema = _load_schema_file(f"{kind}.json")
    errors: list[dict[str, str]] = []
    _validate_schema(obj, schema, "/", errors, schema, f"{kind}.json")
    # dedupe and sort
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, str]] = []
    for e in errors:
        key = (e["path"], e["message"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    unique.sort(key=lambda e: (e["path"], e["message"]))
    return unique


def load_expected(expected_dir: Path | str | None = None) -> dict[str, Any]:
    if expected_dir is None:
        expected_dir = REPO_ROOT / "fixtures" / "golden" / "expected.d"
    ed = Path(expected_dir)
    if not ed.is_dir():
        raise FileNotFoundError(str(ed))
    base_sha: str | None = None
    cases: dict[str, Any] = {}
    responses: dict[str, Any] = {}
    for path in sorted(ed.glob("*.json"), key=lambda p: p.name):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
        if not isinstance(doc, dict):
            raise ValueError(f"Expected object in {path}")
        if "base_sha" in doc:
            if base_sha is not None or not isinstance(doc["base_sha"], str):
                raise ValueError("Duplicate or invalid base_sha")
            base_sha = doc["base_sha"]
        if "cases" in doc:
            if not isinstance(doc["cases"], dict):
                raise ValueError("cases must be an object")
            for k, v in doc["cases"].items():
                if k in cases:
                    raise ValueError(f"Duplicate case key: {k}")
                cases[k] = v
        if "responses" in doc:
            if not isinstance(doc["responses"], dict):
                raise ValueError("responses must be an object")
            for k, v in doc["responses"].items():
                if k in responses:
                    raise ValueError(f"Duplicate response key: {k}")
                responses[k] = v
    return {"base_sha": base_sha, "cases": cases, "responses": responses}
