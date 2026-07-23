# WP-SITE-1D — globalsoilintelligence.com cutover proposal

Status: **PREPARED FOR REVIEW; NOT EXECUTED.** Signed-in account preflight is complete; approval to generate the ownership-verification request remains pending. Preparation requested by Justin on October 15, 2026. The evidence was refreshed October 16 UTC (October 15 in New York).

## Invariants and intended change

- Serve the already approved Pages artifact from `https://globalsoilintelligence.com/`; use the apex as canonical and redirect `www` to it.
- Capture and library uploads remain closed. The deployed activation manifest was freshly read and is exactly `{"capture_live":false,"library_intake_live":false}`.
- Keep the existing `github-pages` environment: Justin (`jdhart81`) is its required reviewer, and administrators cannot bypass approval.
- Preserve nameservers, DNSSEC, domain registration, subscriptions and every unrelated DNS record, including mail and ownership records. No Supabase, Auth, worker, source, licence, merge or further deployment changes.
- Add only the approved web-routing records and a separately reviewed GitHub-generated verification TXT. Stop on any unexpected record, account state, deployment or activation mismatch.

## Verified baseline

The four authoritative nameservers agree:

`ns-cloud-d1.googledomains.com`, `ns-cloud-d2.googledomains.com`, `ns-cloud-d3.googledomains.com`, `ns-cloud-d4.googledomains.com`.

Public registry: **Squarespace Domains LLC**. Public website: HTTP 200, title **Coming Soon**, heading `globalsoilintelligence.com`.

| Record | Current value | Current TTL |
|---|---|---:|
| `@` A | `198.49.23.144` | 14,400 seconds (4 hours) |
| `www` CNAME | `ext-sq.squarespace.com.` | 14,400 seconds (4 hours) |
| `@` AAAA | No answer | — |
| `@` MX, TXT, CAA | No answers at these queried names | — |
| `_github-pages-challenge-global-soil-intelligence` TXT | No answer | — |

These are named public lookups, **not a full zone export**. They do not prove that other subdomains or mail records are absent. The authenticated panel has now been read and saved in `signed-in-account-readback.json`: the two web records match, and the panel has one additional CNAME `_domainconnect` → `_domainconnect.domains.squarespace.com` (TTL 3,600) under Squarespace Domain Connect. Preserve that record and group. The panel says No custom records. Its nameserver list matches all four authoritative servers. Refresh this inventory before any edit; stop on a mismatch.

GitHub Pages is built with `build_type=workflow`, `cname=null`, and `https_enforced=true` for its current default address. Run [38821460183](https://github.com/global-soil-intelligence/gsip/actions/runs/38821460183) succeeded at main `73088050d6fc68baedf893990ab3fbe76d5e749c`. Its artifact is SHA256 `2bc0829549d98331c7a8dc5e451b6e5457125fd5863f166e63ce1ea90a4cde33`. The deployed site is [global-soil-intelligence.github.io/gsip/](https://global-soil-intelligence.github.io/gsip/).

All three Vite configurations use relative base `./`; capture's manifest uses relative `start_url`. Canonical links, sitemap and robots already name the apex. No source change or rebuild is proposed. The root Pages artifact was verified in the preceding release; custom-domain routing and its certificate are **not yet verified**.

## Account and verification prerequisites

Update after Justin opened the signed-in Chrome tab: both account panels are accessible and were inspected read-only. Earlier sign-in screens are superseded by the following readback:

- [Squarespace DNS panel](https://account.squarespace.com/domains/managed/globalsoilintelligence.com/dns/dns-settings): the complete displayed inventory is three records, matching the two traffic records plus the preserved Domain Connect record. Nameservers match. The two traffic records belong to the Squarespace Defaults group; if removal is later approved, remove only that group containing exactly those two records. Do not remove Squarespace Domain Connect or replace the whole zone.
- [Organization Pages settings](https://github.com/organizations/global-soil-intelligence/settings/pages): the signed-in panel states There are no verified domains for this organization. No existing challenge was displayed. The Add a verified domain form is populated with `globalsoilintelligence.com` but has **not** been submitted. This is Pages domain verification, separate from GitHub's organization badge verification.

If there is no existing challenge, obtaining one means **Add a domain → globalsoilintelligence.com** in organization Pages settings. That action has not been taken. The exact TXT value is consequently unavailable and has not been invented or preapproved.

Proposed ownership record, requiring the actual value to be shown before approval to save it:

| Type | Host in provider panel | Fully qualified name | Value | TTL |
|---|---|---|---|---:|
| TXT | `_github-pages-challenge-global-soil-intelligence` | `_github-pages-challenge-global-soil-intelligence.globalsoilintelligence.com.` | GitHub-generated challenge: **pending** | 3,600 |

Verify the TXT on all four nameservers, then complete GitHub's Verify action and read the result back. Keep this TXT permanently. Verification is the recommended prerequisite to this cutover; failure or another organization's claim stops the work. [GitHub verification instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages).

## Exact traffic-record changes proposed for approval

Delete only these two existing web records:

| Type | Host | Value |
|---|---|---|
| A | `@` | `198.49.23.144` |
| CNAME | `www` | `ext-sq.squarespace.com.` |

Replace them with these nine records, all at proposed TTL **3,600 seconds (1 hour)**:

| Type | Host | Value |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| AAAA | `@` | `2606:50c0:8000::153` |
| AAAA | `@` | `2606:50c0:8001::153` |
| AAAA | `@` | `2606:50c0:8002::153` |
| AAAA | `@` | `2606:50c0:8003::153` |
| CNAME | `www` | `global-soil-intelligence.github.io.` |

The CNAME has no scheme, path or repository suffix. No apex CNAME, wildcard, forwarding rule or nameserver change is proposed. These are [GitHub's current published records](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site). Squarespace supports editing custom TTLs; if the actual panel cannot accept 1 hour for these records, stop and show the available choice before saving. [Squarespace DNS documentation](https://support.squarespace.com/hc/en-us/articles/360002101888-Edit-your-domain-s-DNS-records).

## Execution order after explicit approval

1. Refresh the exact DNS, complete zone inventory, verified ownership, Pages run/source and both closed flags. Stop on a mismatch. The review of public DNS so far is not permission to edit it.
2. Bind the domain to this repository **before** changing traffic DNS. The following requests are proposed only; do not run them during preparation:

   ```sh
   gh api --method PUT repos/global-soil-intelligence/gsip/pages \
     -f cname=globalsoilintelligence.com
   gh api repos/global-soil-intelligence/gsip/pages
   ```

   Require `cname=globalsoilintelligence.com`, the same workflow source and the existing approval protection. Do not add a committed CNAME file; this Actions publishing mode does not need one.
3. In the authenticated DNS panel, replace only the two listed records with the nine listed records. Save and read back each affected record set. Existing records are cached for 4 hours; setting new TTLs to 1 hour does not shorten already cached answers. No advance TTL change is included. Allow up to 24 hours for propagation and certificate readiness; temporary mixed old/new views or HTTPS unavailability are possible.
4. Confirm all four authoritative servers, then independent recursive resolvers, give the exact expected A/AAAA/CNAME sets. Read GitHub DNS health:

   ```sh
   gh api repos/global-soil-intelligence/gsip/pages/health
   gh api repos/global-soil-intelligence/gsip/pages
   ```

   Wait for a trusted certificate that covers apex and `www`; never disable certificate validation. The current default-domain HTTPS setting does not prove custom-domain certificate readiness. No CAA record is proposed because none was returned; a new restrictive CAA finding stops the work for review. [GitHub HTTPS instructions](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https).
5. Once the custom certificate is ready, retain or reassert HTTPS enforcement and read back:

   ```sh
   gh api --method PUT repos/global-soil-intelligence/gsip/pages \
     -F https_enforced=true
   gh api repos/global-soil-intelligence/gsip/pages
   ```

   This uses [GitHub's documented Pages settings API](https://docs.github.com/en/rest/pages/pages#update-information-about-a-github-pages-site). It does not dispatch a deployment or modify a branch.
6. Verify HTTPS apex serves the reviewed artifact; HTTP and `www` redirect to HTTPS apex. Check the previous GitHub URL and a nested path redirect without duplicated `/gsip/`. Compare all 38 deployed files against the approved artifact at their new root. Check the homepage, map, methods, data, card, about, reference-card PDF, share image, `robots.txt`, `sitemap.xml` and `llms.txt`; canonical URLs must resolve. Test visible navigation, asset loading, PWA manifest/service-worker scope and browser console errors.
7. Read `https://globalsoilintelligence.com/capture/gsip-activation.json`: require exactly both booleans false. Inspect capture in a clean browser: closed notice, no submission form, upload control or sign-in attempt. Do not test a real submission. Save immutable evidence and the completed/blocked checklist.

## Rollback proposed for review

This is a documented recovery plan, **not an executed action or implicit authority**. If a mismatch arises during execution, stop and report. Run rollback only if included in the explicit go or separately authorized.

Restore `@` A to the single `198.49.23.144` record and `www` CNAME to `ext-sq.squarespace.com.`, both TTL 14,400. Remove only the four added GitHub A and four AAAA records. Preserve the verification TXT, all unrelated records and subscriptions. Confirm all four nameservers have restored records; wait at least the added records’ 3,600-second TTL after authoritative convergence, then check named independent resolvers (Cloudflare `1.1.1.1` and Google `8.8.8.8`) before unbinding the repository domain. This sample cannot prove that every worldwide cache has expired. Keep the verified ownership TXT and the GitHub domain claim during the transition.

Once routing has returned to Squarespace, remove the Pages custom-domain setting with the prepared JSON body `{"cname":null}`; sending a JSON null is required, not the string `"null"`. Then read Pages back, confirm `cname=null`, default-site HTTPS enforcement, the original `github.io/gsip/` address, successful artifact delivery and the closed flags. If settings require a new Pages deployment, that is a separate approval; do not dispatch automatically. Rollback cannot instantly clear third-party DNS caches.

## Assumptions, holds and evidence

- Apex is the canonical address requested by Justin; `www` is a redirect. Dual-stack IPv4/IPv6 is proposed explicitly above.
- The parked Squarespace page should be replaced; its subscription and domain registration should stay intact. This plan does not cancel, transfer or delete them.
- The signed-in DNS panel and nameserver list now match public DNS. Its three-record inventory is saved; refresh it before execution.
- A safe cutover requires organization Pages ownership verification. The generated TXT value and its approval remain pending. Account sign-in and the displayed complete zone inventory are now verified. Traffic records above are exact; the pending TXT is not presented as executable.
- No code changed; no new implementation tests were appropriate. Current GitHub deployment success, current public DNS and current closed activation were checked. Custom-domain, HTTPS, redirect, browser and 38-file checks after cutover remain **not run**.
- Machine-readable proposal: `proposed-changes.json`. Public evidence: `authoritative-dns-preflight.json` (48 queries), `registrar-preflight.json`, `http-preflight.json`, `github-pages-preflight.json`, `pages-environment-preflight.json`, `pages-run-preflight.json`. No credentials, contributor records or coordinates were collected.

## Next narrow approval

May Codex submit **Add domain** for `globalsoilintelligence.com` in the `global-soil-intelligence` organization Pages verification form to generate the exact TXT challenge? This saves a pending verification request only. DNS routing, repository custom-domain binding, deployments, capture and library uploads remain unchanged. The exact generated TXT will be shown for approval before it is added to DNS. This pause follows Justin’s prepare-for-approval instruction because the button saves organization settings.
