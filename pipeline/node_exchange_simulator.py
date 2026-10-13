"""Synthetic-only private exchange. No real authority, transport, field use or publication."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypeVar, cast
from uuid import UUID, uuid4

from pipeline.node_exchange import (
    MAX_NODE_EXCHANGE_SEQUENCE,
    NodeExchangeBinding,
    NodeExchangeDeclaration,
    NodeExchangeHead,
    NodeExchangeRetirement,
    NodeExchangeRetirementAliases,
    NodeExchangeSlot,
    PreparedNodeExchangeEvent,
    advance_node_exchange_head,
    bind_node_exchange_measurement,
    check_node_exchange_identity,
    node_exchange_declaration_covered,
    node_exchange_slot,
    node_exchange_stream,
    prepare_node_exchange_event,
)
from pipeline.node_exchange_store import (
    MAX_RETAINED_BYTES,
    BlobWrite,
    PrivateExchangeSession,
    PrivateExchangeStore,
    StoreSnapshot,
)

MAX_SCOPES = 100
MAX_QUEUED_DECLARATIONS = 1_000
MAX_GAPS_PER_STREAM = 20
MAX_SEQUENCE_SLOTS = 10_000
MAX_REFUSALS = 10_000
MAX_CLEANUP = 1_000
MAX_QUEUED_BYTES = 200_000_000
MAX_DAILY_DECLARATIONS = 100
MAX_BATCH = 20
MAX_ATTEMPTS = 5
BACKOFF_SECONDS = (60, 120, 240, 480)
# A local stopped-claim recovery rule. This is not the imported-photo lease.
CLAIM_RECOVERY_SECONDS = 600
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_VERSION = "gsip-node-exchange-simulator-v1"
_MESSAGE = "synthetic exchange unavailable"
T = TypeVar("T")


class SyntheticExchangeError(ValueError):
    """Fixed generic error; incoming values are never an ordinary error surface."""


def _guard(operation: Callable[[], T]) -> T:
    try:
        return operation()
    except Exception:
        failed = True
    if failed:
        raise SyntheticExchangeError(_MESSAGE)
    raise AssertionError


def _id(value: str | UUID) -> str:
    if isinstance(value, UUID):
        return str(value)
    if type(value) is not str or _UUID.fullmatch(value) is None:
        raise SyntheticExchangeError(_MESSAGE)
    return str(UUID(value))


def _require(condition: bool) -> None:
    if not condition:
        raise SyntheticExchangeError(_MESSAGE)


def _wire(value: dict[str, Any]) -> bytes:
    # This is one Python sender's serialization, never cross-language canonical JSON.
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True, repr=False)
class SyntheticOrigin:
    """Explicit fictional generator inputs; no source file or real declaration importer."""

    human_id: str
    grant_id: str
    sample_id: str
    measurement_id: str
    kind: Literal["camera_rgb", "instrument_reflectance"] = "camera_rgb"
    variant: int = 0
    sealed: bool = False
    synthetic_restricted: bool = False

    def payload(self) -> dict[str, Any]:
        if type(self.variant) is not int or not 0 <= self.variant <= 100:
            raise SyntheticExchangeError(_MESSAGE)
        if type(self.sealed) is not bool or type(self.synthetic_restricted) is not bool:
            raise SyntheticExchangeError(_MESSAGE)
        value = 0.1 + self.variant / 1_000
        digest = hashlib.sha256(b"fictional-synthetic-origin-v1").hexdigest()
        if self.kind == "camera_rgb":
            measurement: dict[str, Any] = {
                "kind": self.kind,
                "source_sha256": digest,
                "device_id": _id(self.measurement_id),
                "extractor_version": "rgb-summary-v1",
                "mean_rgb": [value, 0.2, 0.3],
                "std_rgb": [0.01, 0.01, 0.01],
                "pixel_count": 400,
                "card_present": False,
                "calibration_status": "uncalibrated",
            }
        elif self.kind == "instrument_reflectance":
            measurement = {
                "kind": self.kind,
                "source_sha256": digest,
                "instrument_id": _id(self.measurement_id),
                "calibration_id": _id(self.grant_id),
                "wavelength_nm": [500, 600, 700],
                "reflectance": [value, 0.2, 0.3],
                "uncertainty": [0.01, 0.01, 0.01],
            }
        else:
            raise SyntheticExchangeError(_MESSAGE)
        return {
            "protocol_version": "gsip-capture-v1",
            "context": {"depth_top_cm": 0, "depth_bottom_cm": 10, "condition": "dry"},
            "measurement": measurement,
            "synthetic_claim": self.synthetic_restricted,
        }


@dataclass(frozen=True, repr=False)
class FakeScope:
    source_peer_id: str
    destination_peer_id: str
    scope_id: str
    human_id: str
    active: bool = True
    connected: bool = True
    known: bool = True
    expired: bool = False
    cleanup_allowed: bool = True


@dataclass(frozen=True, repr=False)
class FakeAuthority:
    """Explicit in-process fictional facts. No JSON/file/credential authority adapter."""

    fixture_id: str
    scopes: tuple[FakeScope, ...]
    origins: tuple[SyntheticOrigin, ...]

    def scope(self, scope_id: str) -> FakeScope:
        matched = [scope for scope in self.scopes if _id(scope.scope_id) == scope_id]
        if len(matched) != 1 or type(matched[0]) is not FakeScope:
            raise SyntheticExchangeError(_MESSAGE)
        scope = matched[0]
        for value in (
            scope.active,
            scope.connected,
            scope.known,
            scope.expired,
            scope.cleanup_allowed,
        ):
            if type(value) is not bool:
                raise SyntheticExchangeError(_MESSAGE)
        return scope

    def origin(self, human: str, sample: str, measurement: str) -> SyntheticOrigin:
        matched = [
            origin
            for origin in self.origins
            if (_id(origin.human_id), _id(origin.sample_id), _id(origin.measurement_id))
            == (human, sample, measurement)
        ]
        if len(matched) != 1 or type(matched[0]) is not SyntheticOrigin:
            raise SyntheticExchangeError(_MESSAGE)
        return matched[0]


@dataclass
class FakeClock:
    """Explicit UTC fixture clock; no ambient wall clock or environment lookup."""

    now: datetime

    def seconds(self) -> int:
        if type(self.now) is not datetime or self.now.tzinfo is not UTC:
            raise SyntheticExchangeError(_MESSAGE)
        return int(self.now.timestamp())

    def day(self) -> str:
        self.seconds()
        return self.now.date().isoformat()


@dataclass(frozen=True, repr=False)
class LocalReceipt:
    status: Literal["stored", "already_stored", "retired", "held", "conflict"]
    event_id: str = field(repr=False)
    sha256: str = field(repr=False)
    scope_id: str = field(repr=False)
    sample_handle: str = field(repr=False)
    measurement_handles: tuple[str, ...] = field(default=(), repr=False)
    payload_absent: bool = False


@dataclass(frozen=True, repr=False)
class _Claim:
    event_id: str
    nonce: str
    raw: bytes
    kind: Literal["declare", "retire"]


@dataclass
class FakeTransport:
    """Only scripted local calls, never an injectable HTTP or peer adapter."""

    script: tuple[Literal["deliver", "disconnect", "transient", "lose_reply"], ...] = ()
    _position: int = field(default=0, init=False, repr=False)

    def deliver(self, simulator: SyntheticExchangeSimulator, raw: bytes) -> LocalReceipt | None:
        action = self.script[self._position] if self._position < len(self.script) else "deliver"
        self._position = min(self._position + 1, len(self.script))
        if action == "disconnect":
            return None
        if action == "transient":
            raise _TransientFailure()
        if action not in ("deliver", "lose_reply"):
            raise SyntheticExchangeError(_MESSAGE)
        result = simulator.receive_event(raw)
        if action == "lose_reply":
            raise _TransientFailure()
        return result


class _TransientFailure(Exception):
    pass


_COLLECTIONS = (
    "scopes",
    "origins",
    "measurements",
    "aliases",
    "events",
    "source_slots",
    "recipient_slots",
    "source_heads",
    "recipient_heads",
    "bindings",
    "refusals",
    "outbox",
    "cleanup",
    "blob_owners",
    "quotas",
    "retired_grants",
)


def _fresh(fixture_id: str) -> dict[str, Any]:
    return {"schema_version": _VERSION, "fixture_only": True, "fixture_id": fixture_id} | {
        key: {} for key in _COLLECTIONS
    }


def _stream_key(stream: Sequence[str | UUID]) -> str:
    return "/".join(_id(value) for value in stream)


def _group(human: str, sample: str) -> str:
    return human + "/" + sample


def _slot_dict(slot: NodeExchangeSlot) -> dict[str, Any]:
    return slot.model_dump(mode="json")


def _slot_key(slot: NodeExchangeSlot) -> str:
    return _stream_key(slot.stream) + "/" + str(slot.stream_sequence)


def _validate_fixture(authority: FakeAuthority, clock: FakeClock) -> None:
    if type(authority) is not FakeAuthority or type(clock) is not FakeClock:
        raise SyntheticExchangeError(_MESSAGE)
    _id(authority.fixture_id)
    clock.seconds()
    _require(type(authority.scopes) is tuple and len(authority.scopes) <= MAX_SCOPES)
    _require(type(authority.origins) is tuple and len(authority.origins) <= MAX_SEQUENCE_SLOTS)
    _require(len({_id(scope.scope_id) for scope in authority.scopes}) == len(authority.scopes))
    for scope in authority.scopes:
        _require(type(scope) is FakeScope)
        authority.scope(_id(scope.scope_id))
        for value in (scope.source_peer_id, scope.destination_peer_id, scope.human_id):
            _id(value)
    original_keys = set()
    for origin in authority.origins:
        _require(type(origin) is SyntheticOrigin)
        key = (_id(origin.human_id), _id(origin.sample_id), _id(origin.measurement_id))
        _id(origin.grant_id)
        _require(key not in original_keys)
        original_keys.add(key)
        origin.payload()


class SyntheticExchangeSimulator:
    """One aggregate private root; every supplied fixture remains synthetic/unverified."""

    def __init__(self, store: PrivateExchangeStore, authority: FakeAuthority, clock: FakeClock):
        _guard(lambda: _validate_fixture(authority, clock))
        _require(type(store) is PrivateExchangeStore)
        self._store = store
        self._authority = authority
        self._clock = clock

    @classmethod
    def create(
        cls, root: Path, allowed_root: Path, authority: FakeAuthority, clock: FakeClock
    ) -> SyntheticExchangeSimulator:
        def create() -> SyntheticExchangeSimulator:
            _validate_fixture(authority, clock)
            simulator = cls(
                PrivateExchangeStore.create_designated(root, allowed_root), authority, clock
            )
            with simulator._store.locked() as session:
                snap = session.snapshot()
                session.commit_metadata(_fresh(_id(authority.fixture_id)), snap.generation)
            return simulator

        return _guard(create)

    @classmethod
    def open(
        cls, root: Path, allowed_root: Path, authority: FakeAuthority, clock: FakeClock
    ) -> SyntheticExchangeSimulator:
        def open_store() -> SyntheticExchangeSimulator:
            simulator = cls(
                PrivateExchangeStore.open_designated(root, allowed_root), authority, clock
            )
            with simulator._store.locked() as session:
                simulator._data(session.snapshot())
            return simulator

        return _guard(open_store)

    def _data(self, snap: StoreSnapshot) -> dict[str, Any]:
        data = snap.data
        _require(set(data) == {"schema_version", "fixture_only", "fixture_id", *_COLLECTIONS})
        _require(data["schema_version"] == _VERSION and data["fixture_only"] is True)
        _require(data["fixture_id"] == _id(self._authority.fixture_id))
        _require(all(type(data[key]) is dict for key in _COLLECTIONS))
        for scope_id, scope in data["scopes"].items():
            _require(
                type(scope) is dict
                and set(scope)
                == {
                    "stream",
                    "human",
                    "active",
                    "connected",
                    "known",
                    "expired",
                    "cleanup_allowed",
                    "fenced",
                    "pending_erasure",
                    "conflicted",
                }
            )
            self._scope(data, _id(scope_id))
            _require(
                all(
                    type(scope[key]) is bool
                    for key in (
                        "active",
                        "connected",
                        "known",
                        "expired",
                        "cleanup_allowed",
                        "fenced",
                        "pending_erasure",
                        "conflicted",
                    )
                )
            )
            _require(not scope["pending_erasure"] or scope["fenced"])
        for key, group in data["origins"].items():
            _require(
                type(group) is dict
                and set(group) == {"human", "sample", "grant", "withdrawn", "sealed", "synthetic"}
            )
            _require(key == _group(_id(group["human"]), _id(group["sample"])))
            _id(group["grant"])
            _require(
                all(type(group[field]) is bool for field in ("withdrawn", "sealed", "synthetic"))
            )
        for key, group_key in data["measurements"].items():
            human, measurement = key.split("/")
            _id(measurement)
            _require(
                group_key in data["origins"] and data["origins"][group_key]["human"] == _id(human)
            )
        sample_aliases: set[tuple[str, str]] = set()
        measurement_aliases: set[tuple[str, str]] = set()
        for key, alias in data["aliases"].items():
            _require(
                type(alias) is dict and set(alias) == {"group", "stream", "sample", "measurements"}
            )
            _require(
                alias["group"] in data["origins"] and key == alias["stream"] + "/" + alias["group"]
            )
            stream_ids = alias["stream"].split("/")
            _require(len(stream_ids) == 3)
            scope_facts = self._scope(data, stream_ids[2])
            _require(
                scope_facts["stream"] == stream_ids
                and scope_facts["human"] == data["origins"][alias["group"]]["human"]
            )
            _id(alias["sample"])
            _require((alias["stream"], alias["sample"]) not in sample_aliases)
            sample_aliases.add((alias["stream"], alias["sample"]))
            _require(type(alias["measurements"]) is dict and bool(alias["measurements"]))
            _require(len(set(alias["measurements"].values())) == len(alias["measurements"]))
            for original, handle in alias["measurements"].items():
                _id(original)
                _id(handle)
                _require((alias["stream"], handle) not in measurement_aliases)
                measurement_aliases.add((alias["stream"], handle))
                _require(
                    data["measurements"].get(
                        data["origins"][alias["group"]]["human"] + "/" + original
                    )
                    == alias["group"]
                )
        for key, refusal in data["refusals"].items():
            parsed = NodeExchangeRetirementAliases.model_validate(refusal)
            scope_facts = self._scope(data, str(parsed.stream[2]))
            _require(scope_facts["stream"] == [str(value) for value in parsed.stream])
            prefix = _stream_key(parsed.stream)
            expected = prefix + "/sample/" + str(parsed.sample_handle)
            if parsed.measurement_handles:
                _require(len(parsed.measurement_handles) == 1)
                expected = prefix + "/measurement/" + str(parsed.measurement_handles[0])
            _require(key == expected)
        for role in ("source_slots", "recipient_slots"):
            for key, value in data[role].items():
                slot = NodeExchangeSlot.model_validate(value)
                event = data["events"].get(str(slot.event_id))
                _require(key == _slot_key(slot) and event is not None and event["slot"] == value)
        for event_id, event in data["events"].items():
            _require(
                type(event) is dict
                and set(event)
                == {
                    "slot",
                    "kind",
                    "scope",
                    "sample",
                    "measurement",
                    "group",
                    "source_admitted",
                    "recipient_admitted",
                    "source_day",
                    "recipient_day",
                    "source_blob",
                    "recipient_blob",
                    "gapped",
                }
            )
            slot = NodeExchangeSlot.model_validate(event["slot"])
            _require(event_id == str(slot.event_id))
            _require(event["scope"] == str(slot.stream[2]) and event["scope"] in data["scopes"])
            _require(event["group"] in data["origins"] and event["kind"] in ("declare", "retire"))
            _require(
                data["scopes"][event["scope"]]["stream"] == [str(value) for value in slot.stream]
            )
            _require(
                data["scopes"][event["scope"]]["human"] == data["origins"][event["group"]]["human"]
            )
            _id(event["sample"])
            _require(type(event["gapped"]) is bool)
            if event["kind"] == "retire":
                _require(event["measurement"] is None)
            else:
                _require(_id(event["measurement"]) == event["measurement"])
            for role in ("source", "recipient"):
                _require(type(event[role + "_admitted"]) is bool)
                if event[role + "_admitted"]:
                    _require(data[role + "_slots"].get(_slot_key(slot)) == event["slot"])
                blob = event[role + "_blob"]
                _require(
                    blob is None or (event[role + "_admitted"] and blob in data["blob_owners"])
                )
                day = event[role + "_day"]
                if not event[role + "_admitted"] or event["kind"] == "retire":
                    _require(day is None)
                else:
                    _require(
                        type(day) is str and datetime.fromisoformat(day).date().isoformat() == day
                    )
        for key, flag in data["retired_grants"].items():
            human, grant = key.split("/")
            _id(human)
            _id(grant)
            _require(flag is True)
        computed_quotas: dict[str, int] = {}
        for event in data["events"].values():
            for role in ("source", "recipient"):
                if event["kind"] == "declare" and event[role + "_admitted"]:
                    key = (
                        role
                        + "/"
                        + data["origins"][event["group"]]["human"]
                        + "/"
                        + event[role + "_day"]
                    )
                    computed_quotas[key] = computed_quotas.get(key, 0) + 1
        _require(
            data["quotas"] == computed_quotas
            and all(0 < value <= MAX_DAILY_DECLARATIONS for value in computed_quotas.values())
        )
        for event_id, item in data["outbox"].items():
            _require(
                type(item) is dict
                and set(item)
                == {
                    "kind",
                    "blob_id",
                    "draft",
                    "attempts",
                    "ready_at",
                    "claim",
                    "claim_until",
                    "held",
                }
            )
            _require(
                event_id in data["events"]
                and item["kind"] == data["events"][event_id]["kind"]
                and item["blob_id"] == data["events"][event_id]["source_blob"]
            )
            _require(all(type(item[key]) is bool for key in ("draft", "held")))
            _require(
                type(item["attempts"]) is int
                and 0 <= item["attempts"] <= MAX_ATTEMPTS
                and type(item["ready_at"]) is int
            )
            if item["claim"] is None:
                _require(item["claim_until"] is None)
            else:
                _require(_id(item["claim"]) == item["claim"] and type(item["claim_until"]) is int)
        references: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for event in data["events"].values():
            for role in ("source", "recipient"):
                blob = event[role + "_blob"]
                if blob is not None:
                    references.setdefault(blob, []).append((role, event))
        for blob_id, owner in data["blob_owners"].items():
            _require(type(owner) is dict and set(owner) == {"group", "scope", "sample", "science"})
            _require(
                owner["group"] in data["origins"]
                and owner["scope"] in data["scopes"]
                and type(owner["science"]) is bool
            )
            _id(owner["sample"])
            _require(blob_id in snap.blobs)
            ref = snap.blobs[blob_id]
            linked = references.get(blob_id, [])
            if ref.category == "preparation":
                _require(owner["science"] and not linked)
                _require(
                    any(
                        (event["group"], event["scope"], event["sample"])
                        == (owner["group"], owner["scope"], owner["sample"])
                        for event in data["events"].values()
                    )
                )
            else:
                _require(len(linked) == 1)
                role, event = linked[0]
                _require(
                    ref.category in ("source", "draft")
                    if role == "source"
                    else ref.category == "recipient"
                )
                _require(
                    (owner["group"], owner["scope"], owner["sample"])
                    == (event["group"], event["scope"], event["sample"])
                )
                _require(owner["science"] == (event["kind"] == "declare"))
        _require(set(snap.blobs) == set(data["blob_owners"]))
        expected_binding_keys = {
            role + "/" + _stream_key(event["slot"]["stream"]) + "/" + event["measurement"]
            for event in data["events"].values()
            if event["kind"] == "declare"
            for role in ("source", "recipient")
            if event[role + "_blob"] is not None
        }
        # The binding map is an index over complete retained declaration facts,
        # never optional caller authority. Repeats share one key; erased roles
        # retain slot/digest facts without retaining a scientific binding.
        _require(set(data["bindings"]) == expected_binding_keys)
        for key, binding in data["bindings"].items():
            _require(
                type(binding) is dict
                and set(binding) == {"role", "stream", "sample", "measurement", "group", "blob_id"}
            )
            _require(
                binding["role"] in ("source", "recipient")
                and binding["group"] in data["origins"]
                and binding["blob_id"] in data["blob_owners"]
            )
            _require(
                key == binding["role"] + "/" + binding["stream"] + "/" + _id(binding["measurement"])
            )
            _id(binding["sample"])
            linked = references.get(binding["blob_id"], [])
            _require(len(linked) == 1)
            role, event = linked[0]
            _require(binding["stream"] == _stream_key(event["slot"]["stream"]))
            _require(
                (role, event["kind"], event["group"], event["sample"], event["measurement"])
                == (
                    binding["role"],
                    "declare",
                    binding["group"],
                    binding["sample"],
                    binding["measurement"],
                )
            )
        for key, cleanup in data["cleanup"].items():
            _require(
                type(cleanup) is dict
                and set(cleanup) == {"fields", "group", "complete"}
                and cleanup["complete"] is False
            )
            prepared = prepare_node_exchange_event(_wire(cleanup["fields"]))
            _require(isinstance(prepared.event, NodeExchangeRetirement))
            _require(
                key
                == _stream_key(node_exchange_stream(prepared.event))
                + "/"
                + str(prepared.event.payload.sample_handle)
            )
            _require(
                cleanup["group"] in data["origins"]
                and data["origins"][cleanup["group"]]["withdrawn"]
            )
            _require(
                data["events"][str(prepared.event.event_id)]["slot"]
                == _slot_dict(node_exchange_slot(prepared))
            )
        for role in ("source", "recipient"):
            for key, raw_head in data[role + "_heads"].items():
                ids = key.split("/")
                _require(len(ids) == 3 and self._scope(data, ids[2])["stream"] == ids)
                parsed_head = NodeExchangeHead.model_validate(raw_head)
                slot = data[role + "_slots"].get(key + "/" + str(parsed_head.stream_sequence))
                _require(slot is not None and slot["sha256"] == parsed_head.sha256)
        # A head is derived from this role's admitted facts, never the other role.
        for role in ("source", "recipient"):
            facts = [
                NodeExchangeSlot.model_validate(value) for value in data[role + "_slots"].values()
            ]
            for scope in data["scopes"].values():
                if scope["conflicted"]:
                    continue
                stream = _stream_key(scope["stream"])
                ids = scope["stream"]
                computed = advance_node_exchange_head(
                    (UUID(ids[0]), UUID(ids[1]), UUID(ids[2])), None, facts
                )
                expected_head = (
                    None if computed.head is None else computed.head.model_dump(mode="json")
                )
                _require(data[role + "_heads"].get(stream) == expected_head)
                if role == "recipient":
                    sequence = -1 if computed.head is None else computed.head.stream_sequence
                    for event in data["events"].values():
                        if event["recipient_admitted"] and event["scope"] == ids[2]:
                            _require(
                                event["gapped"] == (event["slot"]["stream_sequence"] > sequence)
                            )
        self._capacities(data, snap, incoming_bytes=0)
        return copy.deepcopy(data)

    def _load(self, session: PrivateExchangeSession) -> tuple[StoreSnapshot, dict[str, Any]]:
        snap = session.snapshot()
        data = self._data(snap)
        changed = False
        for group in data["origins"].values():
            if (
                group["human"] + "/" + group["grant"] in data["retired_grants"]
                and not group["withdrawn"]
            ):
                group["withdrawn"] = True
                changed = True
            _, sealed, synthetic = self._sample_facts(group["human"], group["sample"])
            for restriction, extra in (("sealed", sealed), ("synthetic", synthetic)):
                if extra and not group[restriction]:
                    group[restriction] = True
                    changed = True
        if changed:
            snap = session.commit_metadata(data, snap.generation)
        # Canonical restrictions already survived. Finish only registered source
        # science before further admission or any cleanup claim.
        for key, group in tuple(data["origins"].items()):
            if group["withdrawn"]:
                aliases = [value for value in data["aliases"].values() if value["group"] == key]
                candidate = copy.deepcopy(data)
                altered = False
                scopes = sorted({alias["stream"].split("/")[2] for alias in aliases})
                try:
                    for alias in aliases:
                        scope = data["scopes"][alias["stream"].split("/")[2]]
                        if scope["fenced"] and scope["pending_erasure"]:
                            continue
                        cleanup_key = alias["stream"] + "/" + alias["sample"]
                        if cleanup_key not in candidate["cleanup"]:
                            self._refuse_alias(candidate, alias)
                            fields = self._cleanup_fields(candidate, alias)
                            candidate["cleanup"][cleanup_key] = {
                                "fields": fields,
                                "group": key,
                                "complete": False,
                            }
                            altered = True
                    self._capacities(candidate, snap, 0)
                    if altered:
                        snap = session.commit_metadata(candidate, snap.generation)
                except ValueError:
                    self._fence(session, snap, data, scopes)
                    snap = session.snapshot()
                    data = self._data(snap)
                else:
                    if altered:
                        data = self._data(snap)
                snap = self._erase_owned(session, snap, data, key, source_only=True)
                data = self._data(snap)
        return snap, data

    def _sample_facts(self, human: str, sample: str) -> tuple[set[str], bool, bool]:
        """Complete current canonical facts for one original fake human/sample only."""
        current = [
            origin
            for origin in self._authority.origins
            if (_id(origin.human_id), _id(origin.sample_id)) == (human, sample)
        ]
        return (
            {_id(origin.grant_id) for origin in current},
            any(origin.sealed for origin in current),
            any(origin.synthetic_restricted for origin in current),
        )

    def _group_allowed(self, group: dict[str, Any]) -> bool:
        grants, _, _ = self._sample_facts(group["human"], group["sample"])
        return bool(not group["withdrawn"] and not group["sealed"] and grants == {group["grant"]})

    def _measurement_allowed(self, data: dict[str, Any], event: dict[str, Any]) -> bool:
        """Resolve the immutable scoped handle to this exact current fictional original."""
        if event["kind"] != "declare":
            return False
        group = data["origins"][event["group"]]
        if not self._group_allowed(group):
            return False
        stream = _stream_key(event["slot"]["stream"])
        alias = data["aliases"].get(stream + "/" + event["group"])
        if alias is None or alias["sample"] != event["sample"]:
            return False
        originals = [
            original
            for original, handle in alias["measurements"].items()
            if handle == event["measurement"]
        ]
        if len(originals) != 1:
            return False
        return any(
            (
                _id(origin.human_id),
                _id(origin.sample_id),
                _id(origin.measurement_id),
                _id(origin.grant_id),
            )
            == (group["human"], group["sample"], originals[0], group["grant"])
            for origin in self._authority.origins
        )

    def _scope(self, data: dict[str, Any], scope_id: str) -> dict[str, Any]:
        configured = self._authority.scope(scope_id)
        facts = data["scopes"].get(scope_id)
        expected = [
            _id(configured.source_peer_id),
            _id(configured.destination_peer_id),
            scope_id,
        ]
        if (
            facts is None
            or facts["stream"] != expected
            or facts["human"] != _id(configured.human_id)
        ):
            raise SyntheticExchangeError(_MESSAGE)
        return cast(dict[str, Any], facts)

    def _allowed(self, facts: dict[str, Any], cleanup: bool = False) -> bool:
        configured = self._authority.scope(facts["stream"][2])
        current = (
            facts["known"]
            and facts["connected"]
            and not facts["expired"]
            and configured.known
            and configured.connected
            and not configured.expired
        )
        if cleanup:
            return bool(current and facts["cleanup_allowed"] and configured.cleanup_allowed)
        return bool(
            current
            and facts["active"]
            and configured.active
            and not facts["fenced"]
            and not facts["conflicted"]
        )

    def enroll_scope(self, scope_id: str | UUID) -> bool:
        def enroll() -> bool:
            normalized = _id(scope_id)
            configured = self._authority.scope(normalized)
            if not configured.known:
                raise SyntheticExchangeError(_MESSAGE)
            with self._store.locked() as session:
                snap, data = self._load(session)
                if normalized in data["scopes"]:
                    self._scope(data, normalized)
                    return False
                if len(data["scopes"]) >= MAX_SCOPES or any(
                    scope["human"] == _id(configured.human_id) and scope["fenced"]
                    for scope in data["scopes"].values()
                ):
                    raise SyntheticExchangeError(_MESSAGE)
                data["scopes"][normalized] = {
                    "stream": [
                        _id(configured.source_peer_id),
                        _id(configured.destination_peer_id),
                        normalized,
                    ],
                    "human": _id(configured.human_id),
                    "active": configured.active,
                    "connected": configured.connected,
                    "known": configured.known,
                    "expired": configured.expired,
                    "cleanup_allowed": configured.cleanup_allowed,
                    # Both false representations are already longer than active true.
                    "fenced": False,
                    "pending_erasure": False,
                    "conflicted": False,
                }
                session.commit_metadata(data, snap.generation)
                return True

        return _guard(enroll)

    def set_scope_status(
        self,
        scope_id: str | UUID,
        *,
        connected: bool | None = None,
        known: bool | None = None,
        expired: bool | None = None,
        cleanup_allowed: bool | None = None,
        revoke: bool = False,
    ) -> None:
        def update() -> None:
            if type(revoke) is not bool:
                raise SyntheticExchangeError(_MESSAGE)
            with self._store.locked() as session:
                snap, data = self._load(session)
                facts = self._scope(data, _id(scope_id))
                for key, value in (
                    ("connected", connected),
                    ("known", known),
                    ("expired", expired),
                    ("cleanup_allowed", cleanup_allowed),
                ):
                    if value is not None:
                        if type(value) is not bool:
                            raise SyntheticExchangeError(_MESSAGE)
                        facts[key] = value
                if revoke:
                    facts["active"] = False
                session.commit_metadata(data, snap.generation)

        _guard(update)

    def _capacities(self, data: dict[str, Any], snap: StoreSnapshot, incoming_bytes: int) -> None:
        declarations = sum(item["kind"] == "declare" for item in data["outbox"].values())
        queued_ids = {
            item["blob_id"] for item in data["outbox"].values() if item["blob_id"] is not None
        }
        gaps: dict[str, int] = {}
        for event in data["events"].values():
            if event["recipient_admitted"] and event["kind"] == "declare" and event["gapped"]:
                declarations += 1
                if event["recipient_blob"] is not None:
                    queued_ids.add(event["recipient_blob"])
                stream = _stream_key(event["slot"]["stream"])
                gaps[stream] = gaps.get(stream, 0) + 1
        queued_bytes = sum(snap.blobs[key].byte_count for key in queued_ids if key in snap.blobs)
        if (
            len(data["scopes"]) > MAX_SCOPES
            or declarations > MAX_QUEUED_DECLARATIONS
            or any(count > MAX_GAPS_PER_STREAM for count in gaps.values())
            or len(data["source_slots"]) + len(data["recipient_slots"]) > MAX_SEQUENCE_SLOTS
            or len(data["refusals"]) > MAX_REFUSALS
            or sum(not item["complete"] for item in data["cleanup"].values()) > MAX_CLEANUP
            or queued_bytes + incoming_bytes > MAX_QUEUED_BYTES
            or sum(ref.byte_count for ref in snap.blobs.values()) + incoming_bytes
            > MAX_RETAINED_BYTES
        ):
            raise SyntheticExchangeError(_MESSAGE)

    def _charge(self, data: dict[str, Any], human: str, role: str) -> str:
        day = self._clock.day()
        key = role + "/" + human + "/" + day
        charge = data["quotas"].get(key, 0)
        if type(charge) is not int or charge >= MAX_DAILY_DECLARATIONS:
            raise SyntheticExchangeError(_MESSAGE)
        data["quotas"][key] = charge + 1
        return day

    def _facts(self, data: dict[str, Any]) -> list[NodeExchangeSlot]:
        return [NodeExchangeSlot.model_validate(event["slot"]) for event in data["events"].values()]

    def _prior_bindings(
        self,
        session: PrivateExchangeSession,
        data: dict[str, Any],
        role: str,
        event: NodeExchangeDeclaration,
    ) -> list[NodeExchangeBinding]:
        result = []
        stream = _stream_key(node_exchange_stream(event))
        for value in data["bindings"].values():
            if value["stream"] != stream or value["measurement"] != str(
                event.payload.measurement_handle
            ):
                continue
            prepared = prepare_node_exchange_event(session.read_blob(value["blob_id"]))
            if not isinstance(prepared.event, NodeExchangeDeclaration):
                raise SyntheticExchangeError(_MESSAGE)
            original_event = data["events"].get(str(prepared.event.event_id))
            if original_event is None or original_event["slot"] != _slot_dict(
                node_exchange_slot(prepared)
            ):
                raise SyntheticExchangeError(_MESSAGE)
            binding = bind_node_exchange_measurement(prepared.event, ())
            group = data["origins"][value["group"]]
            result.append(
                NodeExchangeBinding.model_validate(
                    binding.model_copy(
                        update={
                            "synthetic_restricted": binding.synthetic_restricted
                            or group["synthetic"]
                        }
                    )
                )
            )
        return result

    def _head(self, data: dict[str, Any], role: str, stream: str) -> NodeExchangeHead | None:
        raw = data[role + "_heads"].get(stream)
        return None if raw is None else NodeExchangeHead.model_validate(raw)

    def _advance(self, data: dict[str, Any], role: str, stream: str) -> None:
        facts = [NodeExchangeSlot.model_validate(value) for value in data[role + "_slots"].values()]
        parts = stream.split("/")
        result = advance_node_exchange_head(
            (UUID(parts[0]), UUID(parts[1]), UUID(parts[2])), self._head(data, role, stream), facts
        )
        if result.head is not None:
            data[role + "_heads"][stream] = result.head.model_dump(mode="json")
        if role == "recipient":
            sequence = -1 if result.head is None else result.head.stream_sequence
            for event in data["events"].values():
                if _stream_key(event["slot"]["stream"]) == stream and event["recipient_admitted"]:
                    event["gapped"] = event["slot"]["stream_sequence"] > sequence

    def _event(self, prepared: PreparedNodeExchangeEvent, group: str) -> dict[str, Any]:
        event = prepared.event
        return {
            "slot": _slot_dict(node_exchange_slot(prepared)),
            "kind": event.kind,
            "scope": str(event.scope_id),
            "sample": str(event.payload.sample_handle),
            "measurement": str(event.payload.measurement_handle)
            if isinstance(event, NodeExchangeDeclaration)
            else None,
            "group": group,
            "source_admitted": False,
            "recipient_admitted": False,
            "source_day": None,
            "recipient_day": None,
            "source_blob": None,
            "recipient_blob": None,
            "gapped": False,
        }

    def _receipt(
        self, prepared: PreparedNodeExchangeEvent, status: Any, absent: bool = False
    ) -> LocalReceipt:
        event = prepared.event
        handles = (
            tuple(str(value) for value in event.payload.measurement_handles)
            if isinstance(event, NodeExchangeRetirement)
            else ()
        )
        return LocalReceipt(
            status,
            str(event.event_id),
            prepared.sha256,
            str(event.scope_id),
            str(event.payload.sample_handle),
            handles,
            absent,
        )

    def stage_declaration(
        self,
        scope_id: str | UUID,
        sample_id: str | UUID,
        measurement_id: str | UUID,
        *,
        draft: bool = False,
    ) -> LocalReceipt:
        def stage() -> LocalReceipt:
            if type(draft) is not bool:
                raise SyntheticExchangeError(_MESSAGE)
            with self._store.locked() as session:
                snap, data = self._load(session)
                facts = self._scope(data, _id(scope_id))
                if not self._allowed(facts):
                    raise SyntheticExchangeError(_MESSAGE)
                group_key = _group(facts["human"], _id(sample_id))
                grants, sealed, synthetic = self._sample_facts(facts["human"], _id(sample_id))
                if len(grants) != 1:
                    # There is no unambiguous grant for a new restriction row.
                    # Preserve known restrictions without choosing a sibling's grant.
                    if group_key not in data["origins"] and (sealed or synthetic):
                        scopes = [
                            key
                            for key, value in data["scopes"].items()
                            if value["human"] == facts["human"]
                        ]
                        self._fence(session, snap, data, scopes)
                    raise SyntheticExchangeError(_MESSAGE)
                canonical_grant = next(iter(grants))
                group = data["origins"].setdefault(
                    group_key,
                    {
                        "human": facts["human"],
                        "sample": _id(sample_id),
                        "grant": canonical_grant,
                        "withdrawn": facts["human"] + "/" + canonical_grant
                        in data["retired_grants"],
                        "sealed": sealed,
                        "synthetic": synthetic,
                    },
                )
                if group["grant"] != canonical_grant:
                    raise SyntheticExchangeError(_MESSAGE)
                group["sealed"] = group["sealed"] or sealed
                group["synthetic"] = group["synthetic"] or synthetic
                if group_key not in snap.data["origins"] and (
                    group["sealed"] or group["synthetic"] or group["withdrawn"]
                ):
                    # A later admission/quota/capacity refusal must not discard
                    # an already known canonical restriction on this original.
                    try:
                        snap = session.commit_metadata(data, snap.generation)
                    except ValueError:
                        fallback = self._data(snap)
                        scopes = [
                            key
                            for key, value in fallback["scopes"].items()
                            if value["human"] == facts["human"]
                        ]
                        self._fence(session, snap, fallback, scopes)
                        raise SyntheticExchangeError(_MESSAGE) from None
                    data = self._data(snap)
                    group = data["origins"][group_key]
                if not self._group_allowed(group):
                    raise SyntheticExchangeError(_MESSAGE)
                origin = self._authority.origin(facts["human"], _id(sample_id), _id(measurement_id))
                measurement_key = facts["human"] + "/" + _id(measurement_id)
                if data["measurements"].setdefault(measurement_key, group_key) != group_key:
                    raise SyntheticExchangeError(_MESSAGE)
                stream = _stream_key(facts["stream"])
                alias_key = stream + "/" + group_key
                alias = data["aliases"].setdefault(
                    alias_key,
                    {
                        "group": group_key,
                        "stream": stream,
                        "sample": str(uuid4()),
                        "measurements": {},
                    },
                )
                measurement = alias["measurements"].setdefault(_id(measurement_id), str(uuid4()))
                # UUID randomness does not authorize reuse of another live or
                # permanently refused scoped identity.
                sample_owners = [
                    value
                    for value in data["aliases"].values()
                    if value["stream"] == stream and value["sample"] == alias["sample"]
                ]
                _require(len(sample_owners) == 1 and sample_owners[0]["group"] == group_key)
                measurement_owners = [
                    (value["group"], original)
                    for value in data["aliases"].values()
                    if value["stream"] == stream
                    for original, handle in value["measurements"].items()
                    if handle == measurement
                ]
                _require(measurement_owners == [(group_key, _id(measurement_id))])
                _require(stream + "/sample/" + alias["sample"] not in data["refusals"])
                _require(stream + "/measurement/" + measurement not in data["refusals"])
                head = self._head(data, "source", stream)
                sequence = 0 if head is None else head.stream_sequence + 1
                if sequence > MAX_NODE_EXCHANGE_SEQUENCE:
                    raise SyntheticExchangeError(_MESSAGE)
                payload = (
                    origin.payload()
                    | {"synthetic_claim": group["synthetic"]}
                    | {
                        "sample_handle": alias["sample"],
                        "measurement_handle": measurement,
                    }
                )
                raw = _wire(
                    {
                        "schema_version": "gsip-node-exchange-v1",
                        "event_id": str(uuid4()),
                        "source_peer_id": facts["stream"][0],
                        "destination_peer_id": facts["stream"][1],
                        "scope_id": facts["stream"][2],
                        "stream_sequence": sequence,
                        "previous_event_sha256": None if head is None else head.sha256,
                        "kind": "declare",
                        "payload": payload,
                    }
                )
                prepared = prepare_node_exchange_event(raw)
                if not isinstance(prepared.event, NodeExchangeDeclaration):
                    raise SyntheticExchangeError(_MESSAGE)
                bind_node_exchange_measurement(
                    prepared.event, self._prior_bindings(session, data, "source", prepared.event)
                )
                slot = node_exchange_slot(prepared)
                check_node_exchange_identity(slot, self._facts(data))
                event_id = str(prepared.event.event_id)
                blob_id = str(uuid4())
                event = self._event(prepared, group_key)
                event.update(
                    source_admitted=True,
                    source_day=self._charge(data, facts["human"], "source"),
                    source_blob=blob_id,
                )
                data["events"][event_id] = event
                data["source_slots"][_slot_key(slot)] = event["slot"]
                data["blob_owners"][blob_id] = {
                    "group": group_key,
                    "scope": str(prepared.event.scope_id),
                    "sample": alias["sample"],
                    "science": True,
                }
                data["bindings"]["source/" + stream + "/" + measurement] = {
                    "role": "source",
                    "stream": stream,
                    "sample": alias["sample"],
                    "measurement": measurement,
                    "group": group_key,
                    "blob_id": blob_id,
                }
                data["outbox"][event_id] = {
                    "kind": "declare",
                    "blob_id": blob_id,
                    "draft": draft,
                    "attempts": 0,
                    "ready_at": self._clock.seconds(),
                    "claim": None,
                    "claim_until": None,
                    "held": False,
                }
                self._advance(data, "source", stream)
                self._capacities(data, snap, len(raw))
                session.put_blob(
                    data, BlobWrite(blob_id, "draft" if draft else "source", raw), snap.generation
                )
                return self._receipt(prepared, "stored")

        return _guard(stage)

    def queue_draft(self, event_id: str | UUID) -> None:
        def queue() -> None:
            with self._store.locked() as session:
                snap, data = self._load(session)
                event = data["events"][_id(event_id)]
                facts = self._scope(data, event["scope"])
                if not self._allowed(facts) or not self._measurement_allowed(data, event):
                    raise SyntheticExchangeError(_MESSAGE)
                item = data["outbox"][_id(event_id)]
                prepare_node_exchange_event(session.read_blob(item["blob_id"]))
                item["draft"] = False
                session.commit_metadata(data, snap.generation)

        _guard(queue)

    def _alias_for_event(
        self, data: dict[str, Any], prepared: PreparedNodeExchangeEvent
    ) -> dict[str, Any]:
        stream = _stream_key(node_exchange_stream(prepared.event))
        sample = str(prepared.event.payload.sample_handle)
        matches = [
            alias
            for alias in data["aliases"].values()
            if alias["stream"] == stream and alias["sample"] == sample
        ]
        if len(matches) != 1:
            raise SyntheticExchangeError(_MESSAGE)
        alias = matches[0]
        if isinstance(prepared.event, NodeExchangeDeclaration):
            if str(prepared.event.payload.measurement_handle) not in alias["measurements"].values():
                raise SyntheticExchangeError(_MESSAGE)
        else:
            if not set(str(value) for value in prepared.event.payload.measurement_handles).issubset(
                alias["measurements"].values()
            ):
                raise SyntheticExchangeError(_MESSAGE)
        return cast(dict[str, Any], alias)

    def receive_event(self, raw: bytes) -> LocalReceipt:
        def receive() -> LocalReceipt:
            prepared = prepare_node_exchange_event(raw)
            if isinstance(prepared.event, NodeExchangeRetirement):
                return self._receive_retirement(prepared)
            with self._store.locked() as session:
                snap, data = self._load(session)
                facts = self._scope(data, str(prepared.event.scope_id))
                if facts["stream"] != [
                    str(value) for value in node_exchange_stream(prepared.event)
                ] or not self._allowed(facts):
                    return self._receipt(prepared, "held")
                refusals = [
                    NodeExchangeRetirementAliases.model_validate(value)
                    for value in data["refusals"].values()
                ]
                if node_exchange_declaration_covered(prepared.event, refusals):
                    return self._receipt(prepared, "held")
                alias = self._alias_for_event(data, prepared)
                group = data["origins"][alias["group"]]
                if not self._measurement_allowed(data, self._event(prepared, alias["group"])):
                    return self._receipt(prepared, "held")
                slot = node_exchange_slot(prepared)
                try:
                    check_node_exchange_identity(slot, self._facts(data))
                    bind_node_exchange_measurement(
                        prepared.event,
                        self._prior_bindings(session, data, "recipient", prepared.event),
                    )
                except ValueError:
                    facts["conflicted"] = True
                    session.commit_metadata(data, snap.generation)
                    return self._receipt(prepared, "conflict")
                event_id = str(prepared.event.event_id)
                if event_id in data["events"] and data["events"][event_id]["recipient_admitted"]:
                    event = data["events"][event_id]
                    if event["recipient_blob"] is None:
                        return self._receipt(prepared, "held")
                    own = prepare_node_exchange_event(session.read_blob(event["recipient_blob"]))
                    if own.original_bytes != prepared.original_bytes:
                        raise SyntheticExchangeError(_MESSAGE)
                    return self._receipt(prepared, "already_stored")
                event = data["events"].setdefault(event_id, self._event(prepared, alias["group"]))
                blob_id = str(uuid4())
                event.update(
                    recipient_admitted=True,
                    recipient_day=self._charge(data, facts["human"], "recipient"),
                    recipient_blob=blob_id,
                )
                data["recipient_slots"][_slot_key(slot)] = event["slot"]
                stream = _stream_key(slot.stream)
                try:
                    self._advance(data, "recipient", stream)
                except ValueError:
                    facts["conflicted"] = True
                    original = self._data(snap)
                    original["scopes"][str(prepared.event.scope_id)]["conflicted"] = True
                    session.commit_metadata(original, snap.generation)
                    return self._receipt(prepared, "conflict")
                group["synthetic"] = group["synthetic"] or prepared.event.payload.synthetic_claim
                data["bindings"][
                    "recipient/" + stream + "/" + str(prepared.event.payload.measurement_handle)
                ] = {
                    "role": "recipient",
                    "stream": stream,
                    "sample": str(prepared.event.payload.sample_handle),
                    "measurement": str(prepared.event.payload.measurement_handle),
                    "group": alias["group"],
                    "blob_id": blob_id,
                }
                data["blob_owners"][blob_id] = {
                    "group": alias["group"],
                    "scope": str(prepared.event.scope_id),
                    "sample": alias["sample"],
                    "science": True,
                }
                self._capacities(data, snap, len(prepared.original_bytes))
                session.put_blob(
                    data, BlobWrite(blob_id, "recipient", prepared.original_bytes), snap.generation
                )
                return self._receipt(prepared, "stored")

        return _guard(receive)

    def _fence(
        self,
        session: PrivateExchangeSession,
        snap: StoreSnapshot,
        data: dict[str, Any],
        scopes: Sequence[str],
    ) -> None:
        # No reserved record means no durable fallback, hence no successful acknowledgment.
        _require(bool(scopes))
        for scope in scopes:
            data["scopes"][scope]["fenced"] = True
            data["scopes"][scope]["pending_erasure"] = True
        session.commit_metadata(data, snap.generation)

    def _refuse_alias(self, data: dict[str, Any], alias: dict[str, Any]) -> None:
        stream = alias["stream"]
        handles = tuple(alias["measurements"].values())
        data["refusals"][stream + "/sample/" + alias["sample"]] = {
            "stream": stream.split("/"),
            "sample_handle": alias["sample"],
            "measurement_handles": [],
        }
        for handle in handles:
            data["refusals"][stream + "/measurement/" + handle] = {
                "stream": stream.split("/"),
                "sample_handle": alias["sample"],
                "measurement_handles": [handle],
            }

    def _cleanup_fields(self, data: dict[str, Any], alias: dict[str, Any]) -> dict[str, Any]:
        stream = alias["stream"]
        head = self._head(data, "source", stream)
        fields = {
            "schema_version": "gsip-node-exchange-v1",
            "event_id": str(uuid4()),
            "source_peer_id": stream.split("/")[0],
            "destination_peer_id": stream.split("/")[1],
            "scope_id": stream.split("/")[2],
            "stream_sequence": 0 if head is None else head.stream_sequence + 1,
            "previous_event_sha256": None if head is None else head.sha256,
            "kind": "retire",
            "payload": {
                "sample_handle": alias["sample"],
                "measurement_handles": sorted(alias["measurements"].values())[:100],
            },
        }
        prepared = prepare_node_exchange_event(_wire(fields))
        slot = node_exchange_slot(prepared)
        check_node_exchange_identity(slot, self._facts(data))
        event = self._event(prepared, alias["group"])
        event["source_admitted"] = True
        data["events"][str(prepared.event.event_id)] = event
        data["source_slots"][_slot_key(slot)] = event["slot"]
        self._advance(data, "source", stream)
        return fields

    def _erase_owned(
        self,
        session: PrivateExchangeSession,
        snap: StoreSnapshot,
        data: dict[str, Any],
        group: str,
        *,
        source_only: bool,
    ) -> StoreSnapshot:
        ids = [
            blob_id
            for blob_id, owner in data["blob_owners"].items()
            if owner["group"] == group
            and owner["science"]
            and (not source_only or snap.blobs[blob_id].category in ("source", "draft"))
        ]
        if not ids:
            return snap
        for blob_id in ids:
            del data["blob_owners"][blob_id]
        data["bindings"] = {
            key: value for key, value in data["bindings"].items() if value["blob_id"] not in ids
        }
        for event_id, event in data["events"].items():
            for role in ("source", "recipient"):
                if event[role + "_blob"] in ids:
                    event[role + "_blob"] = None
            if event_id in data["outbox"] and data["outbox"][event_id]["blob_id"] in ids:
                del data["outbox"][event_id]
        return session.erase_blobs(data, ids, snap.generation)

    def withdraw_original(self, human_id: str | UUID, sample_id: str | UUID) -> int:
        def withdraw() -> int:
            group_key = _group(_id(human_id), _id(sample_id))
            with self._store.locked() as session:
                snap, data = self._load(session)
                group = data["origins"].get(group_key)
                if group is None:
                    origins = [
                        origin
                        for origin in self._authority.origins
                        if _group(_id(origin.human_id), _id(origin.sample_id)) == group_key
                    ]
                    _require(
                        bool(origins) and len({_id(origin.grant_id) for origin in origins}) == 1
                    )
                    group = {
                        "human": _id(human_id),
                        "sample": _id(sample_id),
                        "grant": _id(origins[0].grant_id),
                        "withdrawn": False,
                        "sealed": any(origin.sealed for origin in origins),
                        "synthetic": any(origin.synthetic_restricted for origin in origins),
                    }
                    data["origins"][group_key] = group
                group["withdrawn"] = True
                aliases = [
                    alias for alias in data["aliases"].values() if alias["group"] == group_key
                ]
                scopes = sorted({alias["stream"].split("/")[2] for alias in aliases})
                candidate = copy.deepcopy(data)
                try:
                    for alias in aliases:
                        self._refuse_alias(candidate, alias)
                        key = alias["stream"] + "/" + alias["sample"]
                        if key not in candidate["cleanup"]:
                            fields = self._cleanup_fields(candidate, alias)
                            candidate["cleanup"][key] = {
                                "fields": fields,
                                "group": group_key,
                                "complete": False,
                            }
                    self._capacities(candidate, snap, 0)
                    # Include complete-image byte refusal in the reserved-fence fallback.
                    snap = session.commit_metadata(candidate, snap.generation)
                except ValueError:
                    # A not-yet-staged original may itself need a new origin row.
                    # Fall back only to existing facts; fence this human's scopes
                    # when no immutable alias yet identifies narrower coverage.
                    fallback = self._data(snap)
                    if group_key in fallback["origins"]:
                        fallback["origins"][group_key]["withdrawn"] = True
                    fallback_scopes = scopes or [
                        key
                        for key, value in fallback["scopes"].items()
                        if value["human"] == _id(human_id)
                    ]
                    self._fence(session, snap, fallback, fallback_scopes)
                    return len(fallback_scopes)
                # Canonical source withdrawal/refusals/cleanup intent first. No science tuple.
                data = self._data(snap)
                self._erase_owned(session, snap, data, group_key, source_only=True)
                return len(aliases)

        return _guard(withdraw)

    def withdraw_grant(self, human_id: str | UUID, grant_id: str | UUID) -> int:
        def withdraw() -> int:
            human, grant = _id(human_id), _id(grant_id)
            samples = {
                _id(origin.sample_id)
                for origin in self._authority.origins
                if (_id(origin.human_id), _id(origin.grant_id)) == (human, grant)
            }
            _require(bool(samples))
            with self._store.locked() as session:
                snap, data = self._load(session)
                data["retired_grants"][human + "/" + grant] = True
                for group in data["origins"].values():
                    if (group["human"], group["grant"]) == (human, grant):
                        group["withdrawn"] = True
                try:
                    session.commit_metadata(data, snap.generation)
                except ValueError:
                    # A new grant key must not defeat the pre-reserved no-allocation
                    # erasure fence at a full metadata image.
                    fallback = self._data(snap)
                    for group in fallback["origins"].values():
                        if (group["human"], group["grant"]) == (human, grant):
                            group["withdrawn"] = True
                    scopes = [
                        key for key, value in fallback["scopes"].items() if value["human"] == human
                    ]
                    self._fence(session, snap, fallback, scopes)
                    return len(scopes)
            return sum(self.withdraw_original(human, sample) for sample in sorted(samples))

        return _guard(withdraw)

    def _admit_retirement(
        self, data: dict[str, Any], prepared: PreparedNodeExchangeEvent, group: str
    ) -> tuple[dict[str, Any], bool]:
        """Validate recipient facts on a candidate; never promote a contradictory chain."""
        slot = node_exchange_slot(prepared)
        try:
            check_node_exchange_identity(slot, self._facts(data))
            admitted = copy.deepcopy(data)
            event = admitted["events"].setdefault(
                str(prepared.event.event_id), self._event(prepared, group)
            )
            event["recipient_admitted"] = True
            admitted["recipient_slots"][_slot_key(slot)] = _slot_dict(slot)
            self._advance(admitted, "recipient", _stream_key(slot.stream))
        except ValueError:
            data["scopes"][str(prepared.event.scope_id)]["conflicted"] = True
            return data, True
        return admitted, False

    def _receive_retirement(self, prepared: PreparedNodeExchangeEvent) -> LocalReceipt:
        if not isinstance(prepared.event, NodeExchangeRetirement):
            raise SyntheticExchangeError(_MESSAGE)
        with self._store.locked() as session:
            snap, data = self._load(session)
            scope_id = str(prepared.event.scope_id)
            facts = self._scope(data, scope_id)
            if facts["stream"] != [
                str(value) for value in node_exchange_stream(prepared.event)
            ] or not self._allowed(facts, cleanup=True):
                return self._receipt(prepared, "held")
            refusal_key = (
                _stream_key(node_exchange_stream(prepared.event))
                + "/sample/"
                + str(prepared.event.payload.sample_handle)
            )
            known = [
                alias
                for alias in data["aliases"].values()
                if alias["sample"] == str(prepared.event.payload.sample_handle)
                and alias["stream"] == _stream_key(node_exchange_stream(prepared.event))
            ]
            if known:
                group_key = self._alias_for_event(data, prepared)["group"]
            else:
                # Working aliases may already be erased by another scoped cleanup.
                # Retained original/event and refusal facts still bind this exact scope.
                groups = {
                    event["group"]
                    for event in data["events"].values()
                    if event["scope"] == scope_id
                    and event["sample"] == str(prepared.event.payload.sample_handle)
                }
                stream = _stream_key(node_exchange_stream(prepared.event))
                if (
                    refusal_key not in data["refusals"]
                    or len(groups) != 1
                    or any(
                        stream + "/measurement/" + str(handle) not in data["refusals"]
                        for handle in prepared.event.payload.measurement_handles
                    )
                ):
                    return self._receipt(prepared, "held")
                group_key = next(iter(groups))
            data["origins"][group_key]["withdrawn"] = True
            all_aliases = [
                value for value in data["aliases"].values() if value["group"] == group_key
            ]
            candidate = copy.deepcopy(data)
            scopes = sorted(
                {value["stream"].split("/")[2] for value in all_aliases}
                | {
                    event["scope"]
                    for event in data["events"].values()
                    if event["group"] == group_key
                }
            )
            known_source = data["events"].get(str(prepared.event.event_id))
            if (
                known_source is None
                or not known_source["source_admitted"]
                or known_source["kind"] != "retire"
            ):
                for affected_scope_id in scopes:
                    scope = candidate["scopes"][affected_scope_id]
                    scope["fenced"] = True
                    scope["pending_erasure"] = True
            for value in all_aliases:
                self._refuse_alias(candidate, value)
            candidate, conflict = self._admit_retirement(candidate, prepared, group_key)
            try:
                self._capacities(candidate, snap, 0)
                snap = session.commit_metadata(candidate, snap.generation)
            except ValueError:
                self._fence(
                    session,
                    snap,
                    data,
                    scopes,
                )
                return self._receipt(prepared, "held")
            data = self._data(snap)
            snap = self._erase_owned(session, snap, data, group_key, source_only=False)
            data = self._data(snap)
            absent = self._cleanup_absent(session, data, prepared)
            if absent:
                data["aliases"] = {
                    key: value
                    for key, value in data["aliases"].items()
                    if value["group"] != group_key
                }
                session.commit_metadata(data, snap.generation)
            return (
                self._receipt(prepared, "conflict")
                if conflict
                else self._receipt(prepared, "retired", absent)
            )

    def _cleanup_absent(
        self,
        session: PrivateExchangeSession,
        data: dict[str, Any],
        prepared: PreparedNodeExchangeEvent,
    ) -> bool:
        if not isinstance(prepared.event, NodeExchangeRetirement):
            raise SyntheticExchangeError(_MESSAGE)
        stream = _stream_key(node_exchange_stream(prepared.event))
        sample = str(prepared.event.payload.sample_handle)
        if stream + "/sample/" + sample not in data["refusals"]:
            return False
        for handle in prepared.event.payload.measurement_handles:
            if stream + "/measurement/" + str(handle) not in data["refusals"]:
                return False
        groups = {
            event["group"]
            for event in data["events"].values()
            if event["scope"] == str(prepared.event.scope_id) and event["sample"] == sample
        }
        if len(groups) != 1:
            return False
        owners = [
            blob
            for blob, owner in data["blob_owners"].items()
            if owner["science"] and owner["group"] in groups
        ]
        # verified_absent also verifies the entire managed inventory; unknown files hold.
        return not owners and session.verified_absent(owners)

    def _materialize_cleanup(
        self, session: PrivateExchangeSession, snap: StoreSnapshot, data: dict[str, Any]
    ) -> StoreSnapshot:
        for value in data["cleanup"].values():
            fields = value["fields"]
            event_id = fields["event_id"]
            if value["complete"] or event_id in data["outbox"]:
                continue
            prepared = prepare_node_exchange_event(_wire(fields))
            if data["events"][event_id]["slot"] != _slot_dict(node_exchange_slot(prepared)):
                raise SyntheticExchangeError(_MESSAGE)
            blob_id = str(uuid4())
            data["events"][event_id]["source_blob"] = blob_id
            data["blob_owners"][blob_id] = {
                "group": value["group"],
                "scope": fields["scope_id"],
                "sample": fields["payload"]["sample_handle"],
                "science": False,
            }
            data["outbox"][event_id] = {
                "kind": "retire",
                "blob_id": blob_id,
                "draft": False,
                "attempts": 0,
                "ready_at": self._clock.seconds(),
                "claim": None,
                "claim_until": None,
                "held": False,
            }
            try:
                self._capacities(data, snap, len(prepared.original_bytes))
                return session.put_blob(
                    data, BlobWrite(blob_id, "source", prepared.original_bytes), snap.generation
                )
            except ValueError:
                original = self._data(snap)
                self._fence(session, snap, original, [fields["scope_id"]])
                return session.snapshot()
        return snap

    def _claim(self, limit: int) -> list[_Claim]:
        with self._store.locked() as session:
            snap, data = self._load(session)
            for _ in range(limit):
                if not any(
                    not value["complete"] and value["fields"]["event_id"] not in data["outbox"]
                    for value in data["cleanup"].values()
                ):
                    break
                snap = self._materialize_cleanup(session, snap, data)
                data = self._data(snap)
            claims: list[_Claim] = []
            changed = False
            for event_id, item in sorted(
                data["outbox"].items(),
                key=lambda pair: (
                    pair[1]["kind"] != "retire",
                    pair[1]["ready_at"],
                    _stream_key(data["events"][pair[0]]["slot"]["stream"]),
                    data["events"][pair[0]]["slot"]["stream_sequence"],
                    pair[0],
                ),
            ):
                if len(claims) >= limit:
                    break
                event = data["events"][event_id]
                facts = self._scope(data, event["scope"])
                if not self._allowed(facts, cleanup=item["kind"] == "retire"):
                    continue
                if item["kind"] == "declare" and not self._measurement_allowed(data, event):
                    continue
                if item["claim"] is not None and item["claim_until"] <= self._clock.seconds():
                    # Lost replies and stopped processes reuse owned bytes and a fresh nonce.
                    item["claim"] = None
                    item["claim_until"] = None
                    self._transient(item)
                    changed = True
                if (
                    item["held"]
                    or item["draft"]
                    or item["claim"] is not None
                    or item["ready_at"] > self._clock.seconds()
                ):
                    continue
                if not self._allowed(facts, cleanup=item["kind"] == "retire"):
                    continue
                raw = session.read_blob(item["blob_id"])
                prepared = prepare_node_exchange_event(raw)
                if event["slot"] != _slot_dict(node_exchange_slot(prepared)):
                    raise SyntheticExchangeError(_MESSAGE)
                nonce = str(uuid4())
                item["claim"] = nonce
                item["claim_until"] = self._clock.seconds() + CLAIM_RECOVERY_SECONDS
                changed = True
                claims.append(_Claim(event_id, nonce, prepared.original_bytes, item["kind"]))
            if changed:
                session.commit_metadata(data, snap.generation)
            return claims

    def _transient(self, item: dict[str, Any]) -> None:
        item["attempts"] += 1
        if item["attempts"] >= MAX_ATTEMPTS:
            item["held"] = True
        else:
            item["ready_at"] = self._clock.seconds() + BACKOFF_SECONDS[item["attempts"] - 1]

    def _checkpoint(self, claim: _Claim, receipt: LocalReceipt | None, transient: bool) -> bool:
        with self._store.locked() as session:
            snap, data = self._load(session)
            item = data["outbox"].get(claim.event_id)
            if item is None or item["claim"] != claim.nonce:
                return False
            item["claim"] = None
            item["claim_until"] = None
            event = data["events"][claim.event_id]
            facts = self._scope(data, event["scope"])
            if not self._allowed(facts, cleanup=claim.kind == "retire") or (
                claim.kind == "declare" and not self._measurement_allowed(data, event)
            ):
                item["claim"] = None
                session.commit_metadata(data, snap.generation)
                return False
            if transient:
                self._transient(item)
                session.commit_metadata(data, snap.generation)
                return False
            if receipt is None or (type(receipt) is LocalReceipt and receipt.status == "held"):
                item["claim"] = None
                session.commit_metadata(data, snap.generation)
                return False
            prepared = prepare_node_exchange_event(claim.raw)
            if type(receipt) is not LocalReceipt or type(receipt.payload_absent) is not bool:
                item["held"] = True
                session.commit_metadata(data, snap.generation)
                return False
            expected = self._receipt(prepared, receipt.status, receipt.payload_absent)
            if receipt != expected:
                item["held"] = True
                session.commit_metadata(data, snap.generation)
                return False
            if receipt.status == "conflict":
                item["held"] = True
                item["claim"] = None
                session.commit_metadata(data, snap.generation)
                return False
            if claim.kind == "retire":
                if (
                    receipt.status != "retired"
                    or not receipt.payload_absent
                    or not self._cleanup_absent(session, data, prepared)
                ):
                    item["claim"] = None
                    session.commit_metadata(data, snap.generation)
                    return False
                key = (
                    _stream_key(node_exchange_stream(prepared.event))
                    + "/"
                    + str(prepared.event.payload.sample_handle)
                )
                if key not in data["cleanup"]:
                    raise SyntheticExchangeError(_MESSAGE)
                del data["cleanup"][key]
                blob_id = item["blob_id"]
                del data["outbox"][claim.event_id]
                del data["blob_owners"][blob_id]
                event["source_blob"] = None
                session.erase_blobs(data, [blob_id], snap.generation)
            else:
                if (
                    receipt.status not in ("stored", "already_stored")
                    or not self._measurement_allowed(data, event)
                    or not event["recipient_admitted"]
                    or event["recipient_blob"] is None
                ):
                    session.commit_metadata(data, snap.generation)
                    return False
                own = prepare_node_exchange_event(session.read_blob(event["recipient_blob"]))
                if own.original_bytes != claim.raw or event["slot"] != _slot_dict(
                    node_exchange_slot(own)
                ):
                    raise SyntheticExchangeError(_MESSAGE)
                del data["outbox"][claim.event_id]
                # Stored source bytes stay charged until actual rights erasure.
                session.commit_metadata(data, snap.generation)
            return True

    def process_batch(self, transport: FakeTransport, *, limit: int = MAX_BATCH) -> dict[str, int]:
        def process() -> dict[str, int]:
            if (
                type(transport) is not FakeTransport
                or type(limit) is not int
                or not 1 <= limit <= MAX_BATCH
            ):
                raise SyntheticExchangeError(_MESSAGE)
            _require(type(transport.script) is tuple and len(transport.script) <= MAX_BATCH)
            _require(
                all(
                    type(action) is str
                    and action in ("deliver", "disconnect", "transient", "lose_reply")
                    for action in transport.script
                )
            )
            _require(
                type(transport._position) is int
                and 0 <= transport._position <= len(transport.script)
            )
            claims = self._claim(limit)
            completed = 0
            for claim in claims:
                transient = False
                receipt = None
                try:
                    # No root lock held across even the scripted local delivery.
                    receipt = transport.deliver(self, claim.raw)
                except _TransientFailure:
                    transient = True
                except Exception:
                    # Unavailable/unknown outcomes preserve intent without spending an
                    # explicit transient attempt. No value-bearing error is persisted.
                    receipt = None
                completed += self._checkpoint(claim, receipt, transient)
            return {"claimed": len(claims), "completed": completed}

        return _guard(process)

    def payload_status(
        self, event_id: str | UUID
    ) -> Literal["held", "available_for_synthetic_simulation"]:
        def status() -> Literal["held", "available_for_synthetic_simulation"]:
            with self._store.locked() as session:
                snap, data = self._load(session)
                event = data["events"].get(_id(event_id))
                if event is None or event["kind"] != "declare":
                    return "held"
                facts = self._scope(data, event["scope"])
                if (
                    not self._allowed(facts)
                    or not self._measurement_allowed(data, event)
                    or event["gapped"]
                    or event["recipient_blob"] is None
                ):
                    return "held"
                own = prepare_node_exchange_event(session.read_blob(event["recipient_blob"]))
                if event["slot"] != _slot_dict(node_exchange_slot(own)):
                    raise SyntheticExchangeError(_MESSAGE)
                return "available_for_synthetic_simulation"

        return _guard(status)

    def create_synthetic_preparation(self, event_id: str | UUID) -> str:
        def prepare() -> str:
            with self._store.locked() as session:
                snap, data = self._load(session)
                event = data["events"][_id(event_id)]
                facts = self._scope(data, event["scope"])
                if (
                    not self._allowed(facts)
                    or not self._measurement_allowed(data, event)
                    or event["gapped"]
                    or event["recipient_blob"] is None
                ):
                    raise SyntheticExchangeError(_MESSAGE)
                own = prepare_node_exchange_event(session.read_blob(event["recipient_blob"]))
                if event["slot"] != _slot_dict(node_exchange_slot(own)):
                    raise SyntheticExchangeError(_MESSAGE)
                blob_id = str(uuid4())
                raw = b"GSIP synthetic preparation only; no field training or publication.\n"
                data["blob_owners"][blob_id] = {
                    "group": event["group"],
                    "scope": event["scope"],
                    "sample": event["sample"],
                    "science": True,
                }
                self._capacities(data, snap, len(raw))
                session.put_blob(data, BlobWrite(blob_id, "preparation", raw), snap.generation)
                return blob_id

        return _guard(prepare)

    def counts(self) -> dict[str, int | bool]:
        def counts() -> dict[str, int | bool]:
            with self._store.locked() as session:
                snap, data = self._load(session)
                live_groups = {
                    owner["group"]
                    for owner in data["blob_owners"].values()
                    if owner["science"] and self._group_allowed(data["origins"][owner["group"]])
                }
                return {
                    "synthetic_only": True,
                    "field_eligible": 0,
                    "verified_physical_pairs": 0,
                    "scopes": len(data["scopes"]),
                    "fenced_scopes": sum(value["fenced"] for value in data["scopes"].values()),
                    "independent_fake_samples": len(live_groups),
                    "independent_fake_humans": len(
                        {data["origins"][group]["human"] for group in live_groups}
                    ),
                    "queued_declarations": sum(
                        value["kind"] == "declare" for value in data["outbox"].values()
                    )
                    + sum(
                        event["kind"] == "declare"
                        and event["recipient_admitted"]
                        and event["gapped"]
                        for event in data["events"].values()
                    ),
                    "retained_slots": len(data["source_slots"]) + len(data["recipient_slots"]),
                    "refusals": len(data["refusals"]),
                    "pending_cleanup": sum(
                        not value["complete"] for value in data["cleanup"].values()
                    )
                    + sum(value["pending_erasure"] for value in data["scopes"].values()),
                    "retained_bytes": sum(value.byte_count for value in snap.blobs.values()),
                }

        return _guard(counts)
