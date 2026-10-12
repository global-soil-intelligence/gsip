"""WP-OPS-2: compare sanitized catalog snapshots without database access or SQL execution.

Only exact audited baseline policy aliases and hosted-platform metadata additions are allowed.
This proves correspondence of the supplied catalog scope, not historical data effects or a
production deployment. Unknown values appear in output as SHA-256 fingerprints, never text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

Record = dict[str, Any]
Snapshot = dict[str, list[Record]]

CATALOG_SECTIONS = frozenset(
    {
        "tables",
        "columns",
        "indexes",
        "policies",
        "triggers",
        "functions",
        "extensions",
        "constraints",
        "table_grants",
        "column_grants",
    }
)
SUPPLEMENT_SECTIONS = frozenset({"views", "schema_grants", "storage_policies", "private_functions"})
SUBMISSION_POLICIES = (
    ("photos", "photos_insert_own"),
    ("gold_labels", "gold_labels_select_own"),
    ("photos", "photos_select_own"),
    ("predictions", "predictions_select_own"),
    ("priors", "priors_select_own"),
    ("qa_events", "qa_events_select_own"),
)
CANONICAL_PREDICATE = (
    "(submission_id IN ( SELECT submissions.id\n   FROM public.submissions\n"
    "  WHERE (submissions.contributor_id = public.current_contributor_id())))"
)
ALIASED_PREDICATE = (
    "(submission_id IN ( SELECT s.id\n   FROM public.submissions s\n"
    "  WHERE (s.contributor_id = public.current_contributor_id())))"
)
PLATFORM_EXTENSIONS = (
    {"name": "pg_stat_statements", "schema": "extensions", "version": "1.11"},
    {"name": "supabase_vault", "schema": "vault", "version": "0.3.1"},
    {"name": "uuid-ossp", "schema": "extensions", "version": "1.1"},
)
PLATFORM_GRANTS = (
    {"schema": "extensions", "role": "dashboard_user", "privilege": "CREATE", "grantable": False},
    {"schema": "extensions", "role": "dashboard_user", "privilege": "USAGE", "grantable": False},
    {"schema": "public", "role": "postgres", "privilege": "USAGE", "grantable": False},
)

_FUNCTION_FIELDS = {
    "owner": "str",
    "name": "str",
    "arguments": "str",
    "result": "str",
    "security_definer": "bool",
    "volatility": "str",
    "config": "nullable_strings",
    "definition_sha256": "digest",
    "grants": "grants",
}
_POLICY_FIELDS = {
    "table": "str",
    "name": "str",
    "command": "str",
    "permissive": "bool",
    "roles": "strings",
    "using": "nullable_str",
    "check": "nullable_str",
}
_FIELDS = {
    "tables": {"table": "str", "owner": "str", "rls": "bool", "force_rls": "bool"},
    "columns": {
        "table": "str",
        "column": "str",
        "type": "str",
        "default": "nullable_str",
        "not_null": "bool",
    },
    "indexes": {"table": "str", "name": "str", "definition": "str", "valid": "bool"},
    "policies": _POLICY_FIELDS,
    "triggers": {"table": "str", "name": "str", "definition": "str", "enabled": "str"},
    "functions": _FUNCTION_FIELDS,
    "extensions": {"name": "str", "schema": "str", "version": "str"},
    "constraints": {
        "table": "str",
        "name": "str",
        "type": "str",
        "definition": "str",
        "validated": "bool",
    },
    "table_grants": {"table": "str", "role": "str", "privilege": "str", "grantable": "bool"},
    "column_grants": {
        "table": "str",
        "column": "str",
        "role": "str",
        "privilege": "str",
        "grantable": "bool",
    },
    "views": {
        "name": "str",
        "kind": "str",
        "definition_sha256": "digest",
        "options": "nullable_strings",
    },
    "schema_grants": {"schema": "str", "role": "str", "privilege": "str", "grantable": "bool"},
    "storage_policies": _POLICY_FIELDS,
    "private_functions": _FUNCTION_FIELDS,
}
_IDENTITIES = {
    "tables": ("table",),
    "columns": ("table", "column"),
    "indexes": ("table", "name"),
    "policies": ("table", "name"),
    "triggers": ("table", "name"),
    "functions": ("name", "arguments"),
    "extensions": ("name",),
    "constraints": ("table", "name"),
    "table_grants": ("table", "role", "privilege"),
    "column_grants": ("table", "column", "role", "privilege"),
    "views": ("name",),
    "schema_grants": ("schema", "role", "privilege"),
    "storage_policies": ("table", "name"),
    "private_functions": ("name", "arguments"),
}


class EvidenceError(ValueError):
    """Malformed or incomplete catalog evidence; its untrusted values must not be logged."""


def _unique_strings(value: object) -> bool:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return False
    if len(value) != len(set(value)):
        raise EvidenceError("duplicate catalog string record")
    return True


def _valid_value(value: object, kind: str) -> bool:
    if kind == "str":
        return isinstance(value, str)
    if kind == "bool":
        return type(value) is bool
    if kind == "nullable_str":
        return value is None or isinstance(value, str)
    if kind == "digest":
        return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
    if kind in {"strings", "nullable_strings"}:
        return (value is None and kind == "nullable_strings") or _unique_strings(value)
    if kind == "grants":
        if not isinstance(value, list):
            return False
        seen = set()
        for item in value:
            if not isinstance(item, dict) or set(item) != {"role", "privilege", "grantable"}:
                return False
            if (
                not isinstance(item["role"], str)
                or not isinstance(item["privilege"], str)
                or type(item["grantable"]) is not bool
            ):
                return False
            identity = (item["role"], item["privilege"])
            if identity in seen:
                raise EvidenceError("duplicate function grant")
            seen.add(identity)
        return True
    raise EvidenceError("unknown catalog field contract")


def _validated_snapshot(value: object, sections: frozenset[str]) -> Snapshot:
    if not isinstance(value, dict) or set(value) != sections:
        raise EvidenceError("catalog sections are missing or unknown")
    result: Snapshot = {}
    for section in sorted(sections):
        rows = value[section]
        if not isinstance(rows, list):
            raise EvidenceError("catalog section must be an array")
        result[section] = []
        for row in rows:
            fields = _FIELDS[section]
            if not isinstance(row, dict) or set(row) != set(fields):
                raise EvidenceError("catalog record fields are missing or unknown")
            if not all(_valid_value(row[field], kind) for field, kind in fields.items()):
                raise EvidenceError("catalog record has invalid field types")
            result[section].append(dict(row))
    return result


def _index(section: str, records: list[Record]) -> dict[tuple[str, ...], Record]:
    result: dict[tuple[str, ...], Record] = {}
    for record in records:
        identity = tuple(record[field] for field in _IDENTITIES[section])
        if identity in result:
            raise EvidenceError("duplicate catalog identity")
        result[identity] = record
    return result


def policy_record(table: str, name: str, *, alias: bool) -> Record:
    """One of the six complete audited records; no SQL parsing or general normalization."""
    predicate = ALIASED_PREDICATE if alias else CANONICAL_PREDICATE
    insert = name == "photos_insert_own"
    return {
        "table": table,
        "name": name,
        "command": "a" if insert else "r",
        "permissive": True,
        "roles": ["authenticated"],
        "using": None if insert else predicate,
        "check": predicate if insert else None,
    }


def _allowed_policy(reference: Record, observed: Record) -> bool:
    return any(
        reference == policy_record(table, name, alias=False)
        and observed == policy_record(table, name, alias=True)
        for table, name in SUBMISSION_POLICIES
    )


def _fingerprint(record: Record) -> str:
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def compare_catalogs(
    reference_catalog: object,
    observed_catalog: object,
    reference_supplement: object,
    observed_supplement: object,
) -> dict[str, Any]:
    reference = {
        **_validated_snapshot(reference_catalog, CATALOG_SECTIONS),
        **_validated_snapshot(reference_supplement, SUPPLEMENT_SECTIONS),
    }
    observed = {
        **_validated_snapshot(observed_catalog, CATALOG_SECTIONS),
        **_validated_snapshot(observed_supplement, SUPPLEMENT_SECTIONS),
    }
    allowed = []
    unexpected = []
    for section in sorted(reference):
        left, right = _index(section, reference[section]), _index(section, observed[section])
        for identity in sorted(left.keys() | right.keys()):
            first, second = left.get(identity), right.get(identity)
            if first == second:
                continue
            if section == "policies" and first is not None and second is not None:
                if _allowed_policy(first, second):
                    allowed.append(
                        {
                            "section": section,
                            "kind": "exact_submission_alias",
                            "identifier": second["name"],
                        }
                    )
                    continue
            if first is None and second is not None:
                if section == "extensions" and second in PLATFORM_EXTENSIONS:
                    allowed.append(
                        {
                            "section": section,
                            "kind": "exact_platform_addition",
                            "identifier": second["name"],
                        }
                    )
                    continue
                if section == "schema_grants" and second in PLATFORM_GRANTS:
                    allowed.append(
                        {
                            "section": section,
                            "kind": "exact_platform_addition",
                            "identifier": ".".join(identity),
                        }
                    )
                    continue
            record = second if second is not None else first
            if record is None:
                raise EvidenceError("catalog comparison has no record")
            unexpected.append(
                {
                    "section": section,
                    "kind": "missing"
                    if second is None
                    else "unexpected"
                    if first is None
                    else "changed",
                    "fingerprint": _fingerprint(record),
                }
            )
    return {
        "ok": not unexpected,
        "scope": "provided catalog metadata only; no data or deployment proof",
        "counts": {
            section: {"reference": len(reference[section]), "observed": len(observed[section])}
            for section in sorted(reference)
        },
        "allowed_differences": allowed,
        "unexpected_differences": unexpected,
    }


def _object_pairs(pairs: list[tuple[str, Any]]) -> Record:
    result: Record = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> Any:
    raise EvidenceError("non-JSON numeric constant")


def _parse_snapshot(text: str) -> object:
    return json.loads(text, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)


def load_snapshot(path: Path) -> object:
    return _parse_snapshot(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    flags = ("reference-catalog", "observed-catalog", "reference-supplement", "observed-supplement")
    for flag in flags:
        parser.add_argument(f"--{flag}", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        snapshots = []
        digests = {}
        for flag in flags:
            raw = getattr(args, flag.replace("-", "_")).read_bytes()
            snapshots.append(_parse_snapshot(raw.decode("utf-8")))
            digests[flag] = hashlib.sha256(raw).hexdigest()
        result = compare_catalogs(*snapshots)
        result["input_sha256"] = digests
    except (OSError, ValueError):
        result = {"ok": False, "reason": "invalid_or_incomplete_catalog_evidence"}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
