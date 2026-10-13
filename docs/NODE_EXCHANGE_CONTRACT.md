# Private node exchange contract (LIB-5A)

LIB-5A implements pure validation and supplied synthetic integrity facts under
[SPEC §16.9–16.13](SPEC.md#169-lib-5-boundary-and-invariants). It performs no I/O,
reads no credential or environment variable, authenticates no peer and grants no
use, sharing, training or publication permission. LIB-5B owns the separately
reviewed synthetic filesystem simulator; real authority, transport and retention
remain held for LIB-5C. Existing LIB-1/4 contracts are unchanged.

`parseNodeExchangeEvent(bytes)` in `@gsip/schema` and
`parse_node_exchange_event(bytes)` in Python accept only byte buffers and return
normalized immutable declarations or retirements. The input must be strict UTF-8
JSON, at most 2,000,000 bytes inclusive. Size is checked before copying/decoding;
the actual size and snapshot use intrinsic byte-buffer operations so subclass
accessor/conversion overrides cannot evade the bound or replace retry bytes.
A bounded preflight refuses more than 12 simultaneous object/array containers before
full JSON parsing. The root container counts as one; primitives add none. BOM,
malformed UTF-8, duplicate decoded keys and unpaired Unicode surrogates are
refused. Valid escaped surrogate pairs pass syntax preflight; they do not bypass
the contract's exact fields and ASCII vocabularies. Unicode is never normalized.

UUIDs use case-insensitive canonical 36-character hexadecimal text and normalize
to lowercase for comparison, with no version/variant claim. Digests are lowercase
64-hex text. `stream_sequence` and camera `pixel_count` require unsigned decimal
integer JSON tokens within their bounds, checked before conversion. Spellings
such as `1.0`, `1e0` and `-0`, strings and booleans are refused for those fields.
Other scientific numbers retain LIB-1's finite-value bounds. The exported
`NodeExchangeEventSchema` and Python `node_exchange_schema()` describe semantic
validation; already-decoded values/JSON Schema cannot establish raw byte, duplicate
key, nesting or integer spelling compliance. Use the byte parser at intake.

`prepareNodeExchangeEvent` uses built-in WebCrypto and snapshots input before its
hashing await. It returns a frozen event, the original-byte SHA-256 and
`originalBytes()`, which returns a fresh copy. Python's
`prepare_node_exchange_event` returns immutable original bytes, SHA-256 and frozen
typed models. No retained event is reserialized for retry identity. Whitespace,
escape spelling, UUID case and numeric spelling changes conflict when an event
identity or sequence slot already exists, even when validated fields are equal.
This convention supplies neither a signature nor cross-language canonical JSON.

The remaining helpers consume supplied synthetic facts only:

- `nodeExchangeStream` / `node_exchange_stream`: normalized source, destination
  and scope tuple, distinct from LIB-1/4 library namespaces.
- `nodeExchangeSlot` / `node_exchange_slot` and `checkNodeExchangeIdentity` /
  `check_node_exchange_identity`: immutable stream/slot/event ownership and exact
  digest retry/conflict checks. These fact helpers cannot authenticate their inputs.
- `bindNodeExchangeMeasurement` / `bind_node_exchange_measurement`: immutable
  stream/sample/measurement ownership and protocol/context/scientific field-value
  equality. Returned scientific values are independent immutable snapshots. A
  synthetic restriction can grow and cannot be cleared by a false claim; a repeat
  supplies no independent evidence or field verification.
- `advanceNodeExchangeHead` / `advance_node_exchange_head`: only consecutive
  supplied slots with matching predecessor digests advance a committed head.
  Missing predecessors hold the gap; a conflicting predecessor raises a generic
  conflict. No reset or fabricated predecessor is supplied.
- `nodeExchangeRetirementAliases` / `node_exchange_retirement_aliases` and
  `nodeExchangeDeclarationCovered` / `node_exchange_declaration_covered`: minimal
  alias coverage independent of chain commitment. The sample refusal is sample-wide;
  additional measurement aliases never limit that coverage. Parsing/classification
  alone does not apply or authenticate a retirement. Durable refusals, erasure and
  authenticated synthetic/real admission remain later-package responsibilities.

Byte and helper boundary errors are generic and attach no input-bearing cause.
Decoded semantic validation also refuses throwing getters/proxies with only a
generic custom schema issue; prepared values and supplied fact collections are
accessed inside the same generic helper-error boundary. TypeScript fact collections
must be arrays; Python accepts typed sequences. Error containment does not replace
their strict validation.
Python internal model classes are typed values, not a replacement raw intake
boundary. The shared fictional corpus exercises both languages, including strict
integer spellings, forbidden authority/private fields, malformed/deep/oversized
inputs, digest conflicts, immutable bindings, gaps and retirement-first coverage.
All fixtures are synthetic. Passing these checks establishes software behavior
only; capture, photo-publication, field-training and production gates stay closed.
