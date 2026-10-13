import copy
import importlib.util
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from pipeline.node_exchange import (
    MAX_NODE_EXCHANGE_BYTES,
    NodeExchangeDeclaration,
    NodeExchangeSlot,
    node_exchange_schema,
)
from pipeline.node_exchange import (
    advance_node_exchange_head as advance,
)
from pipeline.node_exchange import (
    bind_node_exchange_measurement as bind,
)
from pipeline.node_exchange import (
    check_node_exchange_identity as identity,
)
from pipeline.node_exchange import (
    node_exchange_declaration_covered as covered,
)
from pipeline.node_exchange import (
    node_exchange_retirement_aliases as aliases,
)
from pipeline.node_exchange import (
    node_exchange_slot as slot,
)
from pipeline.node_exchange import (
    node_exchange_stream as stream,
)
from pipeline.node_exchange import (
    parse_node_exchange_event as parse,
)
from pipeline.node_exchange import (
    prepare_node_exchange_event as prepare,
)

CORPUS = json.loads(
    (
        Path(__file__).parents[1] / "packages/schema/tests/fixtures/node-exchange-conformance.json"
    ).read_text()
)
RAW: str = CORPUS["event_cases"][0]["raw"]


def uuid(number: int) -> str:
    return f"00000000-0000-0000-0000-{number:012x}"


def candidate(**changes: Any) -> bytes:
    return json.dumps(json.loads(RAW) | changes, separators=(",", ":")).encode()


def declare(**changes: Any) -> NodeExchangeDeclaration:
    event = parse(candidate(**changes))
    assert isinstance(event, NodeExchangeDeclaration)
    return event


def test_node_exchange_contract_exists() -> None:
    assert importlib.util.find_spec("pipeline.node_exchange") is not None


@pytest.mark.parametrize("case", CORPUS["event_cases"], ids=lambda case: case["name"])
def test_shared_synthetic_event_corpus(case: dict[str, Any]) -> None:
    if case["valid"]:
        assert parse(case["raw"].encode()).schema_version == "gsip-node-exchange-v1"
    else:
        with pytest.raises(ValueError, match="^Invalid node exchange event$"):
            parse(case["raw"].encode())


@pytest.mark.parametrize("case", CORPUS["byte_cases"], ids=lambda case: case["name"])
def test_shared_synthetic_byte_corpus(case: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="^Invalid node exchange event$"):
        parse(bytes.fromhex(case["hex"]))


@pytest.mark.parametrize("case", CORPUS["band_count_cases"])
def test_band_count_bounds(case: dict[str, Any]) -> None:
    value = json.loads(CORPUS["event_cases"][1]["raw"])
    count = case["count"]
    value["payload"]["measurement"].update(
        wavelength_nm=[200 + i for i in range(count)],
        reflectance=[0.4] * count,
        uncertainty=[0.01] * count,
    )
    if case["valid"]:
        parse(json.dumps(value).encode())
    else:
        with pytest.raises(ValueError):
            parse(json.dumps(value).encode())


def test_byte_bound_before_decode_parse_and_bytes_only() -> None:
    raw = RAW.encode()
    assert parse(raw + b" " * (MAX_NODE_EXCHANGE_BYTES - len(raw))).kind == "declare"
    with patch("pipeline.node_exchange.json.loads") as loads:
        values: list[Any] = [b" " * (MAX_NODE_EXCHANGE_BYTES + 1), RAW, bytearray(raw), [], None]
        for value in values:
            with pytest.raises(ValueError, match="^Invalid node exchange event$"):
                parse(value)
        loads.assert_not_called()


def test_intrinsic_bytes_length_and_snapshot_ignore_subclass_overrides() -> None:
    copy_calls = 0

    class SpoofedBytes(bytes):
        def __len__(self) -> int:
            return 0

        def __bytes__(self) -> bytes:
            nonlocal copy_calls
            copy_calls += 1
            return b" " * (MAX_NODE_EXCHANGE_BYTES + 1 - len(RAW)) + RAW.encode()

    oversized = SpoofedBytes(b" " * (MAX_NODE_EXCHANGE_BYTES + 1 - len(RAW)) + RAW.encode())
    with patch("pipeline.node_exchange.json.loads") as loads:
        with pytest.raises(ValueError, match="^Invalid node exchange event$"):
            parse(oversized)
        loads.assert_not_called()
    assert copy_calls == 0
    supplied = SpoofedBytes(RAW.encode())
    assert prepare(supplied).original_bytes == RAW.encode()
    assert copy_calls == 0


def test_container_depth_and_surrogates_before_full_parse() -> None:
    candidates = [
        ('{"x":' + "[" * 11 + "0" + "]" * 11 + "}", True),
        ('{"x":' + "[" * 12 + "0" + "]" * 12 + "}", False),
        ('{"x":"\\ud83d\\ude00"}', True),
        ('{"x":"\\ud83d"}', False),
        ('{"\\ude00":0}', False),
    ]
    original = json.loads
    for text, full_parse in candidates:
        with patch("pipeline.node_exchange.json.loads", wraps=original) as loads:
            with pytest.raises(ValueError, match="^Invalid node exchange event$"):
                parse(text.encode())
            assert any(call.args[0] == text for call in loads.call_args_list) == full_parse


def test_generic_errors_have_no_private_values_cause_or_context() -> None:
    sentinel = "fictional-private-value-must-not-be-echoed"
    for value in [f'{{"{sentinel}":"{sentinel}"'.encode(), candidate(**{sentinel: sentinel})]:
        for operation in (parse, prepare):
            with pytest.raises(ValueError) as raised:
                operation(value)
            assert str(raised.value) == "Invalid node exchange event"
            assert raised.value.__cause__ is None
            assert raised.value.__context__ is None
    assert node_exchange_schema()["discriminator"]["propertyName"] == "kind"


def test_exact_bytes_digest_and_immutable_snapshots() -> None:
    first = prepare(RAW.encode())
    assert first.sha256 == CORPUS["camera_sha256"]
    assert first.original_bytes == RAW.encode()
    assert identity(slot(first), []) == "new"
    assert identity(slot(first), [slot(first)]) == "retry"
    for alternate in [
        RAW + "\n",
        RAW.replace('"depth_top_cm":0', '"depth_top_cm":0.0'),
        RAW.replace('"event_id"', '"event\\u005fid"'),
    ]:
        changed = prepare(alternate.encode())
        assert changed.event == first.event
        with pytest.raises(ValueError, match="^Node exchange conflict$"):
            identity(slot(changed), [slot(first)])
    assert isinstance(first.event, NodeExchangeDeclaration)
    with pytest.raises(ValueError):
        first.event.payload.context.depth_bottom_cm = 20
    if first.event.payload.measurement.kind == "camera_rgb":
        assert isinstance(first.event.payload.measurement.mean_rgb, tuple)


def test_uuid_letter_case_normalization_and_distinct_retry_bytes() -> None:
    identifier = "abcdefab-cdef-abcd-efab-cdefabcdefab"
    fields = dict(
        event_id=identifier,
        source_peer_id=identifier,
        destination_peer_id=identifier,
        scope_id=identifier,
    )
    lower = prepare(candidate(**fields))
    upper = prepare(
        candidate(
            **(fields | {"event_id": identifier.upper(), "source_peer_id": identifier.upper()})
        )
    )
    assert upper.event == lower.event
    with pytest.raises(ValueError, match="^Node exchange conflict$"):
        identity(slot(upper), [slot(lower)])
    normalized = slot(lower).model_dump(mode="json")
    normalized.update(event_id=identifier.upper(), stream=[identifier.upper()] * 3)
    assert identity(NodeExchangeSlot.model_validate(normalized), [slot(lower)]) == "retry"
    payload = json.loads(RAW)["payload"]
    payload.update(sample_handle=identifier, measurement_handle=identifier)
    payload["measurement"]["device_id"] = identifier
    binding = bind(declare(payload=payload), [])
    payload.update(sample_handle=identifier.upper(), measurement_handle=identifier.upper())
    payload["measurement"]["device_id"] = identifier.upper()
    assert bind(declare(payload=payload), [binding]) == binding


def test_immutable_event_and_slot_ownership() -> None:
    first = slot(prepare(RAW.encode()))
    changes: list[dict[str, Any]] = [
        dict(event_id=uuid(50)),
        dict(scope_id=uuid(51)),
        dict(source_peer_id=uuid(52)),
        dict(destination_peer_id=uuid(53)),
        dict(stream_sequence=1, previous_event_sha256=first.sha256),
    ]
    for change in changes:
        with pytest.raises(ValueError, match="^Node exchange conflict$"):
            identity(slot(prepare(candidate(**change))), [first])
    upper = first.model_dump(mode="json")
    upper["event_id"] = upper["event_id"].upper()
    upper["stream"] = [value.upper() for value in upper["stream"]]
    assert identity(NodeExchangeSlot.model_validate(upper), [first]) == "retry"


def test_binding_tuple_and_monotonic_synthetic_restriction() -> None:
    original = declare()
    binding = bind(original, [])
    payload = original.payload.model_dump(mode="json")
    repeated = declare(event_id=uuid(55), payload=payload | {"synthetic_claim": False})
    assert bind(repeated, [binding]).synthetic_restricted
    equivalent = json.loads(RAW.replace('"depth_top_cm":0', '"depth_top_cm":0.0'))
    equivalent["event_id"] = uuid(56)
    assert bind(declare(**equivalent), [binding]) == binding
    for changed in [
        payload | {"sample_handle": uuid(57)},
        payload | {"context": payload["context"] | {"depth_bottom_cm": 6}},
        payload | {"measurement": payload["measurement"] | {"source_sha256": "f" * 64}},
    ]:
        with pytest.raises(ValueError, match="^Node exchange conflict$"):
            bind(declare(event_id=uuid(58), payload=changed), [binding])
    supplied = copy.deepcopy(binding)
    copied = bind(repeated, [supplied])
    assert copied.context is not supplied.context
    assert copied.measurement is not supplied.measurement
    assert copied.context.depth_bottom_cm == 5


def test_chain_gaps_and_independent_retirement_aliases() -> None:
    first = prepare(RAW.encode())
    second = prepare(
        candidate(event_id=uuid(60), stream_sequence=1, previous_event_sha256=first.sha256)
    )
    third = prepare(
        candidate(
            kind="retire",
            event_id=uuid(61),
            stream_sequence=2,
            previous_event_sha256=second.sha256,
            payload={"sample_handle": uuid(5), "measurement_handles": []},
        )
    )
    key = stream(first.event)
    gapped = advance(key, None, [slot(third)])
    assert gapped.head is None and gapped.advanced == 0 and gapped.gap
    refusal = aliases(third.event)
    assert refusal is not None
    assert set(refusal.model_dump()) == {"stream", "sample_handle", "measurement_handles"}
    assert covered(declare(), [refusal])
    assert not covered(declare(scope_id=uuid(70)), [refusal])
    partial = advance(key, None, [slot(first), slot(third)])
    assert partial.head is not None and partial.head.stream_sequence == 0
    assert partial.advanced == 1 and partial.gap
    complete = advance(key, partial.head, [slot(third), slot(second)])
    assert complete.head is not None and complete.head.stream_sequence == 2
    assert complete.head.sha256 == third.sha256 and complete.advanced == 2 and not complete.gap
    for conflict in [
        slot(second).model_copy(update={"previous_event_sha256": "f" * 64}),
        slot(first).model_copy(update={"sha256": "f" * 64}),
    ]:
        with pytest.raises(ValueError, match="^Node exchange conflict$"):
            advance(key, partial.head, [conflict])
