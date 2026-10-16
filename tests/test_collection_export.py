"""Pilot collection cannot enter a public artifact, including through manual/cached export."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
import test_export as fixtures

from pipeline import export

VERSION = "gsip-collection-publication-v1"
ALLOW = {"version": VERSION, "publication_allowed": True}
HELD = {"version": VERSION, "publication_allowed": False}
CAPABILITY_PATH = "/rest/v1/rpc/collection_publication_capabilities"


def source_with_capability(
    raw: bytes | dict[str, Any],
) -> tuple[export.SupabaseExportSource, list[str]]:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == CAPABILITY_PATH:
            assert request.method == "POST" and json.loads(request.content) == {}
            return (
                httpx.Response(200, content=raw)
                if isinstance(raw, bytes)
                else httpx.Response(200, json=raw)
            )
        raise AssertionError("A held export accessed private candidates or a publication target")

    source = export.SupabaseExportSource("https://supabase.test", "fixture")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    return source, seen


@pytest.mark.parametrize(
    "raw",
    [
        HELD,
        {},
        {"version": "unknown", "publication_allowed": True},
        {**ALLOW, "unknown": False},
        {"version": VERSION, "publication_allowed": "true"},
        {"version": VERSION, "publication_allowed": 1},
        {"version": VERSION, "publication_allowed": None},
        b"null",
        b"[]",
        b'{"version":"gsip-collection-publication-v1","publication_allowed":false,'
        b'"publication_allowed":true}',
        b'{"version":"gsip-collection-publication-v1","publication_allowed":NaN}',
        b'{"version":"gsip-collection-publication-v1","publication_allowed":Infinity}',
        b" " * 4096 + json.dumps(ALLOW).encode(),
        b"[" * 1100 + b"0" + b"]" * 1100,
    ],
)
def test_held_missing_unknown_or_ambiguous_capability_precedes_candidate_reads(
    raw: bytes | dict[str, Any],
) -> None:
    source, seen = source_with_capability(raw)
    try:
        with pytest.raises(export.ExportPrivacyError, match="publication"):
            source.submissions()
    finally:
        source.client.close()
    assert seen == [CAPABILITY_PATH]


@pytest.mark.parametrize("boundary", ["photo", "cells", "release", "cached"])
def test_publication_hold_precedes_photo_cache_and_external_publication(
    tmp_path: Path, boundary: str
) -> None:
    source, seen = source_with_capability(HELD)
    try:
        with pytest.raises(export.ExportPrivacyError, match="publication"):
            if boundary == "photo":
                source.photo("never-read.jpg")
            elif boundary == "cells":
                source.refresh_h3_cells(())
            elif boundary == "release":
                source.record_release("2026-10-16", 0, 0, None)
            else:
                # Nonexistent cache proves the hold is checked before inspecting any path.
                result = export.ExportResult(tmp_path / "absent", (), 0, 0)
                export.publish_export(source, result, fixtures.EXPORT_DATE, "fixture", "fake/data")
    finally:
        source.client.close()
    assert seen == [CAPABILITY_PATH]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("scope", ["private_pilot", "unknown", "", None, True])
def test_pilot_or_unknown_scope_refuses_before_photo_policy_staging_and_aggregation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scope: Any
) -> None:
    rows = fixtures.three_contributors_in_one_cell()
    rows.append(replace(fixtures.submission(4), collection_scope=scope))

    class UnreadPrivacy(fixtures.SyntheticPrivacy):
        def policy(self) -> Any:
            raise AssertionError("Scope refusal must precede photo-policy reads")

    def no_aggregation(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Pilot rows must not reach public aggregation")

    monkeypatch.setattr(export, "assign_cells", no_aggregation)
    target = tmp_path / "public"
    with pytest.raises(export.ExportPrivacyError, match="collection scope"):
        export.build_export(
            rows,
            target,
            fixtures.EXPORT_DATE,
            lambda _: pytest.fail("Pilot photos must not be read"),
            photo_privacy=UnreadPrivacy(),
        )
    assert not target.exists()


@pytest.mark.parametrize("scope", ["missing", "private_pilot", "unknown", None, True])
def test_real_adapter_requires_explicit_legacy_scope_before_per_row_private_reads(
    scope: Any,
) -> None:
    tables = fixtures.source_tables("Anonymous soil contributor", [], [])
    if scope == "missing":
        tables["submissions"][0].pop("collection_scope")
    else:
        tables["submissions"][0]["collection_scope"] = scope
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        seen.append(path)
        if path == CAPABILITY_PATH:
            return httpx.Response(200, json=ALLOW)
        name = path.rsplit("/", 1)[-1]
        assert name in {"submissions", "grant_withdrawals", "attribution_reviews"}
        return httpx.Response(200, json=tables[name])

    source = export.SupabaseExportSource("https://supabase.test", "fixture")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(export.ExportPrivacyError, match="collection scope"):
            source.submissions()
    finally:
        source.client.close()
    assert "/rest/v1/submissions" in seen
    assert not any(path.endswith(("contribution_grants", "photos", "gold_labels")) for path in seen)


class SyntheticPublicationSource(export.SupabaseExportSource):
    """Trusted synthetic source only; the real migration has no operation to return allow=True."""

    allowed = True

    def collection_publication_capabilities(self) -> dict[str, Any]:
        return {"version": VERSION, "publication_allowed": self.allowed}

    @property
    def photo_privacy(self) -> fixtures.SyntheticPrivacy:
        return fixtures.SyntheticPrivacy()

    def withdrawn_grant_ids(self) -> set[str]:
        return set()


def test_publication_rechecks_after_artifact_validation_before_constructing_hub(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = fixtures.build(fixtures.three_contributors_in_one_cell(), tmp_path)
    source = SyntheticPublicationSource("https://supabase.test", "fixture")
    original = export._verify_public_artifact

    def close_after_validation(result: export.ExportResult) -> None:
        original(result)
        source.allowed = False

    def no_hub(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("A newly held export must not initialize a Hub client")

    monkeypatch.setattr(export, "_verify_public_artifact", close_after_validation)
    monkeypatch.setattr(export, "HfApi", no_hub)
    try:
        with pytest.raises(export.ExportPrivacyError, match="publication"):
            export.publish_export(source, result, fixtures.EXPORT_DATE, "fixture", "fake/data")
    finally:
        source.client.close()


@pytest.mark.parametrize("closure", ["hub", "cells", "retry"])
def test_publication_rechecks_each_post_hub_write_and_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, closure: str
) -> None:
    result = fixtures.build(fixtures.three_contributors_in_one_cell(), tmp_path)
    calls: list[str] = []

    class Source(SyntheticPublicationSource):
        def refresh_h3_cells(self, cells: Any) -> None:
            calls.append("cells")
            self.allowed = False
            if closure == "retry":
                request = httpx.Request("POST", "https://supabase.test/cells")
                raise httpx.HTTPStatusError(
                    "retry", request=request, response=httpx.Response(500, request=request)
                )

        def record_release(
            self, version: str, rows: int, photos: int, hf_revision: str | None
        ) -> None:
            calls.append("release")

    source = Source("https://supabase.test", "fixture")

    class Hub:
        def upload_folder(self, **kwargs: Any) -> None:
            calls.append("hub")
            if closure == "hub":
                source.allowed = False

    monkeypatch.setattr("pipeline.export.time.sleep", lambda _: None)
    try:
        with pytest.raises(export.ExportPrivacyError, match="publication"):
            export.publish_export(
                source,
                result,
                fixtures.EXPORT_DATE,
                "fixture",
                "fake/data",
                Hub(),  # type: ignore[arg-type]
            )
    finally:
        source.client.close()
    assert calls == (["hub"] if closure == "hub" else ["hub", "cells"])


@pytest.mark.parametrize("status", [401, 404, 500])
def test_capability_unavailable_http_status_refuses_before_candidate_access(status: int) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert request.url.path == CAPABILITY_PATH
        return httpx.Response(status, json={"code": "unavailable"})

    source = export.SupabaseExportSource("https://supabase.test", "fixture")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(export.ExportPrivacyError, match="publication"):
            source.submissions()
    finally:
        source.client.close()
    assert calls == [CAPABILITY_PATH]


def test_capability_timeout_refuses_without_cached_approval() -> None:
    source, _ = source_with_capability(ALLOW)
    source.assert_publication_allowed()
    source.client.close()

    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("unavailable", request=request)

    source.client = httpx.Client(transport=httpx.MockTransport(unavailable))
    try:
        with pytest.raises(export.ExportPrivacyError, match="publication"):
            source.submissions()
    finally:
        source.client.close()


def test_cached_process_evidence_still_cannot_publish_pilot_rows(tmp_path: Path) -> None:
    rows = fixtures.three_contributors_in_one_cell()
    built = fixtures.build(rows, tmp_path)
    result = replace(
        built, source_submissions=(replace(rows[0], collection_scope="private_pilot"),)
    )
    source = SyntheticPublicationSource("https://supabase.test", "fixture")
    try:
        with pytest.raises(export.ExportPrivacyError, match="collection scope"):
            export.publish_export(source, result, fixtures.EXPORT_DATE, "fixture", "fake/data")
    finally:
        source.client.close()


def test_private_collection_classification_is_never_a_public_field() -> None:
    with pytest.raises(export.ExportPrivacyError, match="forbidden private fields"):
        export.assert_public_record({"collection_scope": "legacy"})


def test_cli_without_push_still_holds_before_reads_and_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, seen = source_with_capability(HELD)
    monkeypatch.setenv("SUPABASE_URL", "https://supabase.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "fixture")
    monkeypatch.setattr(export, "SupabaseExportSource", lambda *_: source)
    monkeypatch.setattr(sys, "argv", ["export", "--output", str(tmp_path / "absent")])
    try:
        with pytest.raises(export.ExportPrivacyError, match="publication"):
            export.main()
    finally:
        source.client.close()
    assert seen == [CAPABILITY_PATH]
    assert not (tmp_path / "absent").exists()


def test_synthetic_allowed_wire_contract_preserves_explicit_legacy_row_provenance() -> None:
    tables = fixtures.source_tables("Anonymous soil contributor", [], [])
    selected: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == CAPABILITY_PATH:
            return httpx.Response(200, json=ALLOW)
        name = request.url.path.rsplit("/", 1)[-1]
        if name == "submissions":
            selected.append(request.url.params["select"])
        return httpx.Response(200, json=tables[name])

    source = export.SupabaseExportSource("https://supabase.test", "fixture")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        [row] = source.submissions()
    finally:
        source.client.close()
    assert selected and "collection_scope" in selected[0].split(",")
    assert row.collection_scope == "legacy"
    assert row.provenance_tier == 1
    assert row.grant is not None and not row.grant.withdrawn


def test_source_page_retry_cannot_keep_using_a_previous_publication_approval() -> None:
    pages: list[str] = []
    allowed = True

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal allowed
        if request.url.path == CAPABILITY_PATH:
            return httpx.Response(200, json=ALLOW if allowed else HELD)
        pages.append(request.headers["Range"])
        assert len(pages) == 1
        allowed = False
        return httpx.Response(200, headers={"Content-Range": "0-0/2"}, json=[{"id": "a"}])

    source = export.SupabaseExportSource("https://supabase.test", "fixture")
    source.client.close()
    source.client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(export.ExportPrivacyError, match="publication"):
            source._rows("submissions?select=id", page_size=1)
    finally:
        source.client.close()
    assert pages == ["0-0"]


def test_omitted_pure_source_classification_refuses_before_policy_or_artifacts(
    tmp_path: Path,
) -> None:
    original = fixtures.submission()
    unclassified = export.ExportSubmission(
        **{key: value for key, value in original.__dict__.items() if key != "collection_scope"}
    )

    class UnreadPrivacy(fixtures.SyntheticPrivacy):
        def policy(self) -> Any:
            raise AssertionError("Omitted source classification must refuse before policy reads")

    target = tmp_path / "public"
    with pytest.raises(export.ExportPrivacyError, match="collection scope"):
        export.build_export(
            [unclassified],
            target,
            fixtures.EXPORT_DATE,
            lambda _: pytest.fail("Unclassified photos must not be read"),
            photo_privacy=UnreadPrivacy(),
        )
    assert not target.exists()
