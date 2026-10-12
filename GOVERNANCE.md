# Governance

GSIP is an open commons stewarded by Viridis LLC. This document says who decides, how the hosted service may earn money, and how the community can verify that money never bends the mission.

## Decisions

Justin Hart is the product owner and final decision-maker during the bootstrap phase. Changes land through protected pull requests after automated checks, independent adversarial review, one non-author GitHub approval, and the product owner's go/no-go.

Architecture changes require a specification update (`docs/SPEC.md`) before implementation. Privacy and agent invariants I5, I7 and I12 are reviewed on every pull request.

As the external community grows, the product owner will convene an **advisory council** (contributors, partner labs, educators and at least one independent member), then document a **steering group** that takes over routine technical decisions. Changes to this document need a pull request open for at least 14 days with the advisory council consulted once it exists.

## Steward

Viridis LLC runs the canonical hosted service and may earn revenue from services and goods around the commons. The commons is the code (MIT), the database and structured data (ODbL 1.0), the contributed photos (CC BY-SA 4.0) and the released model weights. Viridis does not own the commons and cannot close it; anyone may fork it under its licenses.

## Business guardrails

Every revenue activity connected to GSIP must satisfy all eight guardrails. Each one names the check that lets anyone verify it.

| ID  | Guardrail                                                                                                                                                                 | Check                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| B1  | **The commons stays free and forkable.** Code, data, photos and model weights stay open, and the full stack deploys on free tiers.                                        | No paid tier gates released data or weights; the default deployment has no paid dependency (BUILD_ORDER guardrail 6). |
| B2  | **Pay for service, never for access, exclusivity or truth.** Sponsors may speed up collection where they need it; they cannot buy embargoes, private data or QA outcomes. | No embargo field exists; sponsored observations carry a public campaign tag.                                          |
| B3  | **Contributors never pay to contribute.** People, schools, researchers, nonprofits, and agents acting for them use the app and API free within fair quotas.               | The capture flow has no paywall; free quotas live in the database.                                                    |
| B4  | **Money never touches scientific judgment.** QA, consensus and model evaluation run without knowing who paid.                                                             | Those code paths take no campaign, customer or payment input.                                                         |
| B5  | **Privacy is not for sale.** No advertising, trackers, data brokering or precise locations, ever.                                                                         | The I7 export assertions, plus a dependency review that rejects advertising and tracking SDKs.                        |
| B6  | **Pay in dollars or in data.** Commercial users either pay, or earn access through verified contributions.                                                                | A public credit ledger per actor once credits exist.                                                                  |
| B7  | **Open books.** A yearly public statement of the commons' costs and revenue, and a fixed share of GSIP revenue returned to the commons.                                   | The statement is published in this repository each year.                                                              |
| B8  | **Share-alike is honoured.** Viridis products use GSIP data as produced works, or publish derived databases under ODbL 1.0.                                               | A license review before each product launch, recorded in the open books.                                              |

**Commons share.** 10 % of GSIP revenue goes to the commons fund. GSIP revenue means revenue from GSIP-branded goods and services, less pass-through costs (laboratory fees, shipping, payment processing and app-store fees). The commons fund pays for contributor rewards, school grants, hosting, and Most Wanted cells no sponsor pays for. Until a fiscal host is chosen, Viridis records the share as a liability in the open books.

## Conflict rules

- Every contract between the commons fund and Viridis is published and approved by an independent advisor before signature.
- Assurance work Viridis sells on GSIP data stays auditable: the underlying observations are public, and assurance reports receive independent review.
- Contributor terms permit relicensing only to more open licenses, never to proprietary ones.
- Sponsored campaigns are tagged publicly and weighted by information gain; part of the commons share funds unsponsored cells so that sponsors do not decide alone where the map is good.

## Names and marks

The licenses cover code, data and photos, not the project's names, logos or certification marks. See `TRADEMARKS.md`.

## Agents

Agents participate through a human of record (SPEC I9). An agent cannot accept terms, approve a pull request, certify the DCO or vote. Agent-authored changes are adopted and signed off by the human who reviews them.
