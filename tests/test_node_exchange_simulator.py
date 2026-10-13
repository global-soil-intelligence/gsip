"""Generated fictional fixtures only; every test forbids network construction."""

from __future__ import annotations

import copy
import json
import multiprocessing
import socket
import threading
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

import pipeline.node_exchange_simulator as module
import pipeline.node_exchange_store as store_module
from pipeline.node_exchange import NodeExchangeDeclaration, prepare_node_exchange_event
from pipeline.node_exchange_simulator import (
    BACKOFF_SECONDS,
    CLAIM_RECOVERY_SECONDS,
    MAX_BATCH,
    FakeAuthority,
    FakeClock,
    FakeScope,
    FakeTransport,
    LocalReceipt,
    SyntheticExchangeError,
    SyntheticExchangeSimulator,
    SyntheticOrigin,
)
from pipeline.node_exchange_store import BlobRef, PrivateExchangeSession, StoreSnapshot


def uid(value: int) -> str:
    return str(UUID(int=value))


HUMAN, GRANT, SAMPLE, MEASUREMENT = map(uid, (11, 12, 13, 14))
SCOPE, OTHER_SCOPE, OTHER_HUMAN = map(uid, (21, 22, 31))
SOURCE, RECIPIENT = map(uid, (41, 42))
MESSAGE = "synthetic exchange unavailable"


@pytest.fixture(autouse=True)
def no_network() -> Iterator[None]:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("synthetic simulator permits no network")

    with pytest.MonkeyPatch.context() as guard:
        guard.setattr(socket, "socket", forbidden)
        guard.setattr(socket, "create_connection", forbidden)
        yield


def fixture(*, scopes: int = 2, extra_human: bool = False) -> FakeAuthority:
    peers = tuple(FakeScope(SOURCE, RECIPIENT, uid(21 + i), HUMAN) for i in range(scopes))
    origins: tuple[SyntheticOrigin, ...] = (
        SyntheticOrigin(HUMAN, GRANT, SAMPLE, MEASUREMENT),
        SyntheticOrigin(HUMAN, GRANT, SAMPLE, uid(15), kind="instrument_reflectance"),
        SyntheticOrigin(HUMAN, GRANT, uid(16), uid(17)),
    )
    if extra_human:
        peers += (FakeScope(SOURCE, RECIPIENT, uid(32), OTHER_HUMAN),)
        origins += (SyntheticOrigin(OTHER_HUMAN, uid(33), SAMPLE, MEASUREMENT),)
    return FakeAuthority(uid(1), peers, origins)


@pytest.fixture
def sim(tmp_path: Path) -> SyntheticExchangeSimulator:
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    result = SyntheticExchangeSimulator.create(
        allowed / "ledger", allowed, fixture(), FakeClock(datetime(2026, 10, 13, tzinfo=UTC))
    )
    result.enroll_scope(SCOPE)
    result.enroll_scope(OTHER_SCOPE)
    return result


def raw_for(sim: SyntheticExchangeSimulator, event: str, role: str = "source") -> bytes:
    with sim._store.locked() as session:
        snap = session.snapshot()
        return session.read_blob(snap.data["events"][event][role + "_blob"])


def facts(sim: SyntheticExchangeSimulator) -> dict[str, Any]:
    with sim._store.locked() as session:
        return session.snapshot().data


def reopen(
    sim: SyntheticExchangeSimulator, authority: FakeAuthority | None = None
) -> SyntheticExchangeSimulator:
    root = sim._store.root
    return SyntheticExchangeSimulator.open(
        root, root.parent, authority or sim._authority, sim._clock
    )


def stage(
    sim: SyntheticExchangeSimulator,
    scope: str = SCOPE,
    measurement: str = MEASUREMENT,
    *,
    draft: bool = False,
) -> LocalReceipt:
    return sim.stage_declaration(scope, SAMPLE, measurement, draft=draft)


def fixed(error: pytest.ExceptionInfo[SyntheticExchangeError]) -> None:
    assert str(error.value) == MESSAGE
    assert error.value.__context__ is None and error.value.__cause__ is None


def changed(raw: bytes, **fields: Any) -> bytes:
    value = json.loads(raw)
    value.update(fields)
    return json.dumps(value, separators=(",", ":"), allow_nan=False).encode()


def test_generated_flow_restart_owned_bytes_and_no_science_metadata(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    original = raw_for(sim, event.event_id)
    data = facts(sim)
    assert data["events"][event.event_id]["source_day"] == "2026-10-13"
    assert data["recipient_heads"] == {}
    assert all(
        key not in json.dumps(data)
        for key in ("mean_rgb", "source_sha256", "condition", "reflectance", "wavelength_nm")
    )
    opened = reopen(sim)
    assert raw_for(opened, event.event_id) == original
    assert opened.process_batch(FakeTransport()) == {"claimed": 1, "completed": 1}
    assert opened.payload_status(event.event_id) == "available_for_synthetic_simulation"
    assert opened.counts()["retained_bytes"] == 2 * len(original)
    assert opened.counts()["queued_declarations"] == 0
    assert opened.receive_event(original).status == "already_stored"
    assert opened.counts()["retained_slots"] == 2
    assert opened.counts()["field_eligible"] == opened.counts()["verified_physical_pairs"] == 0
    assert (
        repr(event)
        == "<pipeline.node_exchange_simulator.LocalReceipt object at " + hex(id(event)) + ">"
    )


def test_owned_prepare_rejects_supplied_metadata(sim: SyntheticExchangeSimulator) -> None:
    event = stage(sim)
    raw = raw_for(sim, event.event_id)
    prepared = prepare_node_exchange_event(raw)
    with pytest.raises(SyntheticExchangeError) as error:
        sim.receive_event(prepared)  # type: ignore[arg-type]
    fixed(error)
    assert facts(sim)["recipient_slots"] == {}


@pytest.mark.parametrize(
    "payload",
    [
        b"secret input",
        b'{"kind":"declare","kind":"retire"}',
        b"\xef\xbb\xbf{}",
        b"[[]]",
        b" " * 2_000_001,
        b"\xff",
    ],
)
def test_strict_raw_boundary_generic(sim: SyntheticExchangeSimulator, payload: bytes) -> None:
    before = facts(sim)
    with pytest.raises(SyntheticExchangeError) as error:
        sim.receive_event(payload)
    fixed(error)
    assert facts(sim) == before


@pytest.mark.parametrize(
    "status", [{"connected": False}, {"known": False}, {"expired": True}, {"revoke": True}]
)
def test_current_rights_hold_without_spending_attempts_or_quota(
    sim: SyntheticExchangeSimulator, status: dict[str, bool]
) -> None:
    event = stage(sim)
    raw = raw_for(sim, event.event_id)
    sim.set_scope_status(SCOPE, **status)
    before = facts(sim)
    assert sim.receive_event(raw).status == "held"
    assert sim.process_batch(FakeTransport()) == {"claimed": 0, "completed": 0}
    assert facts(sim)["outbox"][event.event_id]["attempts"] == 0
    assert facts(sim)["quotas"] == before["quotas"]
    with pytest.raises(SyntheticExchangeError) as error:
        stage(sim)
    fixed(error)


def test_unknown_scope_never_creates_authority_or_fence(sim: SyntheticExchangeSimulator) -> None:
    event = stage(sim)
    before = facts(sim)
    with pytest.raises(SyntheticExchangeError):
        sim.receive_event(changed(raw_for(sim, event.event_id), scope_id=uid(99)))
    assert facts(sim) == before


def test_fixture_seal_and_synthetic_restriction_are_monotonic_after_restart(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    sim.process_batch(FakeTransport())
    stricter = replace(
        sim._authority,
        origins=tuple(
            replace(origin, sealed=True, synthetic_restricted=True)
            if origin.sample_id == SAMPLE
            else origin
            for origin in sim._authority.origins
        ),
    )
    opened = reopen(sim, stricter)
    assert opened.payload_status(event.event_id) == "held"
    assert facts(opened)["origins"][HUMAN + "/" + SAMPLE]["synthetic"] is True
    weaker = reopen(opened, fixture())
    assert weaker.payload_status(event.event_id) == "held"
    with pytest.raises(SyntheticExchangeError):
        stage(weaker)


def test_grant_replacement_never_revives_original_mapping(sim: SyntheticExchangeSimulator) -> None:
    event = stage(sim)
    sim.process_batch(FakeTransport())
    changed_authority = replace(
        sim._authority,
        origins=tuple(replace(origin, grant_id=uid(81)) for origin in sim._authority.origins),
    )
    opened = reopen(sim, changed_authority)
    assert opened.payload_status(event.event_id) == "held"
    with pytest.raises(SyntheticExchangeError):
        stage(opened)


def test_retirement_before_recipient_and_gap_inherits_all_measurements(
    sim: SyntheticExchangeSimulator,
) -> None:
    first = stage(sim)
    second = stage(sim, measurement=uid(15))
    first_raw, second_raw = raw_for(sim, first.event_id), raw_for(sim, second.event_id)
    assert sim.receive_event(second_raw).status == "stored"
    assert sim.payload_status(second.event_id) == "held"
    assert facts(sim)["recipient_heads"] == {}
    sim.withdraw_original(HUMAN, SAMPLE)
    assert sim.process_batch(FakeTransport())["completed"] == 1
    assert sim.receive_event(first_raw).status == "held"
    assert sim.receive_event(second_raw).status == "held"
    assert sim.counts()["retained_bytes"] == 0
    data = facts(sim)
    assert len(data["refusals"]) == 3 and data["aliases"] == {}
    assert len(data["recipient_slots"]) == 2
    assert data["recipient_heads"] == {}  # retirement did not fabricate missing slots
    assert all(
        set(value) == {"stream", "sample_handle", "measurement_handles"}
        for value in data["refusals"].values()
    )


def test_gap_waits_for_own_role_predecessor(sim: SyntheticExchangeSimulator) -> None:
    first, second = stage(sim), stage(sim)
    assert sim.receive_event(raw_for(sim, second.event_id)).status == "stored"
    assert sim.payload_status(second.event_id) == "held"
    assert sim.receive_event(raw_for(sim, first.event_id)).status == "stored"
    assert sim.payload_status(second.event_id) == "available_for_synthetic_simulation"
    assert len(facts(sim)["source_slots"]) == len(facts(sim)["recipient_slots"]) == 2


@pytest.mark.parametrize(
    "mutation", ["whitespace", "event_id", "measurement", "sample", "previous_digest"]
)
def test_slot_byte_and_scientific_conflicts_preserve_quota(
    sim: SyntheticExchangeSimulator, mutation: str
) -> None:
    event = stage(sim)
    raw = raw_for(sim, event.event_id)
    before = facts(sim)
    if mutation == "whitespace":
        incoming = b" " + raw
    else:
        value = json.loads(raw)
        if mutation == "event_id":
            value["event_id"] = uid(71)
        elif mutation in ("measurement", "sample"):
            # New source event / next slot: scientific binding, not identity conflict.
            value["event_id"], value["stream_sequence"], value["previous_event_sha256"] = (
                uid(71),
                1,
                event.sha256,
            )
            if mutation == "measurement":
                value["payload"]["measurement"]["mean_rgb"][0] = 0.9
            else:
                other = stage(sim, OTHER_SCOPE)
                value["payload"]["sample_handle"] = other.sample_handle
        else:
            value["event_id"], value["stream_sequence"], value["previous_event_sha256"] = (
                uid(71),
                1,
                "a" * 64,
            )
            sim.receive_event(raw)
        incoming = json.dumps(value, separators=(",", ":")).encode()
    if mutation == "sample":
        with pytest.raises(SyntheticExchangeError):
            sim.receive_event(incoming)
    else:
        assert sim.receive_event(incoming).status == "conflict"
    assert facts(sim)["quotas"].get("recipient/" + HUMAN + "/2026-10-13", 0) == (
        1 if mutation == "previous_digest" else 0
    )
    assert (
        facts(sim)["quotas"]["source/" + HUMAN + "/2026-10-13"]
        >= before["quotas"]["source/" + HUMAN + "/2026-10-13"]
    )


def test_exact_retry_midnight_restart_and_lost_reply(sim: SyntheticExchangeSimulator) -> None:
    event = stage(sim)
    original = raw_for(sim, event.event_id)
    assert sim.process_batch(FakeTransport(("lose_reply",))) == {"claimed": 1, "completed": 0}
    data = facts(sim)
    assert data["outbox"][event.event_id]["attempts"] == 1
    assert data["events"][event.event_id]["recipient_day"] == "2026-10-13"
    sim._clock.now += timedelta(days=1)
    opened = reopen(sim)
    assert opened.process_batch(FakeTransport()) == {"claimed": 1, "completed": 1}
    assert raw_for(opened, event.event_id) == original
    assert facts(opened)["quotas"] == {
        "source/" + HUMAN + "/2026-10-13": 1,
        "recipient/" + HUMAN + "/2026-10-13": 1,
    }
    newer = stage(opened)
    assert facts(opened)["events"][newer.event_id]["source_day"] == "2026-10-14"


def test_hundred_daily_source_and_recipient_are_separate_and_shared_across_scopes(
    sim: SyntheticExchangeSimulator,
) -> None:
    events = [stage(sim, SCOPE if index % 2 else OTHER_SCOPE) for index in range(100)]
    with pytest.raises(SyntheticExchangeError):
        stage(sim)
    for _ in range(5):
        assert sim.process_batch(FakeTransport())["completed"] == 20
    data = facts(sim)
    assert data["quotas"]["source/" + HUMAN + "/2026-10-13"] == 100
    assert data["quotas"]["recipient/" + HUMAN + "/2026-10-13"] == 100
    assert sim.receive_event(raw_for(sim, events[0].event_id)).status == "already_stored"
    sim._clock.now += timedelta(days=1)
    new = stage(sim)
    assert sim.receive_event(raw_for(sim, new.event_id)).status == "stored"
    sim.withdraw_original(HUMAN, SAMPLE)
    assert facts(sim)["quotas"]["source/" + HUMAN + "/2026-10-13"] == 100
    assert facts(sim)["quotas"]["recipient/" + HUMAN + "/2026-10-13"] == 100


def test_recipient_day_is_its_first_admission_not_source_day(
    sim: SyntheticExchangeSimulator,
) -> None:
    first = stage(sim)
    sim._clock.now += timedelta(days=1)
    assert sim.receive_event(raw_for(sim, first.event_id)).status == "stored"
    data = facts(sim)
    assert data["events"][first.event_id]["source_day"] == "2026-10-13"
    assert data["events"][first.event_id]["recipient_day"] == "2026-10-14"


def test_draft_identity_original_bytes_and_clear_on_withdrawal(
    sim: SyntheticExchangeSimulator,
) -> None:
    draft = stage(sim, draft=True)
    raw = raw_for(sim, draft.event_id)
    assert sim.process_batch(FakeTransport())["claimed"] == 0
    sim.queue_draft(draft.event_id)
    assert raw_for(sim, draft.event_id) == raw
    assert sim.process_batch(FakeTransport())["completed"] == 1
    prep = sim.create_synthetic_preparation(draft.event_id)
    sim.withdraw_original(HUMAN, SAMPLE)
    assert prep in facts(sim)["blob_owners"]  # recipient cleanup has not happened
    assert sim.payload_status(draft.event_id) == "held"
    assert sim.process_batch(FakeTransport())["completed"] == 1
    assert sim.counts()["retained_bytes"] == 0
    assert facts(sim)["bindings"] == facts(sim)["aliases"] == {}


def test_grant_withdrawal_before_any_payload_is_durable(sim: SyntheticExchangeSimulator) -> None:
    assert sim.withdraw_grant(HUMAN, GRANT) == 0
    opened = reopen(sim)
    with pytest.raises(SyntheticExchangeError):
        stage(opened)
    with pytest.raises(SyntheticExchangeError):
        opened.stage_declaration(SCOPE, uid(16), uid(17))
    assert facts(opened)["quotas"] == {}
    assert facts(opened)["retired_grants"] == {HUMAN + "/" + GRANT: True}


def test_same_owner_alias_inheritance_does_not_link_other_human(tmp_path: Path) -> None:
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    sim = SyntheticExchangeSimulator.create(
        allowed / "ledger",
        allowed,
        fixture(extra_human=True),
        FakeClock(datetime(2026, 10, 13, tzinfo=UTC)),
    )
    for scope in (SCOPE, OTHER_SCOPE, uid(32)):
        sim.enroll_scope(scope)
    first, alias = stage(sim), stage(sim, OTHER_SCOPE)
    other = stage(sim, uid(32))
    sim.process_batch(FakeTransport())
    assert sim.counts()["independent_fake_samples"] == 2
    assert sim.counts()["independent_fake_humans"] == 2
    sim.withdraw_original(HUMAN, SAMPLE)
    sim.process_batch(FakeTransport())
    assert sim.payload_status(first.event_id) == sim.payload_status(alias.event_id) == "held"
    assert sim.payload_status(other.event_id) == "available_for_synthetic_simulation"
    assert sim.counts()["independent_fake_samples"] == 1


def test_five_transients_exact_backoff_terminal_held_and_unknown_nonconsuming(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    for index in range(5):
        sim.process_batch(FakeTransport(("transient",)))
        item = facts(sim)["outbox"][event.event_id]
        assert item["attempts"] == index + 1
        if index < 4:
            assert item["ready_at"] == sim._clock.seconds() + BACKOFF_SECONDS[index]
            assert sim.process_batch(FakeTransport())["claimed"] == 0
            sim._clock.now += timedelta(seconds=BACKOFF_SECONDS[index])
    assert facts(sim)["outbox"][event.event_id]["held"] is True
    assert sim.process_batch(FakeTransport())["claimed"] == 0


def test_stopped_claim_recovers_with_fresh_nonce_and_rejects_stale_checkpoint(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    old = sim._claim(1)[0]
    assert sim.process_batch(FakeTransport())["claimed"] == 0
    sim._clock.now += timedelta(seconds=CLAIM_RECOVERY_SECONDS)
    assert reopen(sim).process_batch(FakeTransport())["claimed"] == 0
    sim._clock.now += timedelta(seconds=60)
    new = sim._claim(1)[0]
    assert new.raw == old.raw and new.nonce != old.nonce
    receipt = sim.receive_event(new.raw)
    assert sim._checkpoint(old, receipt, False) is False
    assert facts(sim)["outbox"][event.event_id]["claim"] == new.nonce
    assert sim._checkpoint(new, receipt, False) is True


def test_delayed_delivery_outside_lock_cannot_revive_withdrawn_payload(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    event = stage(sim)
    entered, release = threading.Event(), threading.Event()
    old_deliver = FakeTransport.deliver
    outcome: list[dict[str, int]] = []

    def barrier(
        self: FakeTransport, simulator: SyntheticExchangeSimulator, raw: bytes
    ) -> LocalReceipt | None:
        entered.set()
        assert release.wait(10)
        return old_deliver(self, simulator, raw)

    monkeypatch.setattr(FakeTransport, "deliver", barrier)
    worker = threading.Thread(target=lambda: outcome.append(sim.process_batch(FakeTransport())))
    worker.start()
    assert entered.wait(10)
    sim.withdraw_original(HUMAN, SAMPLE)  # would deadlock if fake delivery held root flock
    release.set()
    worker.join(10)
    assert not worker.is_alive() and outcome == [{"claimed": 1, "completed": 0}]
    assert event.event_id not in facts(sim)["outbox"]
    assert sim.payload_status(event.event_id) == "held"
    monkeypatch.setattr(FakeTransport, "deliver", old_deliver)
    assert sim.process_batch(FakeTransport())["completed"] == 1
    assert sim.counts()["retained_bytes"] == 0


@pytest.mark.parametrize("forged", ["wrong_scope", "wrong_hash", "false_ack", "no_receiver"])
def test_false_or_stale_receipts_never_finish_cleanup_or_delivery(
    sim: SyntheticExchangeSimulator, forged: str
) -> None:
    stage(sim)
    if forged != "no_receiver":
        sim.process_batch(FakeTransport())
        sim.withdraw_original(HUMAN, SAMPLE)
    claim = sim._claim(1)[0]
    prepared = prepare_node_exchange_event(claim.raw)
    if forged == "no_receiver":
        receipt = sim._receipt(prepared, "stored")
    else:
        receipt = sim._receipt(prepared, "retired", True)
        if forged == "wrong_scope":
            receipt = replace(receipt, scope_id=OTHER_SCOPE)
        elif forged == "wrong_hash":
            receipt = replace(receipt, sha256="a" * 64)
        # false_ack has exact identities but registered recipient science remains
    assert sim._checkpoint(claim, receipt, False) is False
    assert claim.event_id in facts(sim)["outbox"]
    if forged != "no_receiver":
        assert sim.counts()["pending_cleanup"] == 1


def test_unknown_artifact_blocks_honest_absence_ack(sim: SyntheticExchangeSimulator) -> None:
    stage(sim)
    sim.process_batch(FakeTransport())
    sim.withdraw_original(HUMAN, SAMPLE)
    claim = sim._claim(1)[0]
    receipt = sim.receive_event(claim.raw)
    assert receipt.payload_absent
    unsafe = sim._store.root / "unknown"
    unsafe.write_bytes(b"fictional retained payload")
    unsafe.chmod(0o600)
    with pytest.raises(SyntheticExchangeError) as error:
        sim.counts()
    fixed(error)
    with pytest.raises(SyntheticExchangeError) as error:
        sim.process_batch(FakeTransport())
    fixed(error)
    assert unsafe.read_bytes() == b"fictional retained payload"


@pytest.mark.parametrize("cap", ["MAX_REFUSALS", "MAX_CLEANUP", "MAX_SEQUENCE_SLOTS"])
def test_cleanup_saturation_activates_reserved_fence_before_later_admission(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch, cap: str
) -> None:
    event = stage(sim)
    before = facts(sim)
    original_maximum = getattr(module, cap)
    maximum = 1 if cap == "MAX_SEQUENCE_SLOTS" else 0
    monkeypatch.setattr(module, cap, maximum)
    sim.withdraw_original(HUMAN, SAMPLE)
    data = facts(sim)
    assert data["scopes"][SCOPE]["fenced"] and data["scopes"][SCOPE]["pending_erasure"]
    assert data["origins"][HUMAN + "/" + SAMPLE]["withdrawn"]
    assert len(data["refusals"]) == 0 and data["cleanup"] == {}
    assert facts(sim)["quotas"] == before["quotas"]
    with pytest.raises(SyntheticExchangeError):
        sim.stage_declaration(SCOPE, uid(16), uid(17))
    assert sim.payload_status(event.event_id) == "held"
    monkeypatch.setattr(module, cap, original_maximum)
    opened = reopen(sim)
    assert opened.counts()["fenced_scopes"] == 1


@pytest.mark.parametrize(
    "cap",
    ["MAX_QUEUED_DECLARATIONS", "MAX_SEQUENCE_SLOTS", "MAX_QUEUED_BYTES", "MAX_RETAINED_BYTES"],
)
def test_normal_capacity_refusal_changes_no_authority_identity_or_quota(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch, cap: str
) -> None:
    monkeypatch.setattr(module, cap, 0)
    before = facts(sim)
    with pytest.raises(SyntheticExchangeError) as error:
        stage(sim)
    fixed(error)
    assert facts(sim) == before


def test_twentieth_gap_inclusive_twenty_first_refused_without_quota(
    sim: SyntheticExchangeSimulator,
) -> None:
    events = [stage(sim) for _ in range(22)]
    for event in events[1:21]:
        assert sim.receive_event(raw_for(sim, event.event_id)).status == "stored"
    before = facts(sim)
    with pytest.raises(SyntheticExchangeError):
        sim.receive_event(raw_for(sim, events[21].event_id))
    assert facts(sim) == before
    assert sim.receive_event(raw_for(sim, events[0].event_id)).status == "stored"
    assert sim.receive_event(raw_for(sim, events[21].event_id)).status == "stored"


def test_hundred_scopes_have_reserved_false_fields(tmp_path: Path) -> None:
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    authority = fixture(scopes=100)
    sim = SyntheticExchangeSimulator.create(
        allowed / "ledger", allowed, authority, FakeClock(datetime(2026, 10, 13, tzinfo=UTC))
    )
    for scope in authority.scopes:
        assert sim.enroll_scope(scope.scope_id)
    assert len(facts(sim)["scopes"]) == 100
    assert all(
        not item["fenced"] and not item["pending_erasure"] for item in facts(sim)["scopes"].values()
    )
    assert sim.enroll_scope(authority.scopes[0].scope_id) is False
    with pytest.raises(SyntheticExchangeError):
        sim.enroll_scope(uid(1999))


def test_batch_maximum_twenty_and_cleanup_priority_at_daily_limit(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "MAX_DAILY_DECLARATIONS", 2)
    first = stage(sim)
    sim.stage_declaration(SCOPE, uid(16), uid(17))
    sim.withdraw_original(HUMAN, SAMPLE)
    assert sim.process_batch(FakeTransport(), limit=1) == {"claimed": 1, "completed": 1}
    assert facts(sim)["outbox"][next(iter(facts(sim)["outbox"]))]["kind"] == "declare"
    assert sim.payload_status(first.event_id) == "held"
    assert MAX_BATCH == 20
    for value in (0, 21, True):
        with pytest.raises(SyntheticExchangeError):
            sim.process_batch(FakeTransport(), limit=value)


def test_actual_cardinality_and_byte_limits_inclusive_projection(
    sim: SyntheticExchangeSimulator,
) -> None:
    data = facts(sim)
    snap = StoreSnapshot(1, data, {})
    for key, cap in (("scopes", 100), ("source_slots", 10_000), ("refusals", 10_000)):
        candidate = copy.deepcopy(data)
        candidate[key] = {str(i): {} for i in range(cap)}
        sim._capacities(candidate, snap, 0)
        candidate[key]["extra"] = {}
        with pytest.raises(SyntheticExchangeError):
            sim._capacities(candidate, snap, 0)
    candidate = copy.deepcopy(data)
    candidate["cleanup"] = {str(i): {"complete": False} for i in range(1_000)}
    sim._capacities(candidate, snap, 0)
    candidate["cleanup"]["extra"] = {"complete": False}
    with pytest.raises(SyntheticExchangeError):
        sim._capacities(candidate, snap, 0)
    candidate = copy.deepcopy(data)
    candidate["outbox"] = {str(i): {"kind": "declare", "blob_id": None} for i in range(1_000)}
    sim._capacities(candidate, snap, 0)
    candidate["outbox"]["extra"] = {"kind": "declare", "blob_id": None}
    with pytest.raises(SyntheticExchangeError):
        sim._capacities(candidate, snap, 0)
    refs = {
        uid(1_000 + i): BlobRef(uid(1_000 + i), "source", 2_000_000, "a" * 64) for i in range(100)
    }
    candidate = copy.deepcopy(data)
    candidate["outbox"] = {key: {"kind": "declare", "blob_id": key} for key in refs}
    exact = StoreSnapshot(1, candidate, refs)
    sim._capacities(candidate, exact, 0)
    with pytest.raises(SyntheticExchangeError):
        sim._capacities(candidate, exact, 1)


def test_source_withdrawal_intent_survives_erase_failure_and_restart(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    event = stage(sim)
    original = sim._erase_owned
    failed = False

    def fail_once(*args: Any, **kwargs: Any) -> StoreSnapshot:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("value-bearing fictional private cause")
        return original(*args, **kwargs)

    monkeypatch.setattr(sim, "_erase_owned", fail_once)
    with pytest.raises(SyntheticExchangeError) as error:
        sim.withdraw_original(HUMAN, SAMPLE)
    fixed(error)
    assert facts(sim)["origins"][HUMAN + "/" + SAMPLE]["withdrawn"]
    assert len(facts(sim)["refusals"]) == 2 and len(facts(sim)["cleanup"]) == 1
    opened = reopen(sim)
    assert opened.counts()["retained_bytes"] == 0
    assert opened.payload_status(event.event_id) == "held"
    assert opened.process_batch(FakeTransport())["completed"] == 1


def test_metadata_refuses_hidden_science_unknown_booleans_and_forged_heads(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    with sim._store.locked() as session:
        snap = session.snapshot()
    mutations = []
    data = copy.deepcopy(snap.data)
    data["events"][event.event_id]["measurement_bytes"] = [0.1, 0.2]
    mutations.append(data)
    data = copy.deepcopy(snap.data)
    data["scopes"][SCOPE]["active"] = "true"
    mutations.append(data)
    data = copy.deepcopy(snap.data)
    data["recipient_heads"] = copy.deepcopy(data["source_heads"])
    mutations.append(data)
    for corrupted in mutations:
        with pytest.raises(SyntheticExchangeError):
            sim._data(StoreSnapshot(snap.generation, corrupted, snap.blobs))


def _race_admission(root: Path, ready: Any, start: Any, result: Any) -> None:
    def deny(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("fictional race permits no network")

    guard = pytest.MonkeyPatch()
    guard.setattr(socket, "socket", deny)
    guard.setattr(socket, "create_connection", deny)
    module.MAX_DAILY_DECLARATIONS = 1
    simulator = SyntheticExchangeSimulator.open(
        root, root.parent, fixture(), FakeClock(datetime(2026, 10, 13, tzinfo=UTC))
    )
    ready.send(True)
    assert start.recv() is True
    try:
        stage(simulator)
        result.send("accepted")
    except SyntheticExchangeError:
        result.send("held")


def test_two_processes_contend_for_last_daily_admission(sim: SyntheticExchangeSimulator) -> None:
    context = multiprocessing.get_context("fork")
    ready_pairs = [context.Pipe(False) for _ in range(2)]
    start_pairs = [context.Pipe(False) for _ in range(2)]
    result_pairs = [context.Pipe(False) for _ in range(2)]
    children = [
        context.Process(
            target=_race_admission,
            args=(sim._store.root, ready_pairs[i][1], start_pairs[i][0], result_pairs[i][1]),
        )
        for i in range(2)
    ]
    try:
        for child in children:
            child.start()
        for receiver, _ in ready_pairs:
            assert receiver.poll(10) and receiver.recv() is True
        for _, sender in start_pairs:
            sender.send(True)
        results = []
        for receiver, _ in result_pairs:
            assert receiver.poll(10)
            results.append(receiver.recv())
        for child in children:
            child.join(10)
            assert child.exitcode == 0
        assert sorted(results) == ["accepted", "held"]
        assert len(facts(sim)["events"]) == 1
        assert facts(sim)["quotas"] == {"source/" + HUMAN + "/2026-10-13": 1}
    finally:
        for child in children:
            if child.is_alive():
                child.terminate()
                child.join(10)
        for pairs in (ready_pairs, start_pairs, result_pairs):
            for first, second in pairs:
                first.close()
                second.close()


def test_gapped_recipient_and_source_outbox_count_as_two_role_records(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = stage(sim), stage(sim)
    monkeypatch.setattr(module, "MAX_QUEUED_DECLARATIONS", 2)
    before = facts(sim)
    with pytest.raises(SyntheticExchangeError):
        sim.receive_event(raw_for(sim, second.event_id))
    assert facts(sim) == before
    assert sim.receive_event(raw_for(sim, first.event_id)).status == "stored"
    assert sim.receive_event(raw_for(sim, second.event_id)).status == "stored"


def test_no_new_scope_escape_after_reserved_saturation_fence(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage(sim)
    monkeypatch.setattr(module, "MAX_REFUSALS", 0)
    sim.withdraw_original(HUMAN, SAMPLE)
    # Existing peer provisioning is not an escape from an unresolved fence.
    expanded = replace(
        sim._authority,
        scopes=sim._authority.scopes + (FakeScope(SOURCE, RECIPIENT, uid(23), HUMAN),),
    )
    opened = reopen(sim, expanded)
    with pytest.raises(SyntheticExchangeError):
        opened.enroll_scope(uid(23))
    assert len(facts(opened)["scopes"]) == 2


def test_expired_claim_while_disconnected_does_not_spend_attempt(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    claim = sim._claim(1)[0]
    sim.set_scope_status(SCOPE, connected=False)
    sim._clock.now += timedelta(seconds=CLAIM_RECOVERY_SECONDS + 1)
    assert sim.process_batch(FakeTransport())["claimed"] == 0
    item = facts(sim)["outbox"][event.event_id]
    assert item["claim"] == claim.nonce and item["attempts"] == 0
    sim.set_scope_status(SCOPE, connected=True)
    assert sim.process_batch(FakeTransport())["claimed"] == 0
    assert facts(sim)["outbox"][event.event_id]["attempts"] == 1


def test_cleanup_after_scope_revocation_requires_separate_current_fake_authority(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    sim.process_batch(FakeTransport())
    sim.set_scope_status(SCOPE, revoke=True, cleanup_allowed=False)
    sim.withdraw_original(HUMAN, SAMPLE)
    assert sim.process_batch(FakeTransport())["claimed"] == 0
    assert sim.counts()["pending_cleanup"] == 1
    sim.set_scope_status(SCOPE, cleanup_allowed=True)
    assert sim.process_batch(FakeTransport())["completed"] == 1
    assert sim.counts()["retained_bytes"] == 0
    assert sim.payload_status(event.event_id) == "held"


def test_sample_wide_empty_retirement_with_no_source_event_still_erases_and_fences(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    sim.process_batch(FakeTransport())
    source = json.loads(raw_for(sim, event.event_id))
    source.update(
        kind="retire",
        event_id=uid(88),
        stream_sequence=10,
        previous_event_sha256="a" * 64,
        payload={"sample_handle": event.sample_handle, "measurement_handles": []},
    )
    receipt = sim.receive_event(json.dumps(source, separators=(",", ":")).encode())
    assert receipt.status == "retired" and receipt.payload_absent
    assert sim.counts()["retained_bytes"] == 0
    assert facts(sim)["scopes"][SCOPE]["fenced"]
    assert sim.payload_status(event.event_id) == "held"


def test_source_grant_interruption_resumes_intents_before_erasure(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = stage(sim)
    other = sim.stage_declaration(SCOPE, uid(16), uid(17))
    original = sim.withdraw_original

    def fail(*args: Any, **kwargs: Any) -> int:
        raise OSError("fictional interruption after canonical grant refusal")

    monkeypatch.setattr(sim, "withdraw_original", fail)
    with pytest.raises(SyntheticExchangeError) as error:
        sim.withdraw_grant(HUMAN, GRANT)
    fixed(error)
    before = facts(sim)
    assert len(before["blob_owners"]) == 2
    assert before["retired_grants"] == {HUMAN + "/" + GRANT: True}
    monkeypatch.setattr(sim, "withdraw_original", original)
    order: list[bool] = []
    original_erase = PrivateExchangeSession.erase_blobs

    def witness(
        session: Any, restricted_data: dict[str, Any], blob_ids: Any, expected_generation: int
    ) -> StoreSnapshot:
        order.append(bool(restricted_data["refusals"]) and bool(restricted_data["cleanup"]))
        return original_erase(session, restricted_data, blob_ids, expected_generation)

    monkeypatch.setattr(PrivateExchangeSession, "erase_blobs", witness)
    opened = reopen(sim)
    assert opened.counts()["retained_bytes"] == 0 and all(order)
    assert len(facts(opened)["cleanup"]) == 2
    assert opened.payload_status(first.event_id) == opened.payload_status(other.event_id) == "held"
    assert opened.process_batch(FakeTransport())["completed"] == 2


def test_cleanup_reply_loss_reuses_exact_retirement_bytes_after_midnight(
    sim: SyntheticExchangeSimulator,
) -> None:
    stage(sim)
    sim.process_batch(FakeTransport())
    sim.withdraw_original(HUMAN, SAMPLE)
    first = sim._claim(1)[0]
    receipt = sim.receive_event(first.raw)
    assert receipt.payload_absent
    assert sim._checkpoint(first, None, True) is False
    sim._clock.now += timedelta(days=1)
    new = reopen(sim)._claim(1)[0]
    assert new.raw == first.raw
    again = sim.receive_event(new.raw)
    assert again.status == "retired" and again.payload_absent
    assert sim._checkpoint(new, again, False) is True
    assert sim.counts()["pending_cleanup"] == 0


def test_metadata_cannot_hide_science_as_retirement_or_join_other_human(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    with sim._store.locked() as session:
        snap = session.snapshot()
    candidate = copy.deepcopy(snap.data)
    blob = candidate["events"][event.event_id]["source_blob"]
    candidate["blob_owners"][blob]["science"] = False
    with pytest.raises(SyntheticExchangeError):
        sim._data(StoreSnapshot(snap.generation, candidate, snap.blobs))
    reassigned = replace(
        sim._authority,
        scopes=tuple(replace(scope, human_id=OTHER_HUMAN) for scope in sim._authority.scopes),
    )
    with pytest.raises(SyntheticExchangeError) as error:
        reopen(sim, reassigned)
    fixed(error)


def test_monotonic_synthetic_true_is_sent_on_next_source_declaration(
    sim: SyntheticExchangeSimulator,
) -> None:
    event = stage(sim)
    source = json.loads(raw_for(sim, event.event_id))
    source["event_id"], source["stream_sequence"], source["previous_event_sha256"] = (
        uid(87),
        2,
        event.sha256,
    )
    source["payload"]["synthetic_claim"] = True
    assert sim.receive_event(json.dumps(source, separators=(",", ":")).encode()).status == "stored"
    next_source = stage(sim)
    assert json.loads(raw_for(sim, next_source.event_id))["payload"]["synthetic_claim"] is True
    assert facts(sim)["origins"][HUMAN + "/" + SAMPLE]["synthetic"]


def test_new_grant_refusal_metadata_failure_uses_reserved_fence(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage(sim)
    original = PrivateExchangeSession.commit_metadata

    def full(
        session: PrivateExchangeSession, data: dict[str, Any], expected_generation: int
    ) -> StoreSnapshot:
        if data["retired_grants"]:
            raise ValueError("fictional full metadata image")
        return original(session, data, expected_generation)

    monkeypatch.setattr(PrivateExchangeSession, "commit_metadata", full)
    assert sim.withdraw_grant(HUMAN, GRANT) == 2
    data = facts(sim)
    assert all(scope["fenced"] and scope["pending_erasure"] for scope in data["scopes"].values())
    assert data["origins"][HUMAN + "/" + SAMPLE]["withdrawn"]
    assert sim.counts()["retained_bytes"] == 0
    assert sim.counts()["pending_cleanup"] == 2


def test_source_delivery_orders_owned_slots_before_filling_gap_budget(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    serial = 100_000

    def descending() -> UUID:
        nonlocal serial
        serial -= 1
        return UUID(int=serial)

    # Deliberately reverse opaque event-ID ordering relative to sequence ordering.
    monkeypatch.setattr(module, "uuid4", descending)
    for _ in range(45):
        stage(sim)
    assert sim.process_batch(FakeTransport()) == {"claimed": 20, "completed": 20}
    assert sim.process_batch(FakeTransport()) == {"claimed": 20, "completed": 20}
    assert sim.process_batch(FakeTransport()) == {"claimed": 5, "completed": 5}
    assert sim.counts()["queued_declarations"] == 0


def test_transport_rejects_callback_objects_before_claim_or_execution(
    sim: SyntheticExchangeSimulator,
) -> None:
    stage(sim)
    before = facts(sim)
    called = False

    class ArbitraryCallback:
        def __len__(self) -> int:
            nonlocal called
            called = True
            return 1

        def __getitem__(self, key: int) -> str:
            nonlocal called
            called = True
            return "deliver"

    for script in (
        ArbitraryCallback(),
        ["deliver"],
        ("unexpected-private-value",),
        ("deliver",) * 21,
    ):
        transport = FakeTransport(script)  # type: ignore[arg-type]
        with pytest.raises(SyntheticExchangeError) as error:
            sim.process_batch(transport)
        fixed(error)
    assert called is False and facts(sim) == before


@pytest.mark.parametrize("retired", [False, True])
def test_source_alias_uuid_collision_never_reuses_live_or_retired_sample_identity(
    sim: SyntheticExchangeSimulator,
    monkeypatch: pytest.MonkeyPatch,
    retired: bool,
) -> None:
    first = stage(sim)
    if retired:
        sim.withdraw_original(HUMAN, SAMPLE)
        sim.process_batch(FakeTransport())
    before = facts(sim)
    identities = iter((UUID(first.sample_handle), UUID(int=1000), UUID(int=1001), UUID(int=1002)))
    monkeypatch.setattr(module, "uuid4", lambda: next(identities))
    with pytest.raises(SyntheticExchangeError) as error:
        sim.stage_declaration(SCOPE, uid(16), uid(17))
    fixed(error)
    assert facts(sim) == before


def test_cleanup_ack_checks_science_in_every_known_same_owner_alias(
    sim: SyntheticExchangeSimulator,
) -> None:
    first, second = stage(sim), stage(sim, OTHER_SCOPE)
    sim.process_batch(FakeTransport())
    sim.create_synthetic_preparation(second.event_id)
    sim.withdraw_original(HUMAN, SAMPLE)
    claim = sim._claim(1)[0]
    prepared = prepare_node_exchange_event(claim.raw)
    assert str(prepared.event.scope_id) == SCOPE
    # Rehearse a partial receiver erase that falsely says the first scope finished.
    # The sibling recipient/preparation copies stay registered and physically present.
    with sim._store.locked() as session:
        snap = session.snapshot()
        data = copy.deepcopy(snap.data)
        removed = [
            key
            for key, owner in data["blob_owners"].items()
            if owner["scope"] == SCOPE and owner["science"]
        ]
        for key in removed:
            del data["blob_owners"][key]
        for event in data["events"].values():
            for role in ("source", "recipient"):
                if event[role + "_blob"] in removed:
                    event[role + "_blob"] = None
        data["bindings"] = {
            key: value for key, value in data["bindings"].items() if value["blob_id"] not in removed
        }
        session.erase_blobs(data, removed, snap.generation)
    assert sim._checkpoint(claim, sim._receipt(prepared, "retired", True), False) is False
    assert sim.counts()["pending_cleanup"] == 2 and sim.counts()["retained_bytes"] > 0
    assert sim.payload_status(first.event_id) == "held"


@pytest.mark.parametrize(
    "boundary",
    ["source_withdrawal", "fresh_retirement", "withdrawn_recovery", "cleanup_materialization"],
)
def test_metadata_image_saturation_activates_existing_scope_fence(
    sim: SyntheticExchangeSimulator,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    receipt = stage(sim)
    original = raw_for(sim, receipt.event_id)
    sim.process_batch(FakeTransport())
    if boundary == "withdrawn_recovery":
        with sim._store.locked() as session:
            current = session.snapshot()
            data = copy.deepcopy(current.data)
            data["origins"][HUMAN + "/" + SAMPLE]["withdrawn"] = True
            session.commit_metadata(data, current.generation)
    elif boundary == "cleanup_materialization":
        sim.withdraw_original(HUMAN, SAMPLE)
    before = facts(sim)
    current_bytes = len((sim._store.root / "state.json").read_bytes())
    monkeypatch.setattr(store_module, "MAX_METADATA_BYTES", current_bytes + 5)
    try:
        if boundary == "source_withdrawal":
            sim.withdraw_original(HUMAN, SAMPLE)
        elif boundary == "fresh_retirement":
            value = json.loads(original)
            value.update(
                kind="retire",
                event_id=uid(900),
                stream_sequence=1,
                previous_event_sha256=receipt.sha256,
                payload={"sample_handle": receipt.sample_handle, "measurement_handles": []},
            )
            assert (
                sim.receive_event(json.dumps(value, separators=(",", ":")).encode()).status
                == "held"
            )
        elif boundary == "withdrawn_recovery":
            reopen(sim).payload_status(receipt.event_id)
        else:
            sim.process_batch(FakeTransport())
    except SyntheticExchangeError as error:
        assert str(error) == MESSAGE and error.__context__ is None and error.__cause__ is None
    after = facts(sim)
    assert after["scopes"][SCOPE]["fenced"] and after["scopes"][SCOPE]["pending_erasure"]
    assert after["origins"][HUMAN + "/" + SAMPLE]["withdrawn"]
    for collection in ("aliases", "refusals", "cleanup", "source_slots", "recipient_slots"):
        assert after[collection] == before[collection]
    assert after["quotas"] == before["quotas"]
    for collection in ("events", "blob_owners", "outbox"):
        assert set(after[collection]) <= set(before[collection])
    assert after["source_heads"] == before["source_heads"]
    assert after["recipient_heads"] == before["recipient_heads"]
    assert sim.payload_status(receipt.event_id) == "held"
    # Restoring the serializer capacity must not reopen the permanent fence.
    monkeypatch.setattr(store_module, "MAX_METADATA_BYTES", 32_000_000)
    assert reopen(sim).payload_status(receipt.event_id) == "held"


@pytest.mark.parametrize("admitted", [False, True])
def test_exact_original_measurement_removal_holds_receive_retry_use_and_preparation(
    sim: SyntheticExchangeSimulator,
    admitted: bool,
) -> None:
    receipt = stage(sim)
    original = raw_for(sim, receipt.event_id)
    if admitted:
        sim.process_batch(FakeTransport())
    sibling_only = replace(
        sim._authority,
        origins=tuple(
            origin for origin in sim._authority.origins if origin.measurement_id != MEASUREMENT
        ),
    )
    opened = reopen(sim, sibling_only)
    before = facts(opened)
    assert opened.receive_event(original).status == "held"
    assert opened.payload_status(receipt.event_id) == "held"
    with pytest.raises(SyntheticExchangeError) as error:
        opened.create_synthetic_preparation(receipt.event_id)
    fixed(error)
    assert opened.process_batch(FakeTransport())["claimed"] == 0
    after = facts(opened)
    assert after["quotas"] == before["quotas"] and after["outbox"] == before["outbox"]
    assert after["blob_owners"] == before["blob_owners"]


def test_missing_exact_measurement_does_not_recover_or_checkpoint_a_sibling_authorized_claim(
    sim: SyntheticExchangeSimulator,
) -> None:
    receipt = stage(sim)
    claim = sim._claim(1)[0]
    stored = sim.receive_event(claim.raw)
    sibling_only = replace(
        sim._authority,
        origins=tuple(
            origin for origin in sim._authority.origins if origin.measurement_id != MEASUREMENT
        ),
    )
    opened = reopen(sim, sibling_only)
    opened._clock.now += timedelta(seconds=CLAIM_RECOVERY_SECONDS + 1)
    assert opened.process_batch(FakeTransport())["claimed"] == 0
    assert facts(opened)["outbox"][receipt.event_id]["attempts"] == 0
    assert opened._checkpoint(claim, stored, False) is False
    assert receipt.event_id in facts(opened)["outbox"]
    assert facts(opened)["outbox"][receipt.event_id]["attempts"] == 0


def test_missing_exact_measurement_holds_draft_release_without_reidentification(
    sim: SyntheticExchangeSimulator,
) -> None:
    receipt = stage(sim, draft=True)
    sibling_only = replace(
        sim._authority,
        origins=tuple(
            origin for origin in sim._authority.origins if origin.measurement_id != MEASUREMENT
        ),
    )
    opened = reopen(sim, sibling_only)
    before = facts(opened)
    with pytest.raises(SyntheticExchangeError) as error:
        opened.queue_draft(receipt.event_id)
    fixed(error)
    assert facts(opened) == before


@pytest.mark.parametrize("changed_field", ["human_id", "sample_id", "grant_id"])
def test_sibling_cannot_supply_changed_original_authority_tuple(
    sim: SyntheticExchangeSimulator, changed_field: str
) -> None:
    receipt = stage(sim)
    original = raw_for(sim, receipt.event_id)
    sim.process_batch(FakeTransport())
    changes: dict[str, Any] = {changed_field: uid(901)}
    changed = replace(
        sim._authority,
        origins=tuple(
            replace(origin, **changes) if origin.measurement_id == MEASUREMENT else origin
            for origin in sim._authority.origins
        ),
    )
    opened = reopen(sim, changed)
    before = facts(opened)
    assert opened.receive_event(original).status == "held"
    assert opened.payload_status(receipt.event_id) == "held"
    with pytest.raises(SyntheticExchangeError) as error:
        opened.create_synthetic_preparation(receipt.event_id)
    fixed(error)
    assert facts(opened) == before


def test_missing_measurement_holds_only_that_measurement_and_preserves_cleanup_authority(
    sim: SyntheticExchangeSimulator,
) -> None:
    missing, sibling = stage(sim), stage(sim, measurement=uid(15))
    sim.process_batch(FakeTransport())
    sim.create_synthetic_preparation(missing.event_id)
    changed = replace(
        sim._authority,
        origins=tuple(
            origin for origin in sim._authority.origins if origin.measurement_id != MEASUREMENT
        ),
    )
    opened = reopen(sim, changed)
    assert opened.payload_status(missing.event_id) == "held"
    assert opened.payload_status(sibling.event_id) == "available_for_synthetic_simulation"
    opened.withdraw_original(HUMAN, SAMPLE)
    assert opened.process_batch(FakeTransport()) == {"claimed": 1, "completed": 1}
    assert facts(opened)["blob_owners"] == facts(opened)["aliases"] == {}
    assert opened.counts()["retained_bytes"] == 0


def test_unstaged_original_withdrawal_metadata_saturation_fences_existing_human_scopes(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = stage(sim)
    sim.process_batch(FakeTransport())
    before = facts(sim)
    assert HUMAN + "/" + uid(16) not in before["origins"]
    current_bytes = len((sim._store.root / "state.json").read_bytes())
    monkeypatch.setattr(store_module, "MAX_METADATA_BYTES", current_bytes + 5)
    try:
        sim.withdraw_original(HUMAN, uid(16))
    except SyntheticExchangeError as metadata_error:
        assert (
            str(metadata_error) == MESSAGE
            and metadata_error.__context__ is None
            and metadata_error.__cause__ is None
        )
    after = facts(sim)
    assert all(value["fenced"] and value["pending_erasure"] for value in after["scopes"].values())
    for collection in ("origins", "aliases", "events", "refusals", "cleanup", "outbox", "quotas"):
        assert after[collection] == before[collection]
    monkeypatch.setattr(store_module, "MAX_METADATA_BYTES", 32_000_000)
    opened = reopen(sim)
    assert opened.payload_status(receipt.event_id) == "held"
    with pytest.raises(SyntheticExchangeError) as error:
        opened.stage_declaration(SCOPE, uid(16), uid(17))
    fixed(error)


@pytest.mark.parametrize("withdrawal", ["original", "grant"])
def test_metadata_saturation_without_original_human_scope_refuses_without_false_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, withdrawal: str
) -> None:
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    sim = SyntheticExchangeSimulator.create(
        allowed / "ledger",
        allowed,
        fixture(extra_human=True),
        FakeClock(datetime(2026, 10, 13, tzinfo=UTC)),
    )
    sim.enroll_scope(uid(32))
    receipt = stage(sim, uid(32))
    sim.process_batch(FakeTransport())
    before = facts(sim)
    current_bytes = len((sim._store.root / "state.json").read_bytes())
    monkeypatch.setattr(store_module, "MAX_METADATA_BYTES", current_bytes + 5)
    with pytest.raises(SyntheticExchangeError) as error:
        if withdrawal == "original":
            sim.withdraw_original(HUMAN, uid(16))
        else:
            sim.withdraw_grant(HUMAN, GRANT)
    fixed(error)
    assert facts(sim) == before
    assert sim.payload_status(receipt.event_id) == "available_for_synthetic_simulation"


@pytest.mark.parametrize("restriction", ["sealed", "synthetic_restricted"])
@pytest.mark.parametrize("draft", [False, True])
def test_initial_sibling_restriction_precedes_admission_draft_and_restart(
    sim: SyntheticExchangeSimulator, restriction: str, draft: bool
) -> None:
    changes: dict[str, Any] = {restriction: True}
    authority = replace(
        sim._authority,
        origins=tuple(
            replace(origin, **changes) if origin.measurement_id == uid(15) else origin
            for origin in sim._authority.origins
        ),
    )
    opened = reopen(sim, authority)
    before = facts(opened)
    if restriction == "sealed":
        with pytest.raises(SyntheticExchangeError) as error:
            stage(opened, draft=draft)
        fixed(error)
        after = facts(opened)
        assert after["origins"][HUMAN + "/" + SAMPLE]["sealed"] is True
        for collection in ("aliases", "events", "source_slots", "outbox", "blob_owners", "quotas"):
            assert after[collection] == before[collection]
        clean = reopen(opened, sim._authority)
        with pytest.raises(SyntheticExchangeError) as error:
            stage(clean, OTHER_SCOPE)
        fixed(error)
        assert facts(clean)["origins"][HUMAN + "/" + SAMPLE]["sealed"] is True
    else:
        receipt = stage(opened, draft=draft)
        raw = raw_for(opened, receipt.event_id)
        assert facts(opened)["origins"][HUMAN + "/" + SAMPLE]["synthetic"] is True
        assert json.loads(raw)["payload"]["synthetic_claim"] is True
        # The known sibling can disappear entirely; the first claim must survive.
        clean_authority = replace(
            sim._authority,
            origins=tuple(
                origin for origin in sim._authority.origins if origin.measurement_id != uid(15)
            ),
        )
        clean = reopen(opened, clean_authority)
        if draft:
            clean.queue_draft(receipt.event_id)
        assert raw_for(clean, receipt.event_id) == raw
        assert clean.process_batch(FakeTransport())["completed"] == 1
        later = stage(clean, OTHER_SCOPE)
        assert json.loads(raw_for(clean, later.event_id))["payload"]["synthetic_claim"] is True
        assert facts(clean)["origins"][HUMAN + "/" + SAMPLE]["synthetic"] is True


@pytest.mark.parametrize("restriction", ["sealed", "synthetic_restricted"])
def test_current_sibling_restriction_survives_grant_label_change_and_omission(
    sim: SyntheticExchangeSimulator, restriction: str
) -> None:
    receipt = stage(sim)
    sim.process_batch(FakeTransport())
    changes: dict[str, Any] = {restriction: True, "grant_id": uid(802)}
    different_grant = replace(
        sim._authority,
        origins=tuple(
            replace(origin, **changes)
            for origin in sim._authority.origins
            if origin.measurement_id == uid(15)
        ),
    )
    opened = reopen(sim, different_grant)
    assert opened.payload_status(receipt.event_id) == "held"
    group = facts(opened)["origins"][HUMAN + "/" + SAMPLE]
    assert group["grant"] == GRANT
    assert group["sealed" if restriction == "sealed" else "synthetic"] is True
    clean = reopen(opened, sim._authority)
    if restriction == "sealed":
        assert clean.payload_status(receipt.event_id) == "held"
        with pytest.raises(SyntheticExchangeError) as error:
            stage(clean, OTHER_SCOPE)
        fixed(error)
    else:
        later = stage(clean, OTHER_SCOPE)
        assert json.loads(raw_for(clean, later.event_id))["payload"]["synthetic_claim"] is True
    assert facts(clean)["origins"][HUMAN + "/" + SAMPLE]["grant"] == GRANT


@pytest.mark.parametrize("measurement", [MEASUREMENT, uid(15)])
def test_initial_conflicting_canonical_grants_refuse_without_selecting_an_origin(
    sim: SyntheticExchangeSimulator, measurement: str
) -> None:
    authority = replace(
        sim._authority,
        origins=tuple(
            replace(origin, grant_id=uid(802)) if origin.measurement_id == uid(15) else origin
            for origin in sim._authority.origins
        ),
    )
    opened = reopen(sim, authority)
    before = facts(opened)
    with pytest.raises(SyntheticExchangeError) as error:
        stage(opened, measurement=measurement)
    fixed(error)
    assert facts(opened) == before


@pytest.mark.parametrize("restriction", ["sealed", "synthetic_restricted"])
def test_initial_restriction_with_conflicting_grants_uses_reserved_fence(
    sim: SyntheticExchangeSimulator, restriction: str
) -> None:
    changes: dict[str, Any] = {restriction: True, "grant_id": uid(802)}
    authority = replace(
        sim._authority,
        origins=tuple(
            replace(origin, **changes) if origin.measurement_id == uid(15) else origin
            for origin in sim._authority.origins
        ),
    )
    opened = reopen(sim, authority)
    before = facts(opened)
    with pytest.raises(SyntheticExchangeError) as error:
        stage(opened)
    fixed(error)
    after = facts(opened)
    assert all(scope["fenced"] and scope["pending_erasure"] for scope in after["scopes"].values())
    for collection in (
        "origins",
        "aliases",
        "events",
        "source_slots",
        "outbox",
        "blob_owners",
        "quotas",
    ):
        assert after[collection] == before[collection]
    with pytest.raises(SyntheticExchangeError) as error:
        stage(reopen(opened, sim._authority))
    fixed(error)


@pytest.mark.parametrize("restriction", ["sealed", "synthetic_restricted"])
def test_saturated_new_restriction_row_fences_before_admission_and_survives_omission(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch, restriction: str
) -> None:
    changes: dict[str, Any] = {restriction: True}
    authority = replace(
        sim._authority,
        origins=tuple(
            replace(origin, **changes) if origin.measurement_id == uid(15) else origin
            for origin in sim._authority.origins
        ),
    )
    opened = reopen(sim, authority)
    before = facts(opened)
    monkeypatch.setattr(
        store_module, "MAX_METADATA_BYTES", len((sim._store.root / "state.json").read_bytes()) + 5
    )
    with pytest.raises(SyntheticExchangeError) as error:
        stage(opened)
    fixed(error)
    after = facts(opened)
    assert all(scope["fenced"] and scope["pending_erasure"] for scope in after["scopes"].values())
    for collection in (
        "origins",
        "aliases",
        "events",
        "source_slots",
        "outbox",
        "blob_owners",
        "quotas",
    ):
        assert after[collection] == before[collection]
    monkeypatch.setattr(store_module, "MAX_METADATA_BYTES", 32_000_000)
    with pytest.raises(SyntheticExchangeError) as error:
        stage(reopen(opened, sim._authority))
    fixed(error)


def test_initial_synthetic_restriction_survives_later_quota_refusal(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    sim.stage_declaration(SCOPE, uid(16), uid(17))
    monkeypatch.setattr(module, "MAX_DAILY_DECLARATIONS", 1)
    authority = replace(
        sim._authority,
        origins=tuple(
            replace(origin, synthetic_restricted=True)
            if origin.measurement_id == uid(15)
            else origin
            for origin in sim._authority.origins
        ),
    )
    opened = reopen(sim, authority)
    before = facts(opened)
    with pytest.raises(SyntheticExchangeError) as error:
        stage(opened)
    fixed(error)
    after = facts(opened)
    assert HUMAN + "/" + SAMPLE in after["origins"], (
        "known restriction was lost on refused admission"
    )
    assert after["origins"][HUMAN + "/" + SAMPLE]["synthetic"] is True
    for collection in ("aliases", "events", "source_slots", "outbox", "blob_owners", "quotas"):
        assert after[collection] == before[collection]
    monkeypatch.setattr(module, "MAX_DAILY_DECLARATIONS", 100)
    later = stage(reopen(opened, sim._authority))
    assert json.loads(raw_for(opened, later.event_id))["payload"]["synthetic_claim"] is True


@pytest.mark.parametrize("restriction", ["sealed", "synthetic_restricted"])
def test_same_sample_other_human_restriction_does_not_group_or_fence(
    tmp_path: Path, restriction: str
) -> None:
    authority = fixture(extra_human=True)
    changes: dict[str, Any] = {restriction: True, "grant_id": uid(803)}
    authority = replace(
        authority,
        origins=tuple(
            replace(origin, **changes) if origin.human_id == OTHER_HUMAN else origin
            for origin in authority.origins
        ),
    )
    allowed = tmp_path.resolve() / "private"
    allowed.mkdir(mode=0o700)
    sim = SyntheticExchangeSimulator.create(
        allowed / "ledger", allowed, authority, FakeClock(datetime(2026, 10, 13, tzinfo=UTC))
    )
    sim.enroll_scope(SCOPE)
    sim.enroll_scope(uid(32))
    receipt = stage(sim)
    group = facts(sim)["origins"][HUMAN + "/" + SAMPLE]
    assert group["sealed"] is group["synthetic"] is False
    assert json.loads(raw_for(sim, receipt.event_id))["payload"]["synthetic_claim"] is False
    assert all(not scope["fenced"] for scope in facts(sim)["scopes"].values())
    assert facts(sim)["quotas"] == {"source/" + HUMAN + "/2026-10-13": 1}


@pytest.mark.parametrize("restriction", ["sealed", "synthetic_restricted"])
def test_known_sample_restriction_survives_missing_selected_measurement_refusal(
    sim: SyntheticExchangeSimulator, restriction: str
) -> None:
    changes: dict[str, Any] = {restriction: True}
    authority = replace(
        sim._authority,
        origins=tuple(
            replace(origin, **changes)
            for origin in sim._authority.origins
            if origin.measurement_id == uid(15)
        ),
    )
    opened = reopen(sim, authority)
    before = facts(opened)
    with pytest.raises(SyntheticExchangeError) as error:
        stage(opened)
    fixed(error)
    after = facts(opened)
    assert HUMAN + "/" + SAMPLE in after["origins"], "known sample restriction was forgotten"
    assert (
        after["origins"][HUMAN + "/" + SAMPLE]["sealed" if restriction == "sealed" else "synthetic"]
        is True
    )
    for collection in ("aliases", "events", "source_slots", "outbox", "blob_owners", "quotas"):
        assert after[collection] == before[collection]
    clean = reopen(opened, sim._authority)
    if restriction == "sealed":
        with pytest.raises(SyntheticExchangeError) as error:
            stage(clean)
        fixed(error)
    else:
        later = stage(clean)
        assert json.loads(raw_for(clean, later.event_id))["payload"]["synthetic_claim"] is True


def test_completed_absence_cannot_reopen_human_through_new_scope_grant_or_missing_label(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch
) -> None:
    restricted = replace(
        sim._authority,
        origins=tuple(
            replace(origin, sealed=True) if origin.measurement_id == uid(15) else origin
            for origin in sim._authority.origins
        ),
    )
    opened = reopen(sim, restricted)
    monkeypatch.setattr(
        store_module, "MAX_METADATA_BYTES", len((sim._store.root / "state.json").read_bytes()) + 5
    )
    with pytest.raises(SyntheticExchangeError):
        stage(opened)
    monkeypatch.setattr(store_module, "MAX_METADATA_BYTES", 32_000_000)
    with sim._store.locked() as session:
        snapshot = session.snapshot()
        assert session.verified_absent([]) and snapshot.blobs == {}
        # Trusted absence projection only: completion may clear a pending obligation,
        # but it supplies no authority to release the separately permanent fence.
        completed = copy.deepcopy(snapshot.data)
        for scope in completed["scopes"].values():
            scope["fenced"] = True
            scope["pending_erasure"] = False
        session.commit_metadata(completed, snapshot.generation)
    authority = replace(
        sim._authority,
        scopes=sim._authority.scopes
        + (
            FakeScope(SOURCE, RECIPIENT, uid(23), HUMAN),
            FakeScope(SOURCE, RECIPIENT, uid(32), OTHER_HUMAN),
        ),
        origins=tuple(
            replace(origin, grant_id=uid(802))
            for origin in sim._authority.origins
            if origin.measurement_id != uid(15)
        )
        + (SyntheticOrigin(OTHER_HUMAN, uid(803), SAMPLE, MEASUREMENT),),
    )
    clean = reopen(opened, authority)
    before = facts(clean)
    with pytest.raises(SyntheticExchangeError) as error:
        clean.enroll_scope(uid(23))
    fixed(error)
    assert facts(clean) == before
    assert clean.enroll_scope(uid(32)) is True
    other = stage(clean, uid(32))
    assert other.status == "stored"
    assert facts(clean)["quotas"] == {"source/" + OTHER_HUMAN + "/2026-10-13": 1}


def erased_alias_cleanup_claims(sim: SyntheticExchangeSimulator) -> list[Any]:
    stage(sim)
    stage(sim, OTHER_SCOPE)
    assert sim.process_batch(FakeTransport()) == {"claimed": 2, "completed": 2}
    sim.withdraw_original(HUMAN, SAMPLE)
    claims = sim._claim(2)
    assert len(claims) == 2
    first = sim.receive_event(claims[0].raw)
    assert first.status == "retired" and first.payload_absent
    assert sim._checkpoint(claims[0], first, False)
    assert facts(sim)["aliases"] == {}
    return claims


@pytest.mark.parametrize("scope_count", [2, 3])
@pytest.mark.parametrize("measurement_count", [1, 2])
def test_multiscope_cleanup_converges_and_later_unrelated_samples_follow_retirement_heads(
    sim: SyntheticExchangeSimulator, scope_count: int, measurement_count: int
) -> None:
    sim = reopen(sim, fixture(scopes=scope_count))
    scopes = [uid(21 + i) for i in range(scope_count)]
    for scope in scopes:
        sim.enroll_scope(scope)
        stage(sim, scope)
        if measurement_count == 2:
            stage(sim, scope, measurement=uid(15))
    assert sim.process_batch(FakeTransport())["completed"] == scope_count * measurement_count
    sim.withdraw_original(HUMAN, SAMPLE)
    assert sim.process_batch(FakeTransport()) == {"claimed": scope_count, "completed": scope_count}
    assert (
        sim.counts()["retained_bytes"]
        == sim.counts()["pending_cleanup"]
        == sim.counts()["fenced_scopes"]
        == 0
    )
    later = [sim.stage_declaration(scope, uid(16), uid(17)) for scope in scopes]
    assert sim.process_batch(FakeTransport()) == {"claimed": scope_count, "completed": scope_count}
    assert all(
        sim.payload_status(event.event_id) == "available_for_synthetic_simulation"
        for event in later
    )
    data = facts(sim)
    for scope in scopes:
        stream = SOURCE + "/" + RECIPIENT + "/" + scope
        assert data["recipient_heads"][stream] == data["source_heads"][stream]
        assert data["recipient_heads"][stream]["stream_sequence"] == measurement_count + 1


@pytest.mark.parametrize("mutation", ["whitespace", "event", "sequence", "predecessor", "handles"])
def test_erased_alias_retirement_changed_bytes_never_acknowledge_absence_or_rewrite_identity(
    sim: SyntheticExchangeSimulator, mutation: str
) -> None:
    claims = erased_alias_cleanup_claims(sim)
    original = claims[1].raw
    receipt = sim.receive_event(original)
    assert receipt.status == "retired" and receipt.payload_absent
    assert sim._checkpoint(claims[1], receipt, False)
    before = facts(sim)
    value = json.loads(original)
    if mutation == "whitespace":
        changed = original + b" "
    else:
        if mutation == "event":
            value["event_id"] = uid(910)
        elif mutation == "sequence":
            value["stream_sequence"] += 1
        elif mutation == "predecessor":
            value["previous_event_sha256"] = "f" * 64
        else:
            value["payload"]["measurement_handles"] = []
        changed = json.dumps(value, separators=(",", ":")).encode()
    response = sim.receive_event(changed)
    assert response.status in ("held", "conflict") and response.payload_absent is False
    after = facts(sim)
    for collection in (
        "events",
        "source_slots",
        "recipient_slots",
        "source_heads",
        "recipient_heads",
        "outbox",
        "blob_owners",
        "quotas",
    ):
        assert after[collection] == before[collection]
    assert sim.counts()["retained_bytes"] == 0


def test_erased_alias_sparse_retirement_retains_its_slot_without_inventing_missing_science(
    sim: SyntheticExchangeSimulator,
) -> None:
    first, second = stage(sim), stage(sim, OTHER_SCOPE)
    late_science = raw_for(sim, second.event_id)
    source_claims = sim._claim(2)
    receipt = sim.receive_event(source_claims[0].raw)
    assert receipt.status == "stored" and sim._checkpoint(source_claims[0], receipt, False)
    sim.withdraw_original(HUMAN, SAMPLE)
    retirements = sim._claim(2)
    for claim in retirements:
        received = sim.receive_event(claim.raw)
        assert received.status == "retired" and received.payload_absent
        assert sim._checkpoint(claim, received, False)
    data = facts(sim)
    retired = data["events"][retirements[1].event_id]
    assert retired["recipient_admitted"] is True and retired["gapped"] is True
    stream = SOURCE + "/" + RECIPIENT + "/" + OTHER_SCOPE
    assert stream not in data["recipient_heads"]
    assert data["events"][second.event_id]["recipient_admitted"] is False
    before_quota = data["quotas"]
    assert sim.receive_event(late_science).status == "held"
    assert facts(sim)["quotas"] == before_quota and sim.counts()["retained_bytes"] == 0
    assert facts(sim)["events"][first.event_id]["recipient_admitted"] is True


def test_erased_alias_delayed_retirements_fill_only_consecutively_validated_recipient_slots(
    sim: SyntheticExchangeSimulator,
) -> None:
    claims = erased_alias_cleanup_claims(sim)
    receipt = sim.receive_event(claims[1].raw)
    assert sim._checkpoint(claims[1], receipt, False)
    original = json.loads(claims[1].raw)
    value2 = copy.deepcopy(original)
    value2.update(event_id=uid(911), stream_sequence=2, previous_event_sha256=receipt.sha256)
    raw2 = json.dumps(value2, separators=(",", ":")).encode()
    prepared2 = prepare_node_exchange_event(raw2)
    value3 = copy.deepcopy(original)
    value3.update(event_id=uid(912), stream_sequence=3, previous_event_sha256=prepared2.sha256)
    raw3 = json.dumps(value3, separators=(",", ":")).encode()
    stream = SOURCE + "/" + RECIPIENT + "/" + OTHER_SCOPE
    source_before = facts(sim)["source_heads"]
    response3 = sim.receive_event(raw3)
    assert response3.status == "retired" and response3.payload_absent
    assert uid(912) in facts(sim)["events"], "delivered retirement identity was omitted"
    assert facts(sim)["events"][uid(912)]["recipient_admitted"] is True
    assert facts(sim)["events"][uid(912)]["source_admitted"] is False
    assert facts(sim)["recipient_heads"][stream]["stream_sequence"] == 1
    response2 = sim.receive_event(raw2)
    assert response2.status == "retired" and response2.payload_absent
    assert facts(sim)["recipient_heads"][stream]["stream_sequence"] == 3
    assert facts(sim)["source_heads"] == source_before
    assert sim.counts()["retained_bytes"] == 0


def test_erased_alias_invalid_retirement_predecessor_holds_without_corrupting_the_root(
    sim: SyntheticExchangeSimulator,
) -> None:
    claims = erased_alias_cleanup_claims(sim)
    receipt = sim.receive_event(claims[1].raw)
    assert sim._checkpoint(claims[1], receipt, False)
    before = facts(sim)
    invalid = changed(
        claims[1].raw, event_id=uid(913), stream_sequence=2, previous_event_sha256="f" * 64
    )
    response = sim.receive_event(invalid)
    assert response.status in ("conflict", "held") and response.payload_absent is False
    after = facts(reopen(sim))
    for collection in (
        "events",
        "source_slots",
        "recipient_slots",
        "source_heads",
        "recipient_heads",
        "quotas",
    ):
        assert after[collection] == before[collection]
    assert sim.counts()["retained_bytes"] == 0


@pytest.mark.parametrize("capacity", ["slots", "metadata"])
def test_erased_alias_retirement_capacity_refusal_keeps_pending_fence_and_exact_intent(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch, capacity: str
) -> None:
    claims = erased_alias_cleanup_claims(sim)
    before = facts(sim)
    if capacity == "slots":
        monkeypatch.setattr(
            module,
            "MAX_SEQUENCE_SLOTS",
            len(before["source_slots"]) + len(before["recipient_slots"]),
        )
    else:
        monkeypatch.setattr(
            store_module,
            "MAX_METADATA_BYTES",
            len((sim._store.root / "state.json").read_bytes()) + 5,
        )
    response = sim.receive_event(claims[1].raw)
    assert response.status == "held" and response.payload_absent is False
    after = facts(sim)
    assert all(scope["fenced"] and scope["pending_erasure"] for scope in after["scopes"].values())
    for collection in (
        "events",
        "source_slots",
        "recipient_slots",
        "source_heads",
        "recipient_heads",
        "outbox",
        "cleanup",
        "refusals",
        "quotas",
    ):
        assert after[collection] == before[collection]
    assert sim._checkpoint(claims[1], response, False) is False
    monkeypatch.setattr(module, "MAX_SEQUENCE_SLOTS", 10_000)
    monkeypatch.setattr(store_module, "MAX_METADATA_BYTES", 32_000_000)
    assert sim.process_batch(FakeTransport()) == {"claimed": 1, "completed": 1}
    assert sim.counts()["retained_bytes"] == 0 and sim.counts()["fenced_scopes"] == 2
    with pytest.raises(SyntheticExchangeError):
        sim.stage_declaration(OTHER_SCOPE, uid(16), uid(17))


@pytest.mark.parametrize(
    "status",
    [{"cleanup_allowed": False}, {"known": False}, {"connected": False}, {"expired": True}],
)
def test_erased_alias_retirement_needs_fresh_cleanup_authority_before_slot_or_ack(
    sim: SyntheticExchangeSimulator, status: dict[str, bool]
) -> None:
    claims = erased_alias_cleanup_claims(sim)
    sim.set_scope_status(OTHER_SCOPE, **status)
    before = facts(sim)
    response = sim.receive_event(claims[1].raw)
    assert response.status == "held" and response.payload_absent is False
    assert facts(sim) == before
    restored = {key: key not in ("expired",) for key in status}
    sim.set_scope_status(OTHER_SCOPE, revoke=True, **restored)
    response = sim.receive_event(claims[1].raw)
    assert response.status == "retired" and response.payload_absent
    assert facts(sim)["events"][claims[1].event_id]["recipient_admitted"] is True
    assert sim._checkpoint(claims[1], response, False)
    with pytest.raises(SyntheticExchangeError):
        sim.stage_declaration(OTHER_SCOPE, uid(16), uid(17))


def test_multiscope_cleanup_lost_reply_replays_owned_bytes_without_charge_or_missing_slot(
    sim: SyntheticExchangeSimulator,
) -> None:
    stage(sim)
    stage(sim, OTHER_SCOPE)
    sim.process_batch(FakeTransport())
    sim.withdraw_original(HUMAN, SAMPLE)
    assert sim.process_batch(FakeTransport(("deliver", "lose_reply"))) == {
        "claimed": 2,
        "completed": 1,
    }
    data = facts(sim)
    assert len(data["outbox"]) == 1
    event_id = next(iter(data["outbox"]))
    raw = raw_for(sim, event_id)
    assert data["events"][event_id]["recipient_admitted"] is True
    before_slots, before_quota = data["recipient_slots"], data["quotas"]
    sim._clock.now += timedelta(days=1)
    clean = reopen(sim)
    assert raw_for(clean, event_id) == raw
    assert clean.process_batch(FakeTransport()) == {"claimed": 1, "completed": 1}
    assert (
        facts(clean)["recipient_slots"] == before_slots and facts(clean)["quotas"] == before_quota
    )
    assert clean.counts()["retained_bytes"] == clean.counts()["pending_cleanup"] == 0


def test_erased_alias_retirement_without_measurement_refusal_cannot_claim_absence(
    sim: SyntheticExchangeSimulator,
) -> None:
    claims = erased_alias_cleanup_claims(sim)
    receipt = sim.receive_event(claims[1].raw)
    assert sim._checkpoint(claims[1], receipt, False)
    value = json.loads(claims[1].raw)
    value.update(event_id=uid(914), stream_sequence=2, previous_event_sha256=receipt.sha256)
    value["payload"]["measurement_handles"] = [uid(915)]
    before = facts(sim)
    response = sim.receive_event(json.dumps(value, separators=(",", ":")).encode())
    assert response.status == "held" and response.payload_absent is False
    assert facts(sim) == before


def test_erased_alias_cleanup_stale_claim_cannot_finish_a_new_nonce_or_lose_retirement_slot(
    sim: SyntheticExchangeSimulator,
) -> None:
    claims = erased_alias_cleanup_claims(sim)
    old = claims[1]
    response = sim.receive_event(old.raw)
    assert response.status == "retired" and response.payload_absent
    sim._clock.now += timedelta(seconds=CLAIM_RECOVERY_SECONDS)
    assert sim._claim(1) == []
    sim._clock.now += timedelta(seconds=BACKOFF_SECONDS[0])
    new = sim._claim(1)[0]
    assert new.raw == old.raw and new.nonce != old.nonce
    assert sim._checkpoint(old, response, False) is False
    assert facts(sim)["outbox"][old.event_id]["claim"] == new.nonce
    assert sim._checkpoint(new, sim.receive_event(new.raw), False) is True
    assert facts(sim)["events"][old.event_id]["recipient_admitted"] is True
    assert sim.counts()["retained_bytes"] == sim.counts()["pending_cleanup"] == 0


def test_erased_alias_first_retirement_role_admission_still_checks_source_identity(
    sim: SyntheticExchangeSimulator,
) -> None:
    claims = erased_alias_cleanup_claims(sim)
    before = facts(sim)
    assert before["events"][claims[1].event_id]["recipient_admitted"] is False
    response = sim.receive_event(claims[1].raw + b" ")
    assert response.status in ("conflict", "held") and response.payload_absent is False
    after = facts(reopen(sim))
    for collection in (
        "events",
        "source_slots",
        "recipient_slots",
        "source_heads",
        "recipient_heads",
        "outbox",
        "quotas",
    ):
        assert after[collection] == before[collection]


@pytest.mark.parametrize(
    "corruption",
    [
        "all_missing",
        "source_missing",
        "recipient_missing",
        "source_other_stream",
        "recipient_other_stream",
        "both_unknown_stream",
    ],
)
@pytest.mark.parametrize("boundary", ["open", "existing_use", "existing_admission"])
def test_live_binding_coverage_and_reference_stream_hold_corrupt_state(
    sim: SyntheticExchangeSimulator, corruption: str, boundary: str
) -> None:
    original = stage(sim)
    original_raw = raw_for(sim, original.event_id)
    assert sim.receive_event(original_raw).status == "stored"
    assert sim.payload_status(original.event_id) == "available_for_synthetic_simulation"
    root = sim._store.root
    original_image = json.loads((root / "state.json").read_bytes())
    image = copy.deepcopy(original_image)
    bindings = image["data"]["bindings"]
    if corruption == "all_missing":
        bindings.clear()
    elif corruption.endswith("missing"):
        role = corruption.split("_")[0]
        for key in tuple(bindings):
            if bindings[key]["role"] == role:
                del bindings[key]
    else:
        target_role = None if corruption == "both_unknown_stream" else corruption.split("_")[0]
        replacement_stream = (
            "/".join((uid(901), uid(902), uid(903)))
            if target_role is None
            else "/".join((SOURCE, RECIPIENT, OTHER_SCOPE))
        )
        for key in tuple(bindings):
            value = bindings[key]
            if target_role is None or value["role"] == target_role:
                del bindings[key]
                value["stream"] = replacement_stream
                bindings[value["role"] + "/" + replacement_stream + "/" + value["measurement"]] = (
                    value
                )
    assert image["blobs"] == original_image["blobs"]
    assert {key for key in image["data"] if image["data"][key] != original_image["data"][key]} == {
        "bindings"
    }
    (root / "state.json").write_text(json.dumps(image, sort_keys=True, separators=(",", ":")))
    with pytest.raises(SyntheticExchangeError) as error:
        if boundary == "open":
            reopen(sim)
        elif boundary == "existing_use":
            sim.payload_status(original.event_id)
        else:
            wire = json.loads(original_raw)
            wire.update(event_id=uid(910), stream_sequence=1, previous_event_sha256=original.sha256)
            wire["payload"]["measurement"]["mean_rgb"][0] += 0.01
            sim.receive_event(json.dumps(wire, separators=(",", ":")).encode())
    fixed(error)
    # Refusal is not a repair or a successful admission; no quota/head/payload fact
    # is rewritten, and the explicitly controlled fictional corruption remains.
    assert json.loads((root / "state.json").read_bytes()) == image


@pytest.mark.parametrize("draft", [False, True])
def test_source_only_draft_binding_is_required_before_reopen(
    sim: SyntheticExchangeSimulator, draft: bool
) -> None:
    original = stage(sim, draft=draft)
    assert reopen(sim).counts()["queued_declarations"] == 1
    root = sim._store.root
    image = json.loads((root / "state.json").read_bytes())
    assert len(image["data"]["bindings"]) == 1
    image["data"]["bindings"].clear()
    (root / "state.json").write_text(json.dumps(image, sort_keys=True, separators=(",", ":")))
    with pytest.raises(SyntheticExchangeError) as error:
        reopen(sim)
    fixed(error)
    assert image["data"]["events"][original.event_id]["recipient_admitted"] is False


def test_repeated_measurement_shares_complete_binding_and_partial_erasure_keeps_recipient(
    sim: SyntheticExchangeSimulator,
) -> None:
    first, second = stage(sim), stage(sim)
    assert sim.receive_event(raw_for(sim, first.event_id)).status == "stored"
    assert sim.receive_event(raw_for(sim, second.event_id)).status == "stored"
    opened = reopen(sim)
    assert len(facts(opened)["bindings"]) == 2
    assert len(facts(opened)["events"]) == 2
    assert opened.payload_status(first.event_id) == "available_for_synthetic_simulation"
    assert opened.payload_status(second.event_id) == "available_for_synthetic_simulation"
    opened.withdraw_original(HUMAN, SAMPLE)
    partial = facts(reopen(opened))
    assert {value["role"] for value in partial["bindings"].values()} == {"recipient"}
    assert opened.process_batch(FakeTransport())["completed"] == 1
    erased = facts(reopen(opened))
    assert erased["bindings"] == {} and erased["blob_owners"] == {}
    assert erased["source_slots"] and erased["recipient_slots"] and erased["refusals"]


def test_gapped_recipient_binding_and_draft_recovery_remain_complete(
    sim: SyntheticExchangeSimulator,
) -> None:
    first = stage(sim, draft=True)
    second = stage(sim)
    assert sim.receive_event(raw_for(sim, second.event_id)).status == "stored"
    assert facts(sim)["events"][second.event_id]["gapped"] is True
    opened = reopen(sim)
    assert len(facts(opened)["bindings"]) == 2
    assert opened.payload_status(second.event_id) == "held"
    assert opened.receive_event(raw_for(opened, first.event_id)).status == "stored"
    assert reopen(opened).payload_status(second.event_id) == "available_for_synthetic_simulation"


@pytest.mark.parametrize("role", ["source", "recipient"])
def test_live_binding_cannot_reference_equal_aliases_in_another_valid_stream(
    sim: SyntheticExchangeSimulator, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    first = stage(sim)
    first_raw = raw_for(sim, first.event_id)
    parsed = prepare_node_exchange_event(first_raw).event
    assert isinstance(parsed, NodeExchangeDeclaration)
    # Different streams may use the same opaque sample/measurement handles. Force
    # that allowed collision through the ordinary stage API, with distinct event
    # and blob UUIDs, so only the referenced stream guard detects the corruption.
    ids = iter(
        (
            parsed.payload.sample_handle,
            parsed.payload.measurement_handle,
            UUID(uid(920)),
            UUID(uid(921)),
        )
    )
    with monkeypatch.context() as scoped:
        scoped.setattr(module, "uuid4", lambda: next(ids))
        second = stage(sim, OTHER_SCOPE)
    assert sim.receive_event(first_raw).status == "stored"
    assert sim.receive_event(raw_for(sim, second.event_id)).status == "stored"
    assert reopen(sim).counts()["independent_fake_samples"] == 1
    root = sim._store.root
    image = json.loads((root / "state.json").read_bytes())
    first_binding = next(
        value
        for value in image["data"]["bindings"].values()
        if value["role"] == role and value["stream"].endswith("/" + SCOPE)
    )
    second_binding = next(
        value
        for value in image["data"]["bindings"].values()
        if value["role"] == role and value["stream"].endswith("/" + OTHER_SCOPE)
    )
    assert (first_binding["sample"], first_binding["measurement"], first_binding["group"]) == (
        second_binding["sample"],
        second_binding["measurement"],
        second_binding["group"],
    )
    first_binding["blob_id"] = second_binding["blob_id"]
    (root / "state.json").write_text(json.dumps(image, sort_keys=True, separators=(",", ":")))
    with pytest.raises(SyntheticExchangeError) as error:
        reopen(sim)
    fixed(error)
    assert json.loads((root / "state.json").read_bytes()) == image
