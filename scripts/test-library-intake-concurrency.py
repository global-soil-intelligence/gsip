"""Local-only two-connection withdrawal/intake races on an explicitly disposable database.

Requires the existing development Docker/psql toolchain, not a production credential.
Creates synthetic fixtures only in a database named gsip_lib4b_*; discard that database afterward.
"""

# SQL interpolates generated synthetic UUIDs through literal(), never external values.
# ruff: noqa: S608

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


@dataclass(frozen=True)
class Fixture:
    auth: str
    contributor: str
    grant: str
    submission: str
    request: dict[str, Any]


def create_fixture(command: list[str]) -> Fixture:
    auth, contributor, grant, submission = (str(uuid4()) for _ in range(4))
    terms = "lib4b-race-" + uuid4().hex
    request: dict[str, Any] = {
        "schema_version": "gsip-library-intake-v1",
        "intake_id": str(uuid4()),
        "node_id": str(uuid4()),
        "sample_id": str(uuid4()),
        "submission_id": submission,
        "protocol_version": "gsip-capture-v1",
        "context": {"depth_top_cm": 0, "depth_bottom_cm": 20, "condition": "dry"},
        "instrument_declaration": None,
    }
    photos = ",".join(
        f"({literal(str(uuid4()))},{literal(submission)},'{shot}',"
        f"{literal(auth + '/' + submission + '/' + shot + '/' + str(uuid4()) + '.jpg')})"
        for shot in ("A", "B")
    )
    sql = f"""
    insert into public.terms_versions(version,published_at)
        values({literal(terms)},now()-interval '1 day');
    insert into auth.users(id,is_anonymous) values({literal(auth)},false);
    insert into private.collection_pilot_members(auth_uid) values({literal(auth)});
    insert into public.contributors(id,auth_uid,handle)
        values({literal(contributor)},{literal(auth)},{literal("race-" + uuid4().hex[:20])});
    insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,
        attribution_name)
        values({literal(grant)},{literal(contributor)},{literal(terms)},now(),
            'Anonymous soil contributor');
    insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at,finalized_at,
        land_cover,surface_condition,disturbed,device_model)
        values({literal(submission)},{literal(contributor)},{literal(grant)},
            'SRID=4326;POINT EMPTY',now(),now(),'bare','dry',false,'synthetic race fixture');
    insert into public.photos(id,submission_id,shot_type,storage_path) values {photos};
    update public.service_state set capture_open=true;
    select public.set_library_intake_open(true);
    """
    run(command, sql)
    return Fixture(auth, contributor, grant, submission, request)


def run(command: list[str], sql: str, *, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(  # noqa: S603 - argv is the fixed local Docker/psql toolchain.
        command, input=sql, text=True, capture_output=True, timeout=30
    )
    if success and result.returncode:
        raise RuntimeError("isolated synthetic database command failed")
    return result


def caller(fixture: Fixture) -> str:
    claims = json.dumps({"sub": fixture.auth, "role": "authenticated"})
    return "set role authenticated; set request.jwt.claims=" + literal(claims) + ";"


def intake(fixture: Fixture) -> str:
    return (
        "select public.record_library_intake(" + literal(json.dumps(fixture.request)) + "::jsonb);"
    )


def withdraw(fixture: Fixture) -> str:
    return (
        "insert into public.deletion_requests(contributor_id,kind) values("
        + literal(fixture.contributor)
        + ",'withdraw_contributions');"
    )


def race(command: list[str], *, operation: str, operation_first: bool) -> dict[str, Any]:
    fixture = create_fixture(command)
    if operation == "withdrawal":
        mutation = caller(fixture) + withdraw(fixture)
    elif operation == "source_delete":
        mutation = "delete from public.submissions where id=" + literal(fixture.submission) + ";"
    else:
        mutation = f"""insert into public.gold_labels(id,submission_id,lab_name,property,value,unit,
            depth_top_cm,depth_bottom_cm,holdout) values({literal(str(uuid4()))},
            {literal(fixture.submission)},'synthetic','soc',1,'g/kg',0,20,true);"""
    admission = caller(fixture) + intake(fixture)
    first = mutation if operation_first else admission
    second = admission if operation_first else mutation
    script = "begin;" + first + "\n\\echo LIBRARY_RACE_LOCK_HELD\nselect pg_sleep(1.5); commit;\n"
    process = subprocess.Popen(  # noqa: S603 - fixed local Docker/psql toolchain.
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("race connection did not expose its local input/output")
    process.stdin.write(script)
    process.stdin.flush()
    while True:
        line = process.stdout.readline()
        if "LIBRARY_RACE_LOCK_HELD" in line:
            break
        if not line:
            process.kill()
            raise RuntimeError("first race connection failed before acquiring the lock")
    started = time.monotonic()
    terminal = operation_first and operation != "holdout"
    result = run(command, "begin;" + second + "commit;", success=not terminal)
    waited = time.monotonic() - started
    # The source transaction is still sleeping when the second connection starts.
    if waited < 0.5:
        raise RuntimeError("second connection did not wait on the expected lock")
    process.stdin.close()
    process.wait(timeout=30)
    if process.returncode:
        raise RuntimeError("first race transaction did not commit")
    if terminal:
        expected_error = "WD001" if operation == "withdrawal" else "42501"
        if result.returncode == 0 or expected_error not in result.stderr:
            raise RuntimeError("late intake was not terminally refused")
    summary = run(
        command,
        f"""select jsonb_build_object(
        'payloads',(select count(*) from private.library_intakes
            where submission_id={literal(fixture.submission)}),
        'tombstones',(select count(*) from private.library_sample_tombstones
            where node_id={literal(fixture.request["node_id"])}),
        'withdrawals',(select count(*) from public.grant_withdrawals
            where grant_id={literal(fixture.grant)}),
        'holdout',(select count(*) from private.library_sample_restrictions
            where node_id={literal(fixture.request["node_id"])} and holdout));""",
    )
    counts = json.loads(summary.stdout.strip())
    expected = {
        "payloads": 1 if operation == "holdout" else 0,
        "tombstones": 0 if operation_first or operation == "holdout" else 1,
        "withdrawals": 1 if operation == "withdrawal" else 0,
        "holdout": 1 if operation == "holdout" else 0,
    }
    if counts != expected:
        raise RuntimeError("race left incorrect payload, withdrawal, holdout or refusal state")
    order = operation + "_then_intake" if operation_first else "intake_then_" + operation
    return {"order": order, "passed": True, **counts}


def pilot_admission_race(
    command: list[str], *, operation: str, operation_first: bool
) -> dict[str, Any]:
    f = create_fixture(command)
    if operation == "revocation":
        mutation = (
            "update private.collection_pilot_members set revoked_at=now() where auth_uid="
            + literal(f.auth)
            + ";"
        )
        expected_error = "42501"
    elif operation == "capture_close":
        mutation = "update public.service_state set capture_open=false;"
        expected_error = "LI001"
    else:
        mutation = "select public.set_library_intake_open(false);"
        expected_error = "LI001"
    admission = caller(f) + intake(f)
    first, second = (mutation, admission) if operation_first else (admission, mutation)
    script = "begin;" + first + "\n\\echo PILOT_RACE_LOCK_HELD\nselect pg_sleep(1.5);commit;\n"
    process = subprocess.Popen(  # noqa: S603 - fixed disposable local PostgreSQL command.
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("pilot race connection has no local input/output")
    process.stdin.write(script)
    process.stdin.flush()
    while True:
        line = process.stdout.readline()
        if "PILOT_RACE_LOCK_HELD" in line:
            break
        if not line:
            process.kill()
            raise RuntimeError("pilot race first operation failed before its lock")
    started = time.monotonic()
    result = run(command, "begin;" + second + "commit;", success=not operation_first)
    if time.monotonic() - started < 0.5:
        raise RuntimeError("pilot race did not serialize admission and closure")
    process.stdin.close()
    process.wait(timeout=30)
    if process.returncode:
        raise RuntimeError("pilot race first transaction failed")
    if operation_first and (result.returncode == 0 or expected_error not in result.stderr):
        raise RuntimeError("closed or revoked invitation admitted a late write")
    result = run(
        command,
        "select count(*) from private.library_intakes where submission_id="
        + literal(f.submission)
        + ";",
    )
    if int(result.stdout.strip()) != (0 if operation_first else 1):
        raise RuntimeError("pilot race left unexpected private admission state")
    return {
        "order": operation + "_then_intake" if operation_first else "intake_then_" + operation,
        "passed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument(
        "--native-psql", action="store_true", help="use an isolated local cluster without Docker"
    )
    parser.add_argument(
        "--socket", help="optional disposable cluster socket directory inside Docker"
    )
    parser.add_argument("--port", type=int, default=5432)
    args = parser.parse_args()
    if not re.fullmatch(r"gsip_lib4b_[a-z0-9_]+", args.database):
        parser.error("target must be an explicitly disposable gsip_lib4b_* database")
    if args.socket and not re.fullmatch(
        r"/tmp/gsip_lib4b_[a-zA-Z0-9_]+",  # noqa: S108 - mktemp-owned test socket
        args.socket,
    ):
        parser.error("socket must belong to an explicitly disposable gsip_lib4b_* cluster")
    if args.port != 5432 and not 55490 <= args.port <= 55599:
        parser.error("port must be the local stack or an isolated migration-test port")
    if args.native_psql and (not args.socket or args.port == 5432):
        parser.error("native psql requires the explicit isolated socket and test port")
    command = [
        "docker",
        "exec",
        "-i",
        "supabase_db_gsip",
        "psql",
        "-X",
        "-q",
        "-t",
        "-A",
        "-U",
        "postgres",
        "-d",
        args.database,
        "-v",
        "ON_ERROR_STOP=1",
        "-v",
        "VERBOSITY=verbose",
    ]
    if args.native_psql:
        command = command[4:]
    command.extend(["-p", str(args.port)])
    if args.socket:
        command.extend(["-h", args.socket])
    outcomes = [
        race(command, operation=operation, operation_first=operation_first)
        for operation in ("withdrawal", "source_delete", "holdout")
        for operation_first in (False, True)
    ]
    outcomes.extend(
        pilot_admission_race(command, operation=operation, operation_first=operation_first)
        for operation in ("revocation", "capture_close", "library_close")
        for operation_first in (False, True)
    )
    print(
        json.dumps(
            {"synthetic_only": True, "production_access": False, "races": outcomes}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
