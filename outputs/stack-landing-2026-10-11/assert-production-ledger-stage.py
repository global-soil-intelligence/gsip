"""Assert only supplied ledger metadata; never connect to or modify a database."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
PLAN = BASE / 'production-repair-expected-ledger-stages-2026-10-12.json'
PLAN_SHA256 = 'aa8a3656306946353624578ca328485e0e09471cf596f3ab52f68bbf86ec8606'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_plan() -> dict:
    if digest(PLAN) != PLAN_SHA256:
        raise ValueError('bound stage plan changed')
    plan = json.loads(PLAN.read_text())
    if plan['target'] != 'toxldjgwkxtneoqsazym':
        raise ValueError('wrong bound project')
    for name, expected in plan['source_sha256'].items():
        if digest(BASE / name) != expected:
            raise ValueError('bound original metadata changed')
    return plan


def normalize(records: list) -> dict[str, dict]:
    if not isinstance(records, list):
        raise ValueError('records must be a list')
    rows = {}
    for row in records:
        if not isinstance(row, dict) or set(row) != {'version', 'name', 'history_row_sha256'}:
            raise ValueError('unexpected metadata record fields')
        if not isinstance(row['version'], str) or not re.fullmatch(r'[0-9]{14}', row['version']):
            raise ValueError('invalid version metadata')
        if not isinstance(row['name'], str) or not re.fullmatch(r'[a-z0-9_]+', row['name']):
            raise ValueError('invalid name metadata')
        if not isinstance(row['history_row_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', row['history_row_sha256']):
            raise ValueError('invalid full-row metadata digest')
        if row['version'] in rows:
            raise ValueError('duplicate version metadata')
        rows[row['version']] = row
    return rows


def assert_stage(plan: dict, stage: str, records: list, added_records: list | None = None) -> dict:
    expected = plan['stages'][stage]
    rows = normalize(records)
    actual_identities = sorted((v, row['name']) for v, row in rows.items())
    expected_identities = sorted((row['version'], row['name']) for row in expected['identities'])
    if len(rows) != expected['expected_count'] or actual_identities != expected_identities:
        raise ValueError('stage count or exact identity set mismatch')
    for protected in expected['protected_original_rows']:
        if rows[protected['version']] != protected:
            raise ValueError('surviving original six-field metadata changed')
    added_hashes_checked = 0
    if expected['preserve_added_stage_hashes']:
        if added_records is None:
            raise ValueError('validated added-stage snapshot is required')
        assert_stage(plan, 'added', added_records)
        added_rows = normalize(added_records)
        for canonical in plan['new_canonical_records']:
            version = canonical['version']
            if rows[version] != added_rows[version]:
                raise ValueError('new canonical metadata changed after added stage')
            added_hashes_checked += 1
    return {'ok': True, 'stage': stage, 'count': len(rows),
            'original_full_row_hashes_checked': len(expected['protected_original_rows']),
            'added_full_row_hashes_checked': added_hashes_checked}


def read_records(path: Path) -> list:
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        if data.get('project', data.get('target', 'toxldjgwkxtneoqsazym')) != 'toxldjgwkxtneoqsazym':
            raise ValueError('wrong supplied project')
        data = data.get('records')
    if not isinstance(data, list):
        raise ValueError('missing supplied metadata records')
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, choices=('before', 'added', 'retired', 'stray_retired'))
    parser.add_argument('--records', required=True, type=Path)
    parser.add_argument('--added-records', type=Path)
    args = parser.parse_args()
    result = assert_stage(load_plan(), args.stage, read_records(args.records),
                          read_records(args.added_records) if args.added_records else None)
    result['records_sha256'] = digest(args.records)
    result['bound_plan_sha256'] = PLAN_SHA256
    if args.added_records:
        result['added_records_sha256'] = digest(args.added_records)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, TypeError) as exc:
        # Error reasons are constants only; no unknown source values are emitted.
        safe = {'bound stage plan changed','wrong bound project','bound original metadata changed',
                'records must be a list','unexpected metadata record fields','invalid version metadata',
                'invalid name metadata','invalid full-row metadata digest','duplicate version metadata',
                'stage count or exact identity set mismatch','surviving original six-field metadata changed',
                'validated added-stage snapshot is required','new canonical metadata changed after added stage',
                'wrong supplied project','missing supplied metadata records'}
        reason = str(exc) if str(exc) in safe else 'invalid supplied metadata; values suppressed'
        print(json.dumps({'ok': False, 'reason': reason}, sort_keys=True))
        raise SystemExit(1) from None
