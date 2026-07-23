# CI assertion performance correction

The first COLLECT-4A CI run, 38993810652 at d379490209a61b4dc3caac7c5b17d84bcaa96322, failed only the existing five-second timeout in the synthetic oversized-declaration refusal case. 443 of 444 capture tests passed. The historical failed run is retained.

Isolated local measurement identified the generic deep-equality assertion, not the runtime guard: saving the synthetic context took approximately 0.82 ms, refusing the handoff 1.12 ms, and the generic preservation assertion 1804.85 ms. The test used 2,000,001 synthetic bytes. No contributor data was used. Temporary timing instrumentation was removed.

The test-only correction compares the complete remaining context, intrinsic typed-array kind, exact byte length and every byte through TypedArray.every. It still checks trailing bytes. Runtime code, the size cap and the five-second timeout are unchanged. No suppression, rule, workflow or dependency changed.

Root isolated rerun: 42/42 queue tests passed, 95 ms test time. Independent reviewer rerun: 42/42 passed, 105 ms. The reviewer confirmed that no assertion or guard was weakened.

After the correction, full local lint, type checking and all 811 unit tests passed (capture 444, schema 310, site 41, map 16). Fresh exact-head CI and native artifacts remain the merge gate. No production or activation changes are authorized by this correction.
