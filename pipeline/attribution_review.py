"""Review typed attribution names before their photos are published (WP-6d).

A photo is published under the default pseudonym, or under a name a steward approved for that
contributor; until then the observation is released without photos (SPEC section 6).

    python -m pipeline.attribution_review list
    python -m pipeline.attribution_review approve --contributor ID --name NAME --reviewer YOU
    python -m pipeline.attribution_review reject --contributor ID --name NAME --reviewer YOU \\
        --note "impersonates a public figure"

(prefix each with `uv run`; the service-role environment variables must be set).

Names are written by contributors: the list shows them ASCII-escaped, so a name can never
inject terminal control sequences or pass for instructions.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TextIO

import httpx

from pipeline.attribution import DEFAULT_ATTRIBUTION

DECISIONS = ("approved", "rejected")


@dataclass(frozen=True)
class PendingName:
    contributor_id: str
    attribution_name: str
    first_accepted_at: str
    grants: int


class UnknownName(ValueError):
    """The contributor never used this exact name, so there is nothing to review."""


class AttributionReviews:
    def __init__(self, url: str, service_key: str) -> None:
        self.url = url.rstrip("/")
        self.client = httpx.Client(
            timeout=30,
            headers={"Authorization": f"Bearer {service_key}", "apikey": service_key},
        )

    def _get(self, path: str, params: dict[str, str]) -> list[dict[str, Any]]:
        response = self.client.get(f"{self.url}/rest/v1/{path}", params=params)
        response.raise_for_status()
        rows: list[dict[str, Any]] = response.json()
        return rows

    def pending(self) -> list[PendingName]:
        rows = self._get(
            "attribution_review_queue",
            {
                "order": "first_accepted_at",
                "select": "contributor_id,attribution_name,first_accepted_at,grants",
            },
        )
        return [
            PendingName(
                contributor_id=str(row["contributor_id"]),
                attribution_name=str(row["attribution_name"]),
                first_accepted_at=str(row["first_accepted_at"]),
                grants=int(row["grants"]),
            )
            for row in rows
        ]

    def decide(
        self,
        contributor_id: str,
        attribution_name: str,
        decision: str,
        reviewer: str,
        note: str | None = None,
    ) -> None:
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}")
        if not 1 <= len(reviewer.strip()) <= 80:
            raise ValueError("name the reviewer (1-80 characters)")
        if attribution_name == DEFAULT_ATTRIBUTION:
            raise ValueError("the default pseudonym needs no review")
        used = {
            str(row["attribution_name"])
            for row in self._get(
                "contribution_grants",
                {"contributor_id": f"eq.{contributor_id}", "select": "attribution_name"},
            )
        }
        if attribution_name not in used:
            raise UnknownName("this contributor never used that exact name")
        response = self.client.post(
            f"{self.url}/rest/v1/attribution_reviews",
            params={"on_conflict": "contributor_id,attribution_name"},
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
            json={
                "attribution_name": attribution_name,
                "contributor_id": contributor_id,
                "decision": decision,
                "note": note,
                "reviewed_at": datetime.now(UTC).isoformat(),
                "reviewer": reviewer.strip(),
            },
        )
        response.raise_for_status()


def render(pending: list[PendingName], out: TextIO) -> None:
    if not pending:
        print("No attribution names are waiting for review.", file=out)
        return
    for item in pending:
        print(
            f"{item.contributor_id}  {ascii(item.attribution_name)}  "
            f"first used {item.first_accepted_at}  ({item.grants} grant(s))",
            file=out,
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Review GSIP photo attribution names")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="names waiting for review")
    for decision in ("approve", "reject"):
        command = commands.add_parser(decision, help=f"{decision} a name for one contributor")
        command.add_argument("--contributor", required=True)
        command.add_argument("--name", required=True)
        command.add_argument("--reviewer", required=True)
        command.add_argument("--note")
    args = parser.parse_args(argv)
    reviews = AttributionReviews(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    )
    if args.command == "list":
        render(reviews.pending(), sys.stdout)
        return
    decision = "approved" if args.command == "approve" else "rejected"
    try:
        reviews.decide(args.contributor, args.name, decision, args.reviewer, args.note)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f"{decision} {ascii(args.name)} for {args.contributor}")


if __name__ == "__main__":
    main()
