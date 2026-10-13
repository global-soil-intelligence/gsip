"""Two-connection photo privacy races; only explicitly disposable local databases.

Synthetic EMPTY geometry, format-only cell strings and generated fixture identities are never
published. Neither database credentials nor operator tokens are printed. CI uses its own
throwaway PostgreSQL cluster; Docker mode targets only the development container.
"""

# SQL contains only internally generated fixture data, escaped with literal().
# ruff: noqa: S608
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def run(command: list[str], sql: str, *, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, input=sql, text=True, capture_output=True, timeout=20)  # noqa: S603
    if success and result.returncode:
        raise RuntimeError("isolated synthetic privacy command failed")
    return result


def value(command: list[str], sql: str) -> Any:
    output = run(command, sql).stdout.strip()
    return json.loads(output.splitlines()[-1]) if output else None


def service(sql: str) -> str:
    return "set request.jwt.claims='{" + '"role":"service_role"' + "}';" + sql


def rpc(name: str, request: dict[str, Any]) -> str:
    return "select public." + name + "(" + literal(json.dumps(request)) + "::jsonb);"


@dataclass(frozen=True)
class Fixture:
    auth: str
    contributor: str
    grant: str
    submission: str
    photo: str
    token: str
    content: dict[str, Any]
    lease: dict[str, Any] | None
    screen: dict[str, Any] | None


def fixture(command: list[str], stage: str) -> Fixture:
    auth, contributor, grant, submission, photo, operator = (str(uuid4()) for _ in range(6))
    terms = "privacy-race-" + uuid4().hex
    token = hashlib.sha256(("synthetic operator " + operator).encode()).hexdigest()
    photo_b = str(uuid4())
    sql = f"""
    insert into public.terms_versions(version,published_at) values({literal(terms)},
        now()-interval '1 day');
    insert into auth.users(id) values({literal(auth)});
    insert into public.contributors(id,auth_uid,handle) values({literal(contributor)},
        {literal(auth)},{literal("privacy-race-" + uuid4().hex[:16])});
    insert into public.contribution_grants(id,contributor_id,terms_version,accepted_at,
        attribution_name)
        values({literal(grant)},{literal(contributor)},{literal(terms)},now(),
        'Anonymous soil contributor');
    insert into public.submissions(id,contributor_id,grant_id,geom_precise,captured_at,
        finalized_at,land_cover,surface_condition,disturbed,device_model)
        values({literal(submission)},{literal(contributor)},{literal(grant)},
        'SRID=4326;POINT EMPTY',now(),now(),'bare','dry',false,'synthetic privacy race');
    insert into public.photos(id,submission_id,shot_type,storage_path,qa_status) values
        ({literal(photo)},{literal(submission)},'A',
        {literal(auth + "/" + submission + "/A/" + str(uuid4()) + ".jpg")},'pass'),
        ({literal(photo_b)},{literal(submission)},'B',
        {literal(auth + "/" + submission + "/B/" + str(uuid4()) + ".jpg")},'pass');
    update public.submissions set status='qa_pass',h3_r8='88'||lpad('1',13,'0'),
        h3_r6='86'||lpad('1',13,'0') where id={literal(submission)};
    insert into private.photo_privacy_operators(operator_id,auth_uid,token_sha256,active)
        values({literal(operator)},{literal(auth)},
        {literal(hashlib.sha256(token.encode()).hexdigest())},true);
    """
    run(command, sql)
    # Make the unused QA-passing B private content permanently withheld; no detector claim.
    run(
        command,
        "update private.photo_privacy_content set status='withheld' "
        + f"where photo_id={literal(photo_b)};",
    )
    content = {
        "schema_version": "gsip-photo-privacy-v1",
        "photo_id": photo,
        "expected_content_revision": 0,
        "sanitized_sha256": "a" * 64,
        "byte_count": 1024,
        "sanitizer_version": "synthetic-v1",
    }
    lease = screen = None
    if stage != "registration":
        run(command, service(rpc("record_photo_privacy_content", content)))
        lease = value(command, service("select public.claim_photo_privacy_job();"))
        if lease is None or lease["photo_id"] != photo:
            raise RuntimeError("synthetic fixture was not exclusively claimable")
        screen = {
            "schema_version": "gsip-photo-privacy-v1",
            "request_id": str(uuid4()),
            **{
                key: lease[key]
                for key in (
                    "photo_id",
                    "content_revision",
                    "policy_id",
                    "policy_revision",
                    "sanitized_sha256",
                    "screening_version",
                    "calibration_version",
                    "detector_manifest_sha256",
                    "calibration_manifest_sha256",
                )
            },
            "face": {"result": "pass", "candidates": 0},
            "scene_text": {
                "result": "flag" if stage == "review" else "pass",
                "candidates": 1 if stage == "review" else 0,
            },
            "card_exception_used": False,
            "card_exclusion": None,
        }
        if stage in ("review", "export"):
            run(
                command,
                service(
                    "select public.complete_photo_privacy_job("
                    + literal(lease["lease_id"])
                    + ","
                    + literal(json.dumps(screen))
                    + "::jsonb);"
                ),
            )
    return Fixture(auth, contributor, grant, submission, photo, token, content, lease, screen)


def action(f: Fixture, stage: str) -> str:
    if stage == "registration":
        return service(rpc("record_photo_privacy_content", f.content))
    if stage == "completion":
        if not f.lease or not f.screen:
            raise RuntimeError("synthetic completion fixture lacks its binding")
        return service(
            "select public.complete_photo_privacy_job("
            + literal(f.lease["lease_id"])
            + ","
            + literal(json.dumps(f.screen))
            + "::jsonb);"
        )
    if not f.screen:
        raise RuntimeError("synthetic review/export fixture lacks its binding")
    binding = {
        key: f.screen[key]
        for key in (
            "photo_id",
            "content_revision",
            "policy_id",
            "policy_revision",
            "sanitized_sha256",
            "screening_version",
            "calibration_version",
        )
    }
    if stage == "review":
        request = {
            "schema_version": "gsip-photo-privacy-v1",
            "review_id": str(uuid4()),
            **binding,
            "decision": "clear",
            "reason": "false_positive",
        }
        return service(
            "select public.review_photo_privacy("
            + literal(f.token)
            + ","
            + literal(json.dumps(request))
            + "::jsonb);"
        )
    return service(
        rpc(
            "authorize_photo_privacy_export",
            {"schema_version": "gsip-photo-privacy-v1", "photos": [binding]},
        )
    )


def race(command: list[str], *, operation: str, stage: str, mutation_first: bool) -> dict[str, Any]:
    f = fixture(command, stage)
    call = action(f, stage)
    if operation == "withdrawal":
        mutation = (
            "insert into public.deletion_requests(contributor_id,kind) values("
            + literal(f.contributor)
            + ",'withdraw_contributions');"
        )
    elif operation == "source_delete":
        mutation = "delete from public.submissions where id=" + literal(f.submission) + ";"
    elif operation == "content":
        replacement = {**f.content, "expected_content_revision": 1, "sanitized_sha256": "b" * 64}
        mutation = service(rpc("record_photo_privacy_content", replacement))
    elif operation == "policy":
        mutation = "update private.photo_privacy_state set publication_open=false;"
    elif operation == "auth_delete":
        mutation = "delete from auth.users where id=" + literal(f.auth) + ";"
    else:
        mutation = (
            "update private.photo_privacy_operators set active=false where auth_uid="
            + literal(f.auth)
            + ";"
        )
    first, second = (mutation, call) if mutation_first else (call, mutation)
    # A visible marker proves connection one finished its operation while retaining locks.
    script = (
        "set statement_timeout='10s'; begin;"
        + first
        + "\n\\echo PRIVACY_RACE_LOCK_HELD\nselect pg_sleep(1.2); commit;\n"
    )
    process = subprocess.Popen(  # noqa: S603 - fixed local toolchain.
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("race connection did not expose local streams")
    process.stdin.write(script)
    process.stdin.flush()
    for line in process.stdout:
        if "PRIVACY_RACE_LOCK_HELD" in line:
            break
    else:
        process.kill()
        raise RuntimeError("first synthetic race failed before its lock witness")
    started = time.monotonic()
    result = run(command, "set statement_timeout='10s'; begin;" + second + "commit;", success=False)
    waited = time.monotonic() - started
    process.stdin.close()
    process.wait(timeout=15)
    nonblocking_source = mutation_first and operation == "source_delete"
    if process.returncode or (waited < 0.4 and not nonblocking_source):
        raise RuntimeError("race lacked successful first commit or expected lock wait")
    refused = mutation_first and stage != "export"
    if refused:
        expected = {
            "withdrawal": ("WD001", "PP002"),
            "source_delete": ("42501", "WD001", "PP002"),
            "content": ("PP002",),
            "policy": ("PP002",),
            "auth_delete": ("42501",),
            "operator_revoke": ("42501",),
        }[operation]
        if result.returncode == 0 or not any(code in result.stderr for code in expected):
            raise RuntimeError("stale second operation was not specifically refused")
    elif result.returncode:
        raise RuntimeError("serialized second operation unexpectedly failed")
    if stage == "export" and mutation_first:
        receipt = json.loads(result.stdout.strip().splitlines()[-1])
        if receipt["authorizations"][0]["authorized"]:
            raise RuntimeError("late export bypassed closed publication gate")
    summary = value(
        command,
        f"""select jsonb_build_object(
        'content',(select count(*) from private.photo_privacy_content where
        photo_id={literal(f.photo)}),
        'screens',(select count(*) from private.photo_privacy_screens where
        photo_id={literal(f.photo)}),
        'reviews',(select count(*) from private.photo_privacy_reviews where
        photo_id={literal(f.photo)}),
        'tombstones',(select count(*) from private.photo_privacy_tombstones where
        identity_kind='photo' and identity_id={literal(f.photo)}),
        'status',(select status from private.photo_privacy_content where
        photo_id={literal(f.photo)}),
        'digest',(select sanitized_sha256 from private.photo_privacy_content where
        photo_id={literal(f.photo)}));""",
    )
    if operation in ("withdrawal", "source_delete"):
        if (
            summary["content"]
            or summary["screens"]
            or summary["reviews"]
            or summary["tombstones"] != 1
        ):
            raise RuntimeError("withdrawal/source race left covered private payload")
    elif operation == "content":
        if summary["digest"] != "b" * 64 or summary["status"] != "pending":
            raise RuntimeError("old worker clearance survived a new byte generation")
    # Dispose this fixture before another claim; rows here are never public release data.
    run(command, "delete from public.submissions where id=" + literal(f.submission) + ";")
    run(
        command,
        "delete from auth.users where id="
        + literal(f.auth)
        + ";update private.photo_privacy_state set publication_open=true;",
    )
    return {
        "order": operation + "_then_" + stage if mutation_first else stage + "_then_" + operation,
        "passed": True,
        "actual_lock_wait": waited >= 0.4,
        "late_operation_refused": refused,
    }


def hold(command: list[str], sql: str) -> subprocess.Popen[str]:
    process = subprocess.Popen(  # noqa: S603 - fixed local toolchain.
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("partial-lock connection streams unavailable")
    process.stdin.write("set statement_timeout='10s';begin;" + sql + "\n\\echo PARTIAL_LOCK_HELD\n")
    process.stdin.flush()
    for line in process.stdout:
        if "PARTIAL_LOCK_HELD" in line:
            return process
    process.kill()
    raise RuntimeError("partial-lock connection failed before lock witness")


def release(process: subprocess.Popen[str], sql: str = "commit;") -> None:
    if process.stdin is None:
        raise RuntimeError("partial-lock connection lost its input")
    process.stdin.write(sql + "\n")
    process.stdin.close()
    process.wait(timeout=15)
    if process.returncode:
        raise RuntimeError("partial-lock source transaction failed")


def mid_source(command: list[str], source: str) -> dict[str, Any]:
    f = fixture(command, "registration")
    table, identity = ("submissions", f.submission) if source == "parent" else ("photos", f.photo)
    process = hold(
        command,
        "select id from public." + table + " where id=" + literal(identity) + " for update;",
    )
    result = run(command, service(action(f, "registration")), success=False)
    if result.returncode == 0 or "PP002" not in result.stderr or "40P01" in result.stderr:
        raise RuntimeError("busy source was not promptly and specifically refused")
    # The refusing call must not retain the other source lock.
    unlocked_table, unlocked_id = (
        ("photos", f.photo) if source == "parent" else ("submissions", f.submission)
    )
    run(
        command,
        "begin;select id from public."
        + unlocked_table
        + " where id="
        + literal(unlocked_id)
        + " for update nowait;rollback;",
    )
    release(process, "delete from public." + table + " where id=" + literal(identity) + ";commit;")
    run(
        command,
        "delete from public.submissions where id="
        + literal(f.submission)
        + ";delete from auth.users where id="
        + literal(f.auth)
        + ";",
    )
    return {
        "order": "mid_" + source + "_delete_then_registration",
        "passed": True,
        "prompt_busy_refusal": True,
        "other_source_lock_released": True,
        "source_delete_committed": True,
    }


def mid_claim(command: list[str]) -> dict[str, Any]:
    first = fixture(command, "registration")
    second = fixture(command, "registration")
    blocker = hold(
        command, "select id from public.photos where id=" + literal(first.photo) + " for update;"
    )
    worker = hold(command, service("select public.claim_photo_privacy_job();"))
    # Worker must have skipped the busy first source and retained only second's lease.
    active = value(
        command,
        "select to_jsonb(count(*)) from private.photo_privacy_jobs where photo_id="
        + literal(first.photo)
        + " and status='processing';",
    )
    if active:
        raise RuntimeError("busy source acquired a lease")
    run(
        command,
        "begin;select id from public.submissions where id="
        + literal(first.submission)
        + " for update nowait;rollback;",
    )
    run(
        command,
        "begin;select id from public.contributors where id="
        + literal(first.contributor)
        + " for update nowait;rollback;",
    )
    release(worker)
    receipt = value(
        command, service("select public.photo_privacy_receipt(" + literal(second.photo) + ");")
    )
    if receipt["status"] != "processing":
        raise RuntimeError("claim did not advance to the available source")
    release(blocker, "delete from public.photos where id=" + literal(first.photo) + ";commit;")
    run(
        command,
        "delete from public.submissions where id in ("
        + literal(first.submission)
        + ","
        + literal(second.submission)
        + ");delete from auth.users where id in ("
        + literal(first.auth)
        + ","
        + literal(second.auth)
        + ");",
    )
    return {
        "order": "mid_photo_lock_then_claim_next_source",
        "passed": True,
        "busy_source_skipped": True,
        "skipped_parent_lock_released": True,
        "skipped_contributor_lock_released": True,
    }


def mid_export(command: list[str]) -> dict[str, Any]:
    first = fixture(command, "export")
    second = fixture(command, "export")
    if not first.screen or not second.screen:
        raise RuntimeError("partial export fixture lacks screen")
    keys = (
        "photo_id",
        "content_revision",
        "policy_id",
        "policy_revision",
        "sanitized_sha256",
        "screening_version",
        "calibration_version",
    )
    request = {
        "schema_version": "gsip-photo-privacy-v1",
        "photos": [{key: f.screen[key] for key in keys} for f in (first, second) if f.screen],
    }
    blocker = hold(
        command,
        "select id from public.submissions where id=" + literal(second.submission) + " for update;",
    )
    response = value(command, service(rpc("authorize_photo_privacy_export", request)))
    if response["authorizations"] != [
        {"photo_id": first.photo, "authorized": True},
        {"photo_id": second.photo, "authorized": False},
    ]:
        raise RuntimeError("partial batch did not conservatively withhold its busy source")
    # The export RPC has returned and released parent 1; deletion in opposite order succeeds.
    release(
        blocker,
        "delete from public.submissions where id="
        + literal(second.submission)
        + ";delete from public.submissions where id="
        + literal(first.submission)
        + ";commit;",
    )
    run(
        command,
        "delete from auth.users where id in ("
        + literal(first.auth)
        + ","
        + literal(second.auth)
        + ");",
    )
    return {
        "order": "mid_second_parent_lock_then_two_source_export",
        "passed": True,
        "busy_source_withheld": True,
        "reverse_parent_deletes_committed": True,
    }


def mid_insert(command: list[str], kind: str, withdrawal_first: bool) -> dict[str, Any]:
    f = fixture(command, "registration")
    storage = f.auth + "/" + f.submission + "/C/" + str(uuid4()) + ".jpg"
    claims = json.dumps({"sub": f.auth, "role": "authenticated"})
    insert = (
        "set role authenticated;set request.jwt.claims="
        + literal(claims)
        + ";insert into public.photos(submission_id,shot_type,storage_path) values("
        + literal(f.submission)
        + ",'C',"
        + literal(storage)
        + ");"
    )
    withdrawal = (
        "insert into public.deletion_requests(contributor_id,kind) values("
        + literal(f.contributor)
        + ","
        + literal(kind)
        + ");"
    )
    first, second = (withdrawal, insert) if withdrawal_first else (insert, withdrawal)
    blocker = hold(command, first)
    application = "privacy_partial_insert_" + uuid4().hex[:8]
    contender = subprocess.Popen(  # noqa: S603 - fixed local toolchain.
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if contender.stdin is None:
        raise RuntimeError("partial insert contender input unavailable")
    contender.stdin.write(
        "set statement_timeout='10s';set application_name="
        + literal(application)
        + ";"
        + second
        + "\n"
    )
    contender.stdin.close()
    waiting = False
    for _ in range(40):
        waiting = value(
            command,
            "select to_jsonb(coalesce(bool_or(wait_event_type='Lock'),false)) "
            "from pg_stat_activity where application_name=" + literal(application) + ";",
        )
        if waiting or contender.poll() is not None:
            break
        time.sleep(0.05)
    if not waiting:
        contender.kill()
        release(blocker, "rollback;")
        raise RuntimeError("photo insertion/withdrawal lacked contributor lock wait")
    if withdrawal_first:
        # Admission must wait before any parent/FK/private row lock; parent remains free.
        run(
            command,
            "begin;select id from public.submissions where id="
            + literal(f.submission)
            + " for update nowait;rollback;",
        )
    release(blocker)
    contender.wait(timeout=15)
    stderr = contender.stderr.read() if contender.stderr else ""
    if (
        "40P01" in stderr
        or (withdrawal_first and (contender.returncode == 0 or "WD001" not in stderr))
        or (not withdrawal_first and contender.returncode)
    ):
        raise RuntimeError("photo admission failed to refresh committed withdrawal rights")
    summary = value(
        command,
        "select jsonb_build_object('withdrawn',exists(select 1 "
        "from public.grant_withdrawals where grant_id="
        + literal(f.grant)
        + "),'source',exists(select 1 from public.photos where storage_path="
        + literal(storage)
        + "),'payloads',(select count(*) from private.photo_privacy_content where grant_id="
        + literal(f.grant)
        + "));",
    )
    if (
        not summary["withdrawn"]
        or summary["payloads"]
        or summary["source"] != (not withdrawal_first)
    ):
        raise RuntimeError("late optional photo recreated withdrawn private payload")
    run(
        command,
        "delete from public.submissions where id="
        + literal(f.submission)
        + ";delete from auth.users where id="
        + literal(f.auth)
        + ";",
    )
    return {
        "order": "mid_"
        + (
            kind + "_then_optional_C_insert"
            if withdrawal_first
            else "optional_C_insert_then_" + kind
        ),
        "passed": True,
        "authenticated_allowed_columns_only": True,
        "actual_contributor_wait": True,
        "private_payloads": 0,
        "late_insert_refused": withdrawal_first,
    }


def isolation_refusal(command: list[str], isolation: str) -> dict[str, Any]:
    f = fixture(command, "registration")
    storage = f.auth + "/" + f.submission + "/C/" + str(uuid4()) + ".jpg"
    claims = json.dumps({"sub": f.auth, "role": "authenticated"})
    admission = (
        "set role authenticated;set request.jwt.claims="
        + literal(claims)
        + ";insert into public.photos(submission_id,shot_type,storage_path) values("
        + literal(f.submission)
        + ",'C',"
        + literal(storage)
        + ");"
    )
    calls = [
        admission,
        *[
            service("select public." + call + ";")
            for call in (
                "photo_privacy_capabilities()",
                "record_photo_privacy_content('{}')",
                "claim_photo_privacy_job()",
                "complete_photo_privacy_job(null,null)",
                "fail_photo_privacy_job(null,'storage')",
                "photo_privacy_receipt(" + literal(f.photo) + ")",
                "photo_privacy_review_context(" + literal(f.photo) + ",null)",
                "review_photo_privacy(null,'{}')",
                "authorize_photo_privacy_export('{}')",
            )
        ],
    ]
    for call in calls:
        result = run(
            command, "begin isolation level " + isolation + ";" + call + "rollback;", success=False
        )
        if result.returncode == 0 or "55000" not in result.stderr:
            raise RuntimeError(
                "stale transaction isolation was not refused before authority checks"
            )
    if value(
        command,
        "select to_jsonb(exists(select 1 from public.photos where storage_path="
        + literal(storage)
        + "));",
    ):
        raise RuntimeError("noncurrent transaction inserted source state")
    run(
        command,
        "delete from public.submissions where id="
        + literal(f.submission)
        + ";delete from auth.users where id="
        + literal(f.auth)
        + ";",
    )
    return {
        "order": isolation.replace(" ", "_") + "_admission_and_nine_RPC_refusal",
        "passed": True,
        "source_insert_refused": True,
        "private_RPCs_refused": 9,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--native-psql", action="store_true")
    parser.add_argument("--socket")
    parser.add_argument("--port", type=int, default=5432)
    args = parser.parse_args()
    if not re.fullmatch(r"gsip_lib4b_[a-z0-9_]+", args.database):
        parser.error("target must be an explicitly disposable gsip_lib4b_* database")
    if args.socket and not re.fullmatch(r"/tmp/gsip_lib4b_[a-zA-Z0-9_]+", args.socket):  # noqa: S108
        parser.error("socket must belong to an explicitly disposable local test cluster")
    if args.port != 5432 and not 55490 <= args.port <= 55599:
        parser.error("port must be local development or isolated migration-test port")
    if args.native_psql and (not args.socket or args.port == 5432):
        parser.error("native mode requires the explicit isolated socket and test port")
    command = [
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
        "-p",
        str(args.port),
    ]
    if args.socket:
        command.extend(["-h", args.socket])
    if not args.native_psql:
        command = ["docker", "exec", "-i", "supabase_db_gsip", *command]
    # Earlier migration/library checks finished already. Discard their synthetic source
    # fixtures so FIFO claims in this explicitly disposable database are exclusive.
    run(command, "delete from public.submissions;")
    policy = str(uuid4())
    run(
        command,
        f"""insert into private.photo_privacy_policies values({literal(policy)},
        {literal("synthetic-race-screen-" + uuid4().hex[:8])},
        {literal("synthetic-race-calib-" + uuid4().hex[:8])},
        repeat('d',64),repeat('e',64),'synthetic-margin-v1','{{}}',repeat('f',64));
        update private.photo_privacy_state set policy_id={literal(policy)},
        implementation_deployed=true,publication_open=true;""",
    )
    outcomes = []
    for operation, stage in [
        ("withdrawal", stage) for stage in ("registration", "completion", "review", "export")
    ] + [
        ("source_delete", "completion"),
        ("content", "completion"),
        ("policy", "completion"),
        ("policy", "export"),
        ("auth_delete", "review"),
        ("operator_revoke", "review"),
    ]:
        for mutation_first in (False, True):
            outcomes.append(
                race(command, operation=operation, stage=stage, mutation_first=mutation_first)
            )
    # Concurrent claiming uses contributor SKIP LOCKED instead of waiting for a job-first lock.
    f = fixture(command, "registration")
    run(command, service(rpc("record_photo_privacy_content", f.content)))
    process = subprocess.Popen(  # noqa: S603 - fixed local toolchain.
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("claim race streams unavailable")
    process.stdin.write(
        service("begin;select public.claim_photo_privacy_job();")
        + "\n\\echo PRIVACY_CLAIM_LOCK_HELD\nselect pg_sleep(1.2);commit;\n"
    )
    process.stdin.flush()
    for line in process.stdout:
        if "PRIVACY_CLAIM_LOCK_HELD" in line:
            break
    else:
        process.kill()
        raise RuntimeError("first claim lacked lock witness")
    second = value(command, service("select public.claim_photo_privacy_job();"))
    if second is not None:
        raise RuntimeError("a concurrent worker acquired a duplicate lease")
    process.stdin.close()
    process.wait(timeout=15)
    if process.returncode:
        raise RuntimeError("first claim failed")
    count = value(
        command,
        "select to_jsonb(count(*)) from private.photo_privacy_jobs where photo_id="
        + literal(f.photo)
        + " and status='processing' and attempts=1;",
    )
    if count != 1:
        raise RuntimeError("concurrent claim changed the attempt budget")
    outcomes.append(
        {
            "order": "claim_then_concurrent_claim",
            "passed": True,
            "skip_locked": True,
            "one_active_lease": True,
        }
    )
    run(command, "delete from public.submissions where id=" + literal(f.submission) + ";")
    outcomes.extend(mid_source(command, source) for source in ("parent", "photo"))
    outcomes.append(mid_claim(command))
    outcomes.append(mid_export(command))
    outcomes.extend(
        mid_insert(command, kind, first)
        for kind in ("withdraw_contributions", "delete_account")
        for first in (False, True)
    )
    outcomes.extend(
        isolation_refusal(command, level) for level in ("repeatable read", "serializable")
    )
    print(
        json.dumps(
            {"synthetic_only": True, "production_access": False, "races": outcomes}, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
