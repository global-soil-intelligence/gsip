"""Public photo attribution (WP-6b, WP-6d). Mirrors `packages/schema/src/attribution.ts`."""

from __future__ import annotations

DEFAULT_ATTRIBUTION = "Anonymous soil contributor"


def photos_publishable(attribution_name: str, review_decision: str | None) -> bool:
    """Photos publish under the default pseudonym, or a typed name a reviewer approved for that
    contributor. Anything else (pending or rejected) releases the observation without photos."""

    return attribution_name == DEFAULT_ATTRIBUTION or review_decision == "approved"
