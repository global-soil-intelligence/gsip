"""WP-OPS-2: catalog comparison fails closed outside exact audited metadata differences."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import reconciliation as reconcile

CANONICAL = (
    "(submission_id IN ( SELECT submissions.id\n   FROM public.submissions\n"
    "  WHERE (submissions.contributor_id = public.current_contributor_id())))"
)
ALIASED = (
    "(submission_id IN ( SELECT s.id\n   FROM public.submissions s\n"
    "  WHERE (s.contributor_id = public.current_contributor_id())))"
)
POLICIES = (
    ("photos", "photos_insert_own"),
    ("gold_labels", "gold_labels_select_own"),
    ("photos", "photos_select_own"),
    ("predictions", "predictions_select_own"),
    ("priors", "priors_select_own"),
    ("qa_events", "qa_events_select_own"),
)


def policy(table: str, name: str, predicate: str) -> dict[str, Any]:
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


def evidence() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    reference: dict[str, Any] = {
        section: []
        for section in (
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
        )
    }
    reference["tables"] = [
        {"table": "synthetic_table", "owner": "postgres", "rls": True, "force_rls": False}
    ]
    reference["functions"] = [
        {
            "name": "synthetic_function",
            "owner": "postgres",
            "arguments": "",
            "result": "boolean",
            "security_definer": False,
            "volatility": "s",
            "config": ['search_path=""'],
            "definition_sha256": "a" * 64,
            "grants": [{"role": "postgres", "privilege": "EXECUTE", "grantable": False}],
        }
    ]
    reference["policies"] = [policy(table, name, CANONICAL) for table, name in POLICIES]
    observed = copy.deepcopy(reference)
    observed["policies"] = [policy(table, name, ALIASED) for table, name in POLICIES]
    observed["extensions"] = [
        {"name": "pg_stat_statements", "schema": "extensions", "version": "1.11"},
        {"name": "supabase_vault", "schema": "vault", "version": "0.3.1"},
        {"name": "uuid-ossp", "schema": "extensions", "version": "1.1"},
    ]
    supplement: dict[str, Any] = {
        section: []
        for section in (
            "views",
            "schema_grants",
            "storage_policies",
            "private_functions",
        )
    }
    supplement["private_functions"] = [
        {
            **copy.deepcopy(reference["functions"][0]),
            "name": "synthetic_private_function",
            "security_definer": True,
        }
    ]
    observed_supplement = copy.deepcopy(supplement)
    observed_supplement["schema_grants"] = [
        {
            "schema": "extensions",
            "role": "dashboard_user",
            "privilege": "CREATE",
            "grantable": False,
        },
        {
            "schema": "extensions",
            "role": "dashboard_user",
            "privilege": "USAGE",
            "grantable": False,
        },
        {"schema": "public", "role": "postgres", "privilege": "USAGE", "grantable": False},
    ]
    return reference, observed, supplement, observed_supplement


def test_only_the_exact_audited_differences_pass() -> None:
    inputs = evidence()
    result = reconcile.compare_catalogs(*inputs)
    assert result["ok"] is True
    assert result["unexpected_differences"] == []
    assert len(result["allowed_differences"]) == 12
    assert result["scope"] == "provided catalog metadata only; no data or deployment proof"
    assert "SELECT" not in json.dumps(result)
    assert "definition_sha256" not in json.dumps(result)


def test_record_and_object_key_order_do_not_change_metadata_comparison() -> None:
    reference, observed, supplement, observed_supplement = evidence()
    observed["policies"].reverse()
    observed["functions"] = [dict(reversed(list(observed["functions"][0].items())))]
    assert reconcile.compare_catalogs(reference, observed, supplement, observed_supplement)["ok"]


@pytest.mark.parametrize(
    "section,field,value",
    [
        ("tables", "rls", False),
        ("tables", "owner", "anon"),
        ("functions", "owner", "anon"),
        ("functions", "grants", [{"role": "postgres", "privilege": "EXECUTE", "grantable": True}]),
        ("functions", "definition_sha256", "b" * 64),
        ("functions", "security_definer", True),
        ("functions", "grants", [{"role": "anon", "privilege": "EXECUTE", "grantable": False}]),
        ("policies", "roles", ["anon"]),
        ("policies", "permissive", False),
        ("policies", "using", "true"),
        ("policies", "check", "true"),
        ("policies", "command", "*"),
        ("policies", "using", ALIASED.replace("s.id", "other.id")),
    ],
)
def test_unapproved_metadata_drift_fails(section: str, field: str, value: Any) -> None:
    reference, observed, supplement, observed_supplement = evidence()
    observed[section][0][field] = value
    result = reconcile.compare_catalogs(reference, observed, supplement, observed_supplement)
    assert result["ok"] is False
    assert result["unexpected_differences"]
    assert all(
        set(item) == {"section", "kind", "fingerprint"} for item in result["unexpected_differences"]
    )
    assert "SELECT" not in json.dumps(result)


@pytest.mark.parametrize(
    "kind", ["extension_version", "extension_schema", "grant_role", "grantable"]
)
def test_platform_allowlist_cannot_expand(kind: str) -> None:
    reference, observed, supplement, observed_supplement = evidence()
    if kind == "extension_version":
        observed["extensions"][0]["version"] = "999"
    elif kind == "extension_schema":
        observed["extensions"][0]["schema"] = "public"
    elif kind == "grant_role":
        observed_supplement["schema_grants"][0]["role"] = "anon"
    else:
        observed_supplement["schema_grants"][0]["grantable"] = True
    assert not reconcile.compare_catalogs(reference, observed, supplement, observed_supplement)[
        "ok"
    ]


def test_allowed_platform_records_cannot_hide_a_missing_reference_record() -> None:
    reference, observed, supplement, observed_supplement = evidence()
    reference["extensions"] = [dict(observed["extensions"][0])]
    observed["extensions"].pop(0)
    assert not reconcile.compare_catalogs(reference, observed, supplement, observed_supplement)[
        "ok"
    ]


@pytest.mark.parametrize("catalog_index", [0, 1, 2, 3])
def test_missing_or_unknown_sections_are_not_empty_evidence(catalog_index: int) -> None:
    inputs = list(evidence())
    section = next(iter(inputs[catalog_index]))
    del inputs[catalog_index][section]
    with pytest.raises(reconcile.EvidenceError, match="sections"):
        reconcile.compare_catalogs(*inputs)
    inputs = list(evidence())
    inputs[catalog_index]["not_a_catalog_section"] = []
    with pytest.raises(reconcile.EvidenceError, match="sections"):
        reconcile.compare_catalogs(*inputs)


@pytest.mark.parametrize("kind", ["record", "identity", "roles", "function_grant"])
def test_duplicate_records_and_nested_identities_fail(kind: str) -> None:
    inputs = list(evidence())
    observed = inputs[1]
    if kind in {"record", "identity"}:
        duplicate = dict(observed["tables"][0])
        if kind == "identity":
            duplicate["rls"] = False
        observed["tables"].append(duplicate)
    elif kind == "roles":
        observed["policies"][0]["roles"] *= 2
    else:
        observed["functions"][0]["grants"] *= 2
    with pytest.raises(reconcile.EvidenceError, match="duplicate"):
        reconcile.compare_catalogs(*inputs)


@pytest.mark.parametrize(
    "kind", ["not_list", "not_record", "unknown_field", "bool_as_integer", "bad_digest"]
)
def test_malformed_catalog_records_fail(kind: str) -> None:
    inputs = list(evidence())
    observed = inputs[1]
    if kind == "not_list":
        observed["tables"] = {}
    elif kind == "not_record":
        observed["tables"] = [None]
    elif kind == "unknown_field":
        observed["tables"][0]["private_contents"] = "never print this value"
    elif kind == "bool_as_integer":
        observed["tables"][0]["rls"] = 1
    else:
        observed["functions"][0]["definition_sha256"] = "not a digest"
    with pytest.raises(reconcile.EvidenceError):
        reconcile.compare_catalogs(*inputs)


def test_json_loader_rejects_duplicate_keys_and_non_json_numbers(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.json"
    path.write_text('{"tables": [], "tables": []}')
    with pytest.raises(reconcile.EvidenceError, match="duplicate"):
        reconcile.load_snapshot(path)
    path.write_text('{"tables": NaN}')
    with pytest.raises(reconcile.EvidenceError):
        reconcile.load_snapshot(path)


def test_cli_exit_status_tracks_drift_without_printing_input_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    inputs = list(evidence())
    arguments: list[str] = []
    for flag, value in zip(
        (
            "--reference-catalog",
            "--observed-catalog",
            "--reference-supplement",
            "--observed-supplement",
        ),
        inputs,
        strict=True,
    ):
        path = tmp_path / f"{flag[2:]}.json"
        path.write_text(json.dumps(value))
        arguments.extend((flag, str(path)))
    assert reconcile.main(arguments) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    inputs[1]["tables"][0]["table"] = "private marker never logged"
    (tmp_path / "observed-catalog.json").write_text(json.dumps(inputs[1]))
    assert reconcile.main(arguments) == 1
    output = capsys.readouterr().out
    assert json.loads(output)["ok"] is False
    assert "private marker" not in output
    (tmp_path / "observed-supplement.json").write_text("{}")
    assert reconcile.main(arguments) == 1
    assert json.loads(capsys.readouterr().out)["ok"] is False


@pytest.mark.parametrize("index", range(6))
def test_each_allowlisted_policy_still_rejects_changed_predicates(index: int) -> None:
    inputs = list(evidence())
    record = inputs[1]["policies"][index]
    field = "check" if record["command"] == "a" else "using"
    record[field] = ALIASED + " OR true"
    assert not reconcile.compare_catalogs(*inputs)["ok"]


def test_alias_permission_does_not_apply_to_another_policy() -> None:
    inputs = list(evidence())
    inputs[0]["policies"].append(policy("synthetic_table", "synthetic_policy", CANONICAL))
    inputs[1]["policies"].append(policy("synthetic_table", "synthetic_policy", ALIASED))
    assert not reconcile.compare_catalogs(*inputs)["ok"]


def test_owner_and_function_grantability_metadata_are_required() -> None:
    inputs = list(evidence())
    for snapshot in inputs[:2]:
        for table in snapshot["tables"]:
            table.pop("owner", None)
        for function in snapshot["functions"]:
            function.pop("owner", None)
            for grant in function["grants"]:
                grant.pop("grantable", None)
    with pytest.raises(reconcile.EvidenceError):
        reconcile.compare_catalogs(*inputs)


@pytest.mark.parametrize(
    "kind",
    ["table_owner", "function_owner", "private_owner", "grantability", "private_grantability"],
)
def test_each_owner_or_grantability_field_is_required(kind: str) -> None:
    inputs = list(evidence())
    if kind == "table_owner":
        del inputs[1]["tables"][0]["owner"]
    elif kind == "function_owner":
        del inputs[1]["functions"][0]["owner"]
    elif kind == "private_owner":
        del inputs[3]["private_functions"][0]["owner"]
    elif kind == "grantability":
        del inputs[1]["functions"][0]["grants"][0]["grantable"]
    else:
        del inputs[3]["private_functions"][0]["grants"][0]["grantable"]
    with pytest.raises(reconcile.EvidenceError):
        reconcile.compare_catalogs(*inputs)


@pytest.mark.parametrize("kind", ["owner", "grantability", "grant_bool_as_integer"])
def test_private_function_ownership_and_grant_escalation_fail(kind: str) -> None:
    inputs = list(evidence())
    function = inputs[3]["private_functions"][0]
    if kind == "owner":
        function["owner"] = "anon"
    elif kind == "grantability":
        function["grants"][0]["grantable"] = True
    else:
        function["grants"][0]["grantable"] = 1
        with pytest.raises(reconcile.EvidenceError):
            reconcile.compare_catalogs(*inputs)
        return
    assert not reconcile.compare_catalogs(*inputs)["ok"]
