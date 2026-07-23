# Merge metadata audit — exception proposed, not approved

All 13 merges were explicitly authorised by Justin and gated on current-head green CI.
My authored fix and local forward-merge commits use Conventional Commits and the Codex trailer.
I omitted explicit subject/body options when executing GitHub merges. GitHub generated its standard
merge titles and omitted the required Codex Co-Authored-By trailer. This does not satisfy the
original commit-metadata rule. It cannot be corrected in those commits without rewriting merged
history, which is prohibited. No history rewrite has been attempted.

Proposed disposition: retain immutable history and accept a narrow metadata exception only for
the 13 merge commits below. Future agent-executed GitHub merges must explicitly supply a
Conventional Commit subject and a body file containing the Codex trailer. No DCO or review
approval is implied; no production authority changes.

| PR | Merge commit | Trailer |
| --- | --- | --- |
| [#28](https://github.com/global-soil-intelligence/gsip/pull/28) | `517bc1d13118b09d5c8c02973e9e8f04744e13a0` | Missing |
| [#29](https://github.com/global-soil-intelligence/gsip/pull/29) | `55d89764375bacaebfcb49662826bc3e6bc2bdb4` | Missing |
| [#30](https://github.com/global-soil-intelligence/gsip/pull/30) | `f84f8464c5dee21d68e0b362ebc64c50c3cbf412` | Missing |
| [#31](https://github.com/global-soil-intelligence/gsip/pull/31) | `acf10eb41d22c043ffa6f8b6b9af6c1815e96138` | Missing |
| [#32](https://github.com/global-soil-intelligence/gsip/pull/32) | `7449070d25111340d8c8200bfda38c5735052fb8` | Missing |
| [#33](https://github.com/global-soil-intelligence/gsip/pull/33) | `02c2ccb91ad8da1e4a6f7325cb2e9087e93b4efc` | Missing |
| [#34](https://github.com/global-soil-intelligence/gsip/pull/34) | `766423725819e77bfc7fa114b8a28f52974f3bb0` | Missing |
| [#35](https://github.com/global-soil-intelligence/gsip/pull/35) | `e72ecd1901c676da249ae39fe14b6f57f5268eb4` | Missing |
| [#36](https://github.com/global-soil-intelligence/gsip/pull/36) | `0bde5e7529580b9bbb389070aa824ce853ebc874` | Missing |
| [#37](https://github.com/global-soil-intelligence/gsip/pull/37) | `7f017dc68c58021dd7a8f227d61a9fa2adc386a1` | Missing |
| [#38](https://github.com/global-soil-intelligence/gsip/pull/38) | `3cdd8c238399c138655feedb997b72d6c40186cf` | Missing |
| [#39](https://github.com/global-soil-intelligence/gsip/pull/39) | `b42cb67965891265beeb432c4b03171588ea72f6` | Missing |
| [#40](https://github.com/global-soil-intelligence/gsip/pull/40) | `665506fd7a2e4d972bb9fe03c4faf0f174c4675b` | Missing |
