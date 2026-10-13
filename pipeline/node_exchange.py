"""Pure synthetic exchange contracts. No I/O, credentials, authority or scientific verification."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypeVar
from uuid import UUID

from pydantic import BeforeValidator, Field, TypeAdapter, model_validator

from pipeline.library import CameraRgb, Context, Digest, InstrumentReflectance, StrictRecord

MAX_NODE_EXCHANGE_BYTES = 2_000_000
MAX_NODE_EXCHANGE_DEPTH = 12
MAX_NODE_EXCHANGE_SEQUENCE = 9_007_199_254_740_991
_INVALID = "Invalid node exchange event"
_CONFLICT = "Node exchange conflict"
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
T = TypeVar("T")


def _guard(operation: Callable[[], T], message: str = _INVALID) -> T:
    try:
        return operation()
    except Exception:
        failure_message = message
    # Outside the exception handler: no retained input-bearing cause/context.
    raise ValueError(failure_message)


def _uuid(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str) or _UUID.fullmatch(value) is None:
        raise ValueError(_INVALID)
    return UUID(value)


OpaqueUuid = Annotated[UUID, BeforeValidator(_uuid)]
SequenceNumber = Annotated[int, Field(strict=True, ge=0, le=MAX_NODE_EXCHANGE_SEQUENCE)]
Stream = tuple[OpaqueUuid, OpaqueUuid, OpaqueUuid]


class _Camera(CameraRgb):
    device_id: OpaqueUuid


class _Instrument(InstrumentReflectance):
    instrument_id: OpaqueUuid
    calibration_id: OpaqueUuid


Measurement = Annotated[_Camera | _Instrument, Field(discriminator="kind")]


class _Declaration(StrictRecord):
    sample_handle: OpaqueUuid
    measurement_handle: OpaqueUuid
    protocol_version: Literal["gsip-capture-v1"]
    context: Context
    measurement: Measurement
    synthetic_claim: Annotated[bool, Field(strict=True)]


class _Retirement(StrictRecord):
    sample_handle: OpaqueUuid
    measurement_handles: Annotated[tuple[OpaqueUuid, ...], Field(max_length=100)]

    @model_validator(mode="after")
    def unique_handles(self) -> _Retirement:
        if len(set(self.measurement_handles)) != len(self.measurement_handles):
            raise ValueError(_INVALID)
        return self


class _Common(StrictRecord):
    schema_version: Literal["gsip-node-exchange-v1"]
    event_id: OpaqueUuid
    source_peer_id: OpaqueUuid
    destination_peer_id: OpaqueUuid
    scope_id: OpaqueUuid
    stream_sequence: SequenceNumber
    previous_event_sha256: Digest | None

    @model_validator(mode="after")
    def initial_predecessor(self) -> _Common:
        if (self.stream_sequence == 0) != (self.previous_event_sha256 is None):
            raise ValueError(_INVALID)
        return self


class NodeExchangeDeclaration(_Common):
    kind: Literal["declare"]
    payload: _Declaration


class NodeExchangeRetirement(_Common):
    kind: Literal["retire"]
    payload: _Retirement


NodeExchangeEvent = NodeExchangeDeclaration | NodeExchangeRetirement
_EVENT: TypeAdapter[NodeExchangeEvent] = TypeAdapter(
    Annotated[NodeExchangeEvent, Field(discriminator="kind")]
)


def _unicode(value: str) -> None:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError(_INVALID)


def _preflight(raw: str) -> None:
    position = 0

    def whitespace() -> None:
        nonlocal position
        while position < len(raw) and raw[position] in " \t\r\n":
            position += 1

    def string() -> str:
        nonlocal position
        if position >= len(raw) or raw[position] != '"':
            raise ValueError(_INVALID)
        start = position
        position += 1
        while position < len(raw):
            if raw[position] == "\\":
                position += 2
                continue
            position += 1
            if raw[position - 1] == '"':
                decoded = json.loads(raw[start:position])
                if not isinstance(decoded, str):
                    raise ValueError(_INVALID)
                _unicode(decoded)
                return decoded
        raise ValueError(_INVALID)

    def value(path: tuple[str, ...], depth: int) -> None:
        nonlocal position
        whitespace()
        lead = raw[position] if position < len(raw) else ""
        if lead in ("{", "["):
            depth += 1
            if depth > MAX_NODE_EXCHANGE_DEPTH:
                raise ValueError(_INVALID)
            position += 1
            is_object = lead == "{"
            end = "}" if is_object else "]"
            keys: set[str] = set()
            whitespace()
            if position < len(raw) and raw[position] == end:
                position += 1
                return
            while position < len(raw):
                child_path = path
                if is_object:
                    whitespace()
                    key = string()
                    if key in keys:
                        raise ValueError(_INVALID)
                    keys.add(key)
                    child_path = (*path, key)
                    whitespace()
                    if position >= len(raw) or raw[position] != ":":
                        raise ValueError(_INVALID)
                    position += 1
                value(child_path, depth)
                whitespace()
                if position < len(raw) and raw[position] == end:
                    position += 1
                    return
                if position >= len(raw) or raw[position] != ",":
                    raise ValueError(_INVALID)
                position += 1
            raise ValueError(_INVALID)
        if lead == '"':
            string()
            return
        start = position
        while position < len(raw) and raw[position] not in " \t\r\n,]}":
            position += 1
        literal = raw[start:position]
        field = "/".join(path)
        bound = {
            "stream_sequence": "9007199254740991",
            "payload/measurement/pixel_count": "40000000",
        }.get(field)
        if bound is not None:
            if (
                re.fullmatch(r"0|[1-9][0-9]*", literal) is None
                or len(literal) > len(bound)
                or (len(literal) == len(bound) and literal > bound)
                or (field == "payload/measurement/pixel_count" and literal == "0")
            ):
                raise ValueError(_INVALID)
            return
        if literal in ("true", "false", "null"):
            return
        if re.fullmatch(
            r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?", literal
        ) is None or not math.isfinite(float(literal)):
            raise ValueError(_INVALID)

    whitespace()
    if position >= len(raw) or raw[position] != "{":
        raise ValueError(_INVALID)
    value((), 0)
    whitespace()
    if position != len(raw):
        raise ValueError(_INVALID)


def _snapshot(data: bytes) -> bytes:
    if not isinstance(data, bytes) or bytes.__len__(data) > MAX_NODE_EXCHANGE_BYTES:
        raise ValueError(_INVALID)
    # Bypass subclass __len__/__bytes__/__getitem__ overrides before retaining bytes.
    return bytes.__getitem__(data, slice(None))


def _parse(data: bytes) -> NodeExchangeEvent:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ValueError(_INVALID)
    raw = data.decode("utf-8", errors="strict")
    _preflight(raw)
    return _EVENT.validate_python(json.loads(raw))


def parse_node_exchange_event(data: bytes) -> NodeExchangeEvent:
    return _guard(lambda: _parse(_snapshot(data)))


@dataclass(frozen=True)
class PreparedNodeExchangeEvent:
    event: NodeExchangeEvent
    sha256: str
    original_bytes: bytes


def prepare_node_exchange_event(data: bytes) -> PreparedNodeExchangeEvent:
    def prepare() -> PreparedNodeExchangeEvent:
        original = _snapshot(data)
        event = _parse(original)
        return PreparedNodeExchangeEvent(event, hashlib.sha256(original).hexdigest(), original)

    return _guard(prepare)


def node_exchange_schema() -> dict[str, Any]:
    """Semantic JSON Schema; raw byte/lexical rules still require the byte parser."""
    return _EVENT.json_schema()


def node_exchange_stream(event: NodeExchangeEvent) -> Stream:
    return _guard(lambda: _stream(_EVENT.validate_python(event)))


def _stream(event: NodeExchangeEvent) -> Stream:
    return event.source_peer_id, event.destination_peer_id, event.scope_id


class NodeExchangeSlot(StrictRecord):
    stream: Stream
    event_id: OpaqueUuid
    stream_sequence: SequenceNumber
    previous_event_sha256: Digest | None
    sha256: Digest

    @model_validator(mode="after")
    def initial_predecessor(self) -> NodeExchangeSlot:
        if (self.stream_sequence == 0) != (self.previous_event_sha256 is None):
            raise ValueError(_CONFLICT)
        return self


class NodeExchangeBinding(StrictRecord):
    stream: Stream
    sample_handle: OpaqueUuid
    measurement_handle: OpaqueUuid
    protocol_version: Literal["gsip-capture-v1"]
    context: Context
    measurement: Measurement
    synthetic_restricted: Annotated[bool, Field(strict=True)]


class NodeExchangeRetirementAliases(_Retirement):
    stream: Stream


class NodeExchangeHead(StrictRecord):
    stream_sequence: SequenceNumber
    sha256: Digest


@dataclass(frozen=True)
class NodeExchangeChainResult:
    head: NodeExchangeHead | None
    advanced: int
    gap: bool


def node_exchange_slot(prepared: PreparedNodeExchangeEvent) -> NodeExchangeSlot:
    def slot() -> NodeExchangeSlot:
        event = _EVENT.validate_python(prepared.event)
        return NodeExchangeSlot(
            stream=_stream(event),
            event_id=event.event_id,
            stream_sequence=event.stream_sequence,
            previous_event_sha256=event.previous_event_sha256,
            sha256=prepared.sha256,
        )

    return _guard(slot, _CONFLICT)


def _slots(slots: Sequence[NodeExchangeSlot]) -> list[NodeExchangeSlot]:
    identities: dict[UUID, NodeExchangeSlot] = {}
    positions: dict[tuple[Stream, int], NodeExchangeSlot] = {}
    result = []
    for value in slots:
        slot = NodeExchangeSlot.model_validate(value)
        key = slot.stream, slot.stream_sequence
        for prior in (identities.get(slot.event_id), positions.get(key)):
            if prior is not None and prior != slot:
                raise ValueError(_CONFLICT)
        identities[slot.event_id] = slot
        positions[key] = slot
        result.append(slot)
    return result


def check_node_exchange_identity(
    candidate: NodeExchangeSlot, slots: Sequence[NodeExchangeSlot]
) -> Literal["new", "retry"]:
    def check() -> Literal["new", "retry"]:
        normalized = NodeExchangeSlot.model_validate(candidate)
        facts = _slots([*slots, normalized])
        return (
            "retry" if any(slot.event_id == normalized.event_id for slot in facts[:-1]) else "new"
        )

    return _guard(check, _CONFLICT)


def bind_node_exchange_measurement(
    event: NodeExchangeDeclaration, bindings: Sequence[NodeExchangeBinding]
) -> NodeExchangeBinding:
    def bind() -> NodeExchangeBinding:
        parsed = _EVENT.validate_python(event)
        if not isinstance(parsed, NodeExchangeDeclaration):
            raise ValueError(_CONFLICT)
        payload = parsed.payload
        candidate = NodeExchangeBinding(
            stream=_stream(parsed),
            sample_handle=payload.sample_handle,
            measurement_handle=payload.measurement_handle,
            protocol_version=payload.protocol_version,
            context=payload.context,
            measurement=payload.measurement,
            synthetic_restricted=payload.synthetic_claim,
        )
        restricted = candidate.synthetic_restricted
        for value in bindings:
            prior = NodeExchangeBinding.model_validate(value)
            if (
                prior.stream != candidate.stream
                or prior.measurement_handle != candidate.measurement_handle
            ):
                continue
            if (
                prior.sample_handle != candidate.sample_handle
                or prior.protocol_version != candidate.protocol_version
                or prior.context != candidate.context
                or prior.measurement != candidate.measurement
            ):
                raise ValueError(_CONFLICT)
            restricted = restricted or prior.synthetic_restricted
        return NodeExchangeBinding.model_validate(
            candidate.model_copy(update={"synthetic_restricted": restricted})
        )

    return _guard(bind, _CONFLICT)


def node_exchange_retirement_aliases(
    event: NodeExchangeEvent,
) -> NodeExchangeRetirementAliases | None:
    """Aliases only: the caller must separately establish synthetic/real cleanup authority."""

    def aliases() -> NodeExchangeRetirementAliases | None:
        parsed = _EVENT.validate_python(event)
        if not isinstance(parsed, NodeExchangeRetirement):
            return None
        return NodeExchangeRetirementAliases(
            stream=_stream(parsed),
            sample_handle=parsed.payload.sample_handle,
            measurement_handles=parsed.payload.measurement_handles,
        )

    return _guard(aliases, _CONFLICT)


def node_exchange_declaration_covered(
    event: NodeExchangeDeclaration, refusals: Sequence[NodeExchangeRetirementAliases]
) -> bool:
    def covered() -> bool:
        parsed = _EVENT.validate_python(event)
        if not isinstance(parsed, NodeExchangeDeclaration):
            raise ValueError(_CONFLICT)
        for value in refusals:
            refusal = NodeExchangeRetirementAliases.model_validate(value)
            if refusal.stream == _stream(parsed) and (
                refusal.sample_handle == parsed.payload.sample_handle
                or parsed.payload.measurement_handle in refusal.measurement_handles
            ):
                return True
        return False

    return _guard(covered, _CONFLICT)


def advance_node_exchange_head(
    stream: Stream, head: NodeExchangeHead | None, slots: Sequence[NodeExchangeSlot]
) -> NodeExchangeChainResult:
    def advance() -> NodeExchangeChainResult:
        normalized: Stream = TypeAdapter(Stream).validate_python(stream)
        current = None if head is None else NodeExchangeHead.model_validate(head)
        selected = [slot for slot in _slots(slots) if slot.stream == normalized]
        by_sequence = {slot.stream_sequence: slot for slot in selected}
        if (
            current is not None
            and current.stream_sequence in by_sequence
            and by_sequence[current.stream_sequence].sha256 != current.sha256
        ):
            raise ValueError(_CONFLICT)
        advanced = 0
        while current is None or current.stream_sequence < MAX_NODE_EXCHANGE_SEQUENCE:
            next_sequence = 0 if current is None else current.stream_sequence + 1
            slot = by_sequence.get(next_sequence)
            if slot is None:
                break
            if slot.previous_event_sha256 != (None if current is None else current.sha256):
                raise ValueError(_CONFLICT)
            current = NodeExchangeHead(stream_sequence=next_sequence, sha256=slot.sha256)
            advanced += 1
        sequence = -1 if current is None else current.stream_sequence
        return NodeExchangeChainResult(
            current, advanced, any(slot.stream_sequence > sequence for slot in selected)
        )

    return _guard(advance, _CONFLICT)
