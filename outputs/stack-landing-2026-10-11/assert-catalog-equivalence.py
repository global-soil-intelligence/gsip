"""Output-only reconciliation evidence: reject every unreviewed catalog difference."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
ALIASES = {
    ('photos', 'photos_insert_own'): 'check',
    ('photos', 'photos_select_own'): 'using',
    ('gold_labels', 'gold_labels_select_own'): 'using',
    ('predictions', 'predictions_select_own'): 'using',
    ('priors', 'priors_select_own'): 'using',
    ('qa_events', 'qa_events_select_own'): 'using',
}
CANONICAL_EXPRESSION = '(submission_id IN ( SELECT submissions.id\n   FROM public.submissions\n  WHERE (submissions.contributor_id = public.current_contributor_id())))'
DEPLOYED_EXPRESSION = '(submission_id IN ( SELECT s.id\n   FROM public.submissions s\n  WHERE (s.contributor_id = public.current_contributor_id())))'
PLATFORM_EXTENSIONS = [
    {'name': 'pg_stat_statements', 'schema': 'extensions', 'version': '1.11'},
    {'name': 'supabase_vault', 'schema': 'vault', 'version': '0.3.1'},
    {'name': 'uuid-ossp', 'schema': 'extensions', 'version': '1.1'},
]
PLATFORM_SCHEMA_GRANTS = [
    {'schema': 'extensions', 'role': 'dashboard_user', 'privilege': 'CREATE', 'grantable': False},
    {'schema': 'extensions', 'role': 'dashboard_user', 'privilege': 'USAGE', 'grantable': False},
    {'schema': 'public', 'role': 'postgres', 'privilege': 'USAGE', 'grantable': False},
]

def rows(values: list[dict]) -> set[str]:
    serialized = [json.dumps(value, sort_keys=True) for value in values]
    if len(serialized) != len(set(serialized)):
        raise AssertionError('duplicate catalog record')
    return set(serialized)

def prove(reference: dict, deployed: dict, supplemental: dict, deployed_supplemental: dict) -> dict:
    actual = copy.deepcopy(deployed)
    allowed_aliases = []
    for key, field in ALIASES.items():
        expected = [p for p in reference['policies'] if (p['table'], p['name']) == key]
        observed = [p for p in actual['policies'] if (p['table'], p['name']) == key]
        assert len(expected) == len(observed) == 1, 'policy identity missing/duplicated'
        assert expected[0][field] == CANONICAL_EXPRESSION, 'reference expression changed'
        assert observed[0][field] == DEPLOYED_EXPRESSION, 'deployed difference exceeds exact alias rename'
        observed[0][field] = CANONICAL_EXPRESSION
        assert observed[0] == expected[0], 'policy roles/command/permissiveness/other expression drift'
        allowed_aliases.append({'table': key[0], 'policy': key[1], 'expression_field': field})
    expected_extensions = rows(reference['extensions']) | rows(PLATFORM_EXTENSIONS)
    assert rows(actual['extensions']) == expected_extensions, 'unexpected extension drift'
    actual['extensions'] = copy.deepcopy(reference['extensions'])
    assert set(reference) == set(actual), 'catalog section drift'
    for section in reference:
        assert rows(reference[section]) == rows(actual[section]), f'unreviewed {section} difference'
    assert set(supplemental) == set(deployed_supplemental), 'supplement section drift'
    for section in supplemental:
        expected = rows(supplemental[section])
        if section == 'schema_grants':
            expected |= rows(PLATFORM_SCHEMA_GRANTS)
        assert expected == rows(deployed_supplemental[section]), f'unreviewed supplemental {section} difference'
    return {'catalog_sections_exact_after_six_literal_alias_substitutions': len(reference), 'supplemental_sections_exact_except_three_platform_schema_grants': len(supplemental), 'allowed_policy_aliases': allowed_aliases, 'preserved_platform_extensions': PLATFORM_EXTENSIONS, 'preserved_platform_schema_grants': PLATFORM_SCHEMA_GRANTS}

def main() -> None:
    names = ['canonical-catalog-baseline17.json', 'production-catalog-before-reconciliation.json', 'canonical-catalog-baseline17-supplement.json', 'production-catalog-before-reconciliation-supplement.json']
    inputs = [json.loads((BASE/name).read_text()) for name in names]
    evidence = prove(*inputs)
    negatives = []
    for mutation in ('private_anon_grant', 'policy_or_true', 'missing_constraint', 'definer_lookup', 'unknown_extension', 'private_schema_usage', 'function_owner_changed', 'table_owner_changed', 'function_delegation_changed'):
        candidate = copy.deepcopy(inputs)
        if mutation == 'private_anon_grant':
            candidate[1]['column_grants'].append({'table':'submissions','column':'geom_precise','role':'anon','privilege':'SELECT','grantable':False})
        elif mutation == 'policy_or_true':
            next(p for p in candidate[1]['policies'] if p['name']=='photos_select_own')['using'] += ' OR true'
        elif mutation == 'missing_constraint':
            candidate[1]['constraints'] = [c for c in candidate[1]['constraints'] if c['name']!='submissions_grant_owner_fkey']
        elif mutation == 'definer_lookup':
            next(f for f in candidate[1]['functions'] if f['name']=='current_contributor_id')['security_definer'] = True
        elif mutation == 'unknown_extension':
            candidate[1]['extensions'].append({'name':'unexpected_synthetic_extension','schema':'public','version':'1'})
        elif mutation == 'function_owner_changed':
            next(f for f in candidate[1]['functions'] if f['name']=='current_contributor_id')['owner'] = 'authenticated'
        elif mutation == 'table_owner_changed':
            candidate[1]['tables'][0]['owner'] = 'authenticated'
        elif mutation == 'function_delegation_changed':
            next(f for f in candidate[1]['functions'] if f['name']=='current_contributor_id')['grants'][0]['grantable'] = True
        else:
            candidate[3]['schema_grants'].append({'schema':'private','role':'anon','privilege':'USAGE','grantable':False})
        try:
            prove(*candidate)
        except AssertionError:
            negatives.append({'mutation':mutation,'rejected':True})
        else:
            raise AssertionError(f'negative control unexpectedly passed: {mutation}')
    evidence.update({'status':'PASS','positive_equivalence_proofs':1,'negative_controls_rejected':len(negatives),'negative_controls':negatives,'input_sha256':{name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in names},'comparator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'extractor_version':2,'scope':'Current GSIP catalog equivalence only; no production row contents, historical DML proof, or production mutation'})
    output = BASE/'canonical-production-equivalence-proof.json'
    output.write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({'status':'PASS','positive_equivalence_proofs':1,'negative_controls_rejected':len(negatives),'output':str(output),'sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))

if __name__ == '__main__':
    main()
