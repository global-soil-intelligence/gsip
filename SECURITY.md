# Security policy

## Report a vulnerability

Report privately through GitHub: https://github.com/global-soil-intelligence/gsip/security/advisories/new

Please don't open a public issue for a suspected vulnerability, a leaked credential, or any exposure of contributor data. We acknowledge reports within 5 business days and agree a fix and disclosure date with you.

## What we most want to hear about

GSIP's main promise is that contributors cannot be located or identified from anything public. Treat any of these as a vulnerability:

- A precise coordinate, or anything finer than the published H3 cell, reachable from a public table, API, map tile, dataset release, log, URL or image byte.
- Image metadata (EXIF, XMP, ICC, comments, maker notes, C2PA manifests) surviving into canonical storage or a release.
- A way to read, overwrite or delete another contributor's rows or Storage objects, or to make a privileged worker act on a path it should not (path traversal, unbound storage paths).
- A row-level-security or grant bypass, including through Edge Functions or remote procedure calls.
- An agent-facing interface (`gsip-public`, MCP, `llms.txt`) returning anything the anonymous role cannot read, or carrying instructions that an agent would follow from people-written text (prompt injection).
- A way around the capture gate, quotas or upstream rate limits at scale.
- A way to publish synthetic or fabricated observations as field data, or to raise a provenance tier without evidence.

## Scope

In scope: the code in this repository, and the canonical hosted service built from it (the Supabase project, Edge Functions, the GitHub Pages site and the Hugging Face dataset). Out of scope: volume denial-of-service testing, social engineering, physical attacks, and already-public issues in third-party dependencies (report those upstream).

## Good-faith research

We won't pursue action against research that follows this policy, stays within accounts and data you own, avoids privacy harm and service disruption, never downloads more contributor data than needed to demonstrate the issue, and gives us reasonable time to fix before disclosure. Do not attempt to locate or contact real contributors.

## Trust boundary

- The service-role key, contributor precise locations, raw uploads and private photo metadata never leave the server side. They are never committed, never shipped to browsers or apps, and never given to agent interfaces.
- Self-hosted deployments use their own Supabase projects and keys. Only the canonical deployment publishes the official dataset releases.
- If a credential is ever committed, treat it as compromised: revoke it, rotate it, and audit what it could reach.
