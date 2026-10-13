"""No image publication from cached flags, altered bytes or unsupported private authority."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
import test_export as fixtures
from PIL import Image

from pipeline import export
from pipeline.export import SupabaseExportSource, build_export, publish_export
from pipeline.photo_export_privacy import PhotoExportBinding, PhotoPolicy, RpcPhotoPrivacy
from pipeline.qa import sanitize_jpeg


def forbidden_loader(path: str) -> bytes:
    raise AssertionError("Closed/unsupported photos must not be downloaded")


def test_direct_legacy_export_defaults_to_data_only(tmp_path: Path) -> None:
    result = build_export(
        fixtures.three_contributors_in_one_cell(), tmp_path, fixtures.EXPORT_DATE, forbidden_loader
    )
    assert result.rows == 3 and result.photos == 0
    assert all(row["photos"] == [] for row in fixtures.load_rows(result))
    assert not (result.target / "photos").exists()


def test_closed_policy_does_not_read_any_image(tmp_path: Path) -> None:
    class Closed(fixtures.SyntheticPrivacy):
        def policy(self) -> PhotoPolicy | None:
            return None

    result = build_export(
        fixtures.three_contributors_in_one_cell(),
        tmp_path,
        fixtures.EXPORT_DATE,
        forbidden_loader,
        photo_privacy=Closed(),
    )
    assert result.rows == 3 and result.photos == 0


def test_old_rpc_schema_preserves_eligible_structured_rows(tmp_path: Path) -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        return httpx.Response(404, json={"code": "PGRST202"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = build_export(
            fixtures.three_contributors_in_one_cell(),
            tmp_path,
            fixtures.EXPORT_DATE,
            forbidden_loader,
            photo_privacy=RpcPhotoPrivacy("https://supabase.test", client),
        )
    assert result.rows == 3 and result.photos == 0
    assert requests and set(requests) == {"/rest/v1/rpc/photo_privacy_capabilities"}


def test_pending_one_photo_holds_only_that_photo(tmp_path: Path) -> None:
    rows = fixtures.three_contributors_in_one_cell()
    pending = rows[0].photos[0].id
    loaded: list[str] = []

    class Pending(fixtures.SyntheticPrivacy):
        def binding(self, photo_id: str) -> PhotoExportBinding | None:
            return None if photo_id == pending else super().binding(photo_id)

    def loader(path: str) -> bytes:
        loaded.append(path)
        return fixtures.clean_photo()

    result = build_export(rows, tmp_path, fixtures.EXPORT_DATE, loader, photo_privacy=Pending())
    assert result.rows == 3 and result.photos == 5
    assert rows[0].photos[0].storage_path not in loaded


def textured_sanitized() -> bytes:
    pixels = bytes(
        component
        for index in range(96 * 80)
        for component in ((index * 37) % 256, (index * 19) % 256, (index * 71) % 256)
    )
    image = Image.frombytes("RGB", (96, 80), pixels)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=83)
    return sanitize_jpeg(output.getvalue())[0]


class TexturedPrivacy(fixtures.SyntheticPrivacy):
    def binding(self, photo_id: str) -> PhotoExportBinding | None:
        binding = super().binding(photo_id)
        assert binding is not None
        return replace(binding, sanitized_sha256=hashlib.sha256(textured_sanitized()).hexdigest())


def test_already_clean_bytes_are_not_encoded_again(tmp_path: Path) -> None:
    clean = textured_sanitized()
    assert hashlib.sha256(sanitize_jpeg(clean)[0]).digest() != hashlib.sha256(clean).digest()
    result = build_export(
        fixtures.three_contributors_in_one_cell(),
        tmp_path,
        fixtures.EXPORT_DATE,
        lambda _: clean,
        photo_privacy=TexturedPrivacy(),
    )
    assert result.photos == 6
    assert all(path.read_bytes() == clean for path in (result.target / "photos").rglob("*.jpg"))


def test_second_encoding_cannot_inherit_input_clearance(tmp_path: Path) -> None:
    encoded = sanitize_jpeg(textured_sanitized())[0]
    result = build_export(
        fixtures.three_contributors_in_one_cell(),
        tmp_path,
        fixtures.EXPORT_DATE,
        lambda _: encoded,
        photo_privacy=TexturedPrivacy(),
    )
    assert result.rows == 3 and result.photos == 0
    assert not (result.target / "photos").exists()


def test_fresh_authorization_removes_photo_and_all_public_references(tmp_path: Path) -> None:
    rows = fixtures.three_contributors_in_one_cell()
    denied = rows[0].photos[0].id

    class LateDenied(fixtures.SyntheticPrivacy):
        def authorize(self, bindings: list[PhotoExportBinding]) -> set[str]:
            return {binding.photo_id for binding in bindings if binding.photo_id != denied}

    result = build_export(
        rows,
        tmp_path,
        fixtures.EXPORT_DATE,
        lambda _: fixtures.clean_photo(),
        photo_privacy=LateDenied(),
    )
    assert result.rows == 3 and result.photos == 5
    assert not (result.target / "photos" / rows[0].id / "A.jpg").exists()
    assert len(fixtures.load_rows(result)[0]["photos"]) == 1
    assert not any("screening" in path.name for path in result.target.rglob("*"))


def test_policy_closes_during_staging_keeps_only_data(tmp_path: Path) -> None:
    class Closing(fixtures.SyntheticPrivacy):
        calls = 0

        def policy(self) -> PhotoPolicy | None:
            self.calls += 1
            return self.policy_value if self.calls == 1 else None

    result = build_export(
        fixtures.three_contributors_in_one_cell(),
        tmp_path,
        fixtures.EXPORT_DATE,
        lambda _: fixtures.clean_photo(),
        photo_privacy=Closing(),
    )
    assert result.rows == 3 and result.photos == 0
    assert not any((result.target / "photos").rglob("*.jpg"))
    assert all(not row["photos"] for row in fixtures.load_rows(result))


def test_lost_authorization_response_withholds_every_photo(tmp_path: Path) -> None:
    class Lost(fixtures.SyntheticPrivacy):
        def authorize(self, bindings: list[PhotoExportBinding]) -> set[str]:
            raise httpx.ReadTimeout("synthetic transport failure")

    result = build_export(
        fixtures.three_contributors_in_one_cell(),
        tmp_path,
        fixtures.EXPORT_DATE,
        lambda _: fixtures.clean_photo(),
        photo_privacy=Lost(),
    )
    assert result.rows == 3 and result.photos == 0


def capabilities() -> dict[str, Any]:
    policy = fixtures.SyntheticPrivacy.policy_value
    return {
        "version": "gsip-photo-privacy-v1",
        "publication_open": True,
        "policy_id": policy.policy_id,
        "policy_revision": policy.policy_revision,
        "screening_version": policy.screening_version,
        "calibration_version": policy.calibration_version,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"version": "unknown"},
        {"publication_open": 1},
        {"publication_open": "true"},
        {"policy_id": None},
        {"policy_revision": True},
        {"policy_revision": -1},
        {"screening_version": "bad\nversion"},
        {"calibration_version": None},
        {"extra": True},
    ],
)
def test_malformed_capability_never_opens_publication(change: dict[str, Any]) -> None:
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={**capabilities(), **change})
        )
    ) as client:
        assert RpcPhotoPrivacy("https://supabase.test", client).policy() is None


@pytest.mark.parametrize("status", ["pending", "processing", "review", "withheld", "error"])
def test_only_current_clear_receipts_can_form_export_bindings(status: str) -> None:
    photo_id = fixtures.three_contributors_in_one_cell()[0].photos[0].id
    body = {
        key: value
        for key, value in capabilities().items()
        if key not in {"version", "publication_open"}
    }
    body.update(
        photo_id=photo_id,
        content_revision=1,
        sanitized_sha256=hashlib.sha256(fixtures.clean_photo()).hexdigest(),
        status=status,
    )
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    ) as client:
        assert RpcPhotoPrivacy("https://supabase.test", client).binding(photo_id) is None


@pytest.mark.parametrize("kind", ["reordered", "missing", "extra", "number", "wrong-policy"])
def test_unsupported_or_reordered_authorization_is_not_trusted(kind: str) -> None:
    photos = fixtures.three_contributors_in_one_cell()[0].photos
    authority = fixtures.SyntheticPrivacy()
    bindings = [authority.binding(photo.id) for photo in photos]
    assert all(binding is not None for binding in bindings)
    valid = [binding for binding in bindings if binding is not None]
    decisions: list[dict[str, Any]] = [
        {"photo_id": item.photo_id, "authorized": True} for item in valid
    ]
    if kind == "reordered":
        decisions.reverse()
    elif kind == "missing":
        decisions.pop()
    elif kind == "extra":
        decisions[0]["reason"] = "private"
    elif kind == "number":
        decisions[0]["authorized"] = 1
    body = {**capabilities(), "authorizations": decisions}
    if kind == "wrong-policy":
        body["policy_revision"] += 1
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    ) as client:
        assert RpcPhotoPrivacy("https://supabase.test", client).authorize(valid) == set()


def test_stale_content_binding_does_not_download(tmp_path: Path) -> None:
    class Stale(fixtures.SyntheticPrivacy):
        def binding(self, photo_id: str) -> PhotoExportBinding | None:
            value = super().binding(photo_id)
            assert value is not None
            return replace(value, policy=replace(self.policy_value, policy_revision=2))

    result = build_export(
        fixtures.three_contributors_in_one_cell(),
        tmp_path,
        fixtures.EXPORT_DATE,
        forbidden_loader,
        photo_privacy=Stale(),
    )
    assert result.rows == 3 and result.photos == 0


def test_actual_staged_byte_mutation_is_removed_before_promotion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = fixtures.three_contributors_in_one_cell()
    original = export._write_public_files
    writes = 0

    def mutated(records: list[dict[str, Any]], root: Path, date: Any, withheld: int) -> None:
        nonlocal writes
        original(records, root, date, withheld)
        writes += 1
        if writes == 1:
            (root / "photos" / rows[0].id / "A.jpg").write_bytes(textured_sanitized())

    monkeypatch.setattr(export, "_write_public_files", mutated)
    result = fixtures.build(rows, tmp_path)
    assert result.rows == 3 and result.photos == 5
    assert not (result.target / "photos" / rows[0].id / "A.jpg").exists()
    assert writes == 2


def test_closed_gate_revalidates_same_date_photo_artifact_before_upload(tmp_path: Path) -> None:
    result = fixtures.build(fixtures.three_contributors_in_one_cell(), tmp_path)
    assert result.photos == 6

    class Closed(fixtures.SyntheticPrivacy):
        def policy(self) -> PhotoPolicy | None:
            return None

    class Source(SupabaseExportSource):
        @property
        def photo_privacy(self) -> Closed:
            return Closed()

        def withdrawn_grant_ids(self) -> set[str]:
            return set()

        def refresh_h3_cells(self, cells: Any) -> None:
            pass

        def record_release(
            self, version: str, rows: int, photos: int, hf_revision: str | None
        ) -> None:
            assert rows == 3 and photos == 0

    class Hub:
        def upload_folder(self, **kwargs: Any) -> None:
            assert not (result.target / "photos").exists()
            assert all(not row["photos"] for row in fixtures.load_rows(result))

    source = Source("https://supabase.test", "fixture")
    try:
        published = publish_export(
            source,
            result,
            fixtures.EXPORT_DATE,
            "fixture",
            "synthetic/example",
            Hub(),  # type: ignore[arg-type]
        )
    finally:
        source.client.close()
    assert published.photos == 0 and published.rows == 3


def test_last_minute_withdrawal_is_rebuilt_and_k_anonymity_recomputed(tmp_path: Path) -> None:
    rows = fixtures.three_contributors_in_one_cell()
    result = fixtures.build(rows, tmp_path)
    grant = rows[0].grant
    assert grant is not None
    withdrawn_id = grant.id

    class Source(SupabaseExportSource):
        @property
        def photo_privacy(self) -> fixtures.SyntheticPrivacy:
            return fixtures.SyntheticPrivacy()

        def withdrawn_grant_ids(self) -> set[str]:
            return {withdrawn_id}

        def photo(self, path: str) -> bytes:
            return fixtures.clean_photo()

        def refresh_h3_cells(self, cells: Any) -> None:
            assert not cells

        def record_release(
            self, version: str, rows: int, photos: int, hf_revision: str | None
        ) -> None:
            assert rows == 0 and photos == 0

    class Hub:
        def upload_folder(self, **kwargs: Any) -> None:
            root = Path(kwargs["folder_path"])
            assert (root / "data/EMPTY.md").exists()
            assert not (root / "photos").exists()

    source = Source("https://supabase.test", "fixture")
    try:
        published = publish_export(
            source,
            result,
            fixtures.EXPORT_DATE,
            "fixture",
            "synthetic/example",
            Hub(),  # type: ignore[arg-type]
        )
    finally:
        source.client.close()
    assert published.rows == 0 and published.photos == 0


@pytest.mark.parametrize("kind", ["duplicate", "nonfinite"])
def test_ambiguous_raw_rpc_json_cannot_open_publication(kind: str) -> None:
    raw = json.dumps(capabilities())
    if kind == "duplicate":
        raw = raw.replace(
            '"publication_open": true', '"publication_open": false, "publication_open": true'
        )
    else:
        raw = raw.replace('"policy_revision": 1', '"policy_revision": NaN')
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))
    ) as client:
        assert RpcPhotoPrivacy("https://supabase.test", client).policy() is None


@pytest.mark.parametrize("operation", ["policy", "binding", "authorize"])
def test_excessively_nested_authority_json_withholds_only_photos(operation: str) -> None:
    raw = "[" * 10_000 + "0" + "]" * 10_000
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))
    ) as client:
        authority = RpcPhotoPrivacy("https://supabase.test", client)
        photo_id = fixtures.three_contributors_in_one_cell()[0].photos[0].id
        if operation == "policy":
            assert authority.policy() is None
        elif operation == "binding":
            assert authority.binding(photo_id) is None
        else:
            binding = fixtures.SyntheticPrivacy().binding(photo_id)
            assert binding is not None
            assert authority.authorize([binding]) == set()


def test_deeply_nested_privacy_reply_does_not_stop_structured_export(tmp_path: Path) -> None:
    raw = "[" * 10_000 + "0" + "]" * 10_000
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=raw))
    ) as client:
        result = build_export(
            fixtures.three_contributors_in_one_cell(),
            tmp_path,
            fixtures.EXPORT_DATE,
            forbidden_loader,
            photo_privacy=RpcPhotoPrivacy("https://supabase.test", client),
        )
    assert result.rows == 3 and result.photos == 0


def test_operator_cli_errors_do_not_echo_private_arguments() -> None:
    result = subprocess.run(  # noqa: S603 - repository CLI and synthetic argument only
        [sys.executable, "-m", "pipeline.export", "--unknown-private-marker"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "unknown-private-marker" not in result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert "Export failed" in result.stderr


def test_empty_cached_artifact_cannot_upload_orphan_media(tmp_path: Path) -> None:
    result = build_export([], tmp_path, fixtures.EXPORT_DATE, forbidden_loader)
    orphan = result.target / "photos/orphan.jpg"
    orphan.parent.mkdir()
    orphan.write_bytes(fixtures.clean_photo())
    checks = 0

    class Closed(fixtures.SyntheticPrivacy):
        def policy(self) -> PhotoPolicy | None:
            nonlocal checks
            checks += 1
            return None

    class Source(SupabaseExportSource):
        @property
        def photo_privacy(self) -> Closed:
            return Closed()

        def withdrawn_grant_ids(self) -> set[str]:
            return set()

        def refresh_h3_cells(self, cells: Any) -> None:
            assert not cells

        def record_release(
            self, version: str, rows: int, photos: int, hf_revision: str | None
        ) -> None:
            assert rows == 0 and photos == 0

    class Hub:
        def upload_folder(self, **kwargs: Any) -> None:
            assert not (Path(kwargs["folder_path"]) / "photos").exists()
            assert checks > 0

    source = Source("https://supabase.test", "fixture")
    try:
        published = publish_export(
            source,
            result,
            fixtures.EXPORT_DATE,
            "fixture",
            "synthetic/example",
            Hub(),  # type: ignore[arg-type]
        )
    finally:
        source.client.close()
    assert published.rows == 0 and published.photos == 0


def test_withdrawal_during_final_photo_rpc_rebuilds_structured_rows(tmp_path: Path) -> None:
    rows = fixtures.three_contributors_in_one_cell()
    result = fixtures.build(rows, tmp_path)
    grant = rows[0].grant
    assert grant is not None
    grant_id = grant.id
    withdrawn = False

    class Withdrawing(fixtures.SyntheticPrivacy):
        def authorize(self, bindings: list[PhotoExportBinding]) -> set[str]:
            nonlocal withdrawn
            withdrawn = True
            return super().authorize(bindings)

    authority = Withdrawing()

    class Source(SupabaseExportSource):
        @property
        def photo_privacy(self) -> Withdrawing:
            return authority

        def withdrawn_grant_ids(self) -> set[str]:
            return {grant_id} if withdrawn else set()

        def photo(self, path: str) -> bytes:
            return fixtures.clean_photo()

        def refresh_h3_cells(self, cells: Any) -> None:
            assert not cells

        def record_release(
            self, version: str, rows: int, photos: int, hf_revision: str | None
        ) -> None:
            assert rows == 0 and photos == 0

    class Hub:
        def upload_folder(self, **kwargs: Any) -> None:
            root = Path(kwargs["folder_path"])
            assert (root / "data/EMPTY.md").exists()
            assert not (root / "photos").exists()
            assert not (root / "data/train.parquet").exists()

    source = Source("https://supabase.test", "fixture")
    try:
        published = publish_export(
            source,
            result,
            fixtures.EXPORT_DATE,
            "fixture",
            "synthetic/example",
            Hub(),  # type: ignore[arg-type]
        )
    finally:
        source.client.close()
    assert withdrawn and published.rows == 0 and published.photos == 0


def test_bytes_changed_during_authorization_cannot_use_prior_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged: list[Path] = []
    original = export._write_public_files

    def remember(records: list[dict[str, Any]], root: Path, date: Any, withheld: int) -> None:
        staged[:] = [root]
        original(records, root, date, withheld)

    class Mutating(fixtures.SyntheticPrivacy):
        def authorize(self, bindings: list[PhotoExportBinding]) -> set[str]:
            for path in (staged[0] / "photos").rglob("*.jpg"):
                path.write_bytes(textured_sanitized())
            return super().authorize(bindings)

    monkeypatch.setattr(export, "_write_public_files", remember)
    result = build_export(
        fixtures.three_contributors_in_one_cell(),
        tmp_path,
        fixtures.EXPORT_DATE,
        lambda _: fixtures.clean_photo(),
        photo_privacy=Mutating(),
    )
    assert result.rows == 3 and result.photos == 0
    assert not (result.target / "photos").exists()
    assert all(not row["photos"] for row in fixtures.load_rows(result))


def test_unapproved_staging_stays_private_outside_export_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    observed: list[Path] = []
    original = export._write_public_files

    def private(records: list[dict[str, Any]], root: Path, date: Any, withheld: int) -> None:
        assert not root.resolve().is_relative_to(tmp_path.resolve())
        assert root.stat().st_mode & 0o777 == 0o700
        observed.append(root)
        original(records, root, date, withheld)

    monkeypatch.setattr(export, "_write_public_files", private)
    result = fixtures.build(fixtures.three_contributors_in_one_cell(), tmp_path)
    assert result.rows == 3 and result.photos == 6
    assert observed and all(not root.exists() for root in observed)


def closed_source() -> SupabaseExportSource:
    class Closed(fixtures.SyntheticPrivacy):
        def policy(self) -> PhotoPolicy | None:
            return None

    class Source(SupabaseExportSource):
        @property
        def photo_privacy(self) -> Closed:
            return Closed()

        def withdrawn_grant_ids(self) -> set[str]:
            return set()

        def refresh_h3_cells(self, cells: Any) -> None:
            pass

        def record_release(
            self, version: str, rows: int, photos: int, hf_revision: str | None
        ) -> None:
            pass

    return Source("https://supabase.test", "fixture")


def refuse_unsafe_artifact(result: export.ExportResult) -> None:
    uploads: list[bool] = []

    class Hub:
        def upload_folder(self, **kwargs: Any) -> None:
            uploads.append(True)

    source = closed_source()
    try:
        with pytest.raises(export.ExportPrivacyError):
            publish_export(
                source,
                result,
                fixtures.EXPORT_DATE,
                "fixture",
                "synthetic/example",
                Hub(),  # type: ignore[arg-type]
            )
    finally:
        source.client.close()
    assert not uploads


@pytest.mark.parametrize("relative", ["thumbnails/orphan.jpg", "private.json", "data/extra.json"])
def test_unknown_cached_files_cannot_enter_closed_release(tmp_path: Path, relative: str) -> None:
    result = build_export([], tmp_path / "release", fixtures.EXPORT_DATE, forbidden_loader)
    unknown = result.target / relative
    unknown.parent.mkdir(parents=True, exist_ok=True)
    unknown.write_bytes(fixtures.clean_photo())
    refuse_unsafe_artifact(result)
    assert unknown.read_bytes() == fixtures.clean_photo()


@pytest.mark.parametrize("relative", ["photos", "data", "README.md", "manifest.json", "."])
def test_cached_symlink_is_refused_without_touching_target(tmp_path: Path, relative: str) -> None:
    result = build_export([], tmp_path / "release", fixtures.EXPORT_DATE, forbidden_loader)
    bystander = tmp_path / "bystander"
    bystander.mkdir()
    content = bystander / "bystander.jpg"
    content.write_bytes(fixtures.clean_photo())
    link = result.target / relative
    directory = relative in {"photos", "data", "."}
    if relative == ".":
        result.target.rename(tmp_path / "original-release")
        link = result.target
    elif link.is_dir():
        shutil.rmtree(link)
    elif link.exists():
        link.unlink()
    link.symlink_to(bystander if directory else content, target_is_directory=directory)
    refuse_unsafe_artifact(result)
    assert content.read_bytes() == fixtures.clean_photo()
    assert sorted(path.name for path in bystander.iterdir()) == ["bystander.jpg"]


def test_cached_hard_link_is_refused_without_rewriting_bystander(tmp_path: Path) -> None:
    result = build_export([], tmp_path / "release", fixtures.EXPORT_DATE, forbidden_loader)
    bystander = tmp_path / "bystander.txt"
    bystander.write_text("synthetic-bystander", encoding="utf-8")
    readme = result.target / "README.md"
    readme.unlink()
    os.link(bystander, readme)
    refuse_unsafe_artifact(result)
    assert bystander.read_text(encoding="utf-8") == "synthetic-bystander"


def test_rpc_cannot_replace_photo_root_with_bystander_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    staged: list[Path] = []
    original = export._write_public_files
    bystander = tmp_path / "bystander"
    bystander.mkdir()
    photo = bystander / "bystander.jpg"
    photo.write_bytes(fixtures.clean_photo())

    def remember(records: list[dict[str, Any]], root: Path, date: Any, withheld: int) -> None:
        staged[:] = [root]
        original(records, root, date, withheld)

    class Replacing(fixtures.SyntheticPrivacy):
        def authorize(self, bindings: list[PhotoExportBinding]) -> set[str]:
            root = staged[0] / "photos"
            shutil.rmtree(root)
            root.symlink_to(bystander, target_is_directory=True)
            return set()

    monkeypatch.setattr(export, "_write_public_files", remember)
    with pytest.raises(export.ExportPrivacyError):
        build_export(
            fixtures.three_contributors_in_one_cell(),
            tmp_path / "release",
            fixtures.EXPORT_DATE,
            lambda _: fixtures.clean_photo(),
            photo_privacy=Replacing(),
        )
    assert photo.read_bytes() == fixtures.clean_photo()
    assert sorted(path.name for path in bystander.iterdir()) == ["bystander.jpg"]


@pytest.mark.parametrize(
    "key",
    [
        "sanitized_sha256",
        "content_revision",
        "policy_id",
        "policy_revision",
        "screening_version",
        "calibration_version",
        "detector_manifest_sha256",
        "calibration_manifest_sha256",
        "operator_id",
        "operator_token",
        "token_hash",
        "privacy_status",
        "photo_privacy",
        "photo_bindings",
        "source_submissions",
        "card_exclusion",
        "card_exception_used",
        "face",
        "scene_text",
        "lease_id",
        "lease_expires_at",
        "review_id",
        "privacy_reviews",
    ],
)
def test_private_privacy_bindings_fail_public_nested_assertions(key: str) -> None:
    with pytest.raises(export.ExportPrivacyError):
        export.assert_public_record({"photos": [{"qa": {key: "synthetic"}}]})
