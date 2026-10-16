"""Audit a private enrichment queue before the existing reviewed import compiler.

This command reads files only. It never changes approvals, the dictionary, inventories
or the DB, and never emits an import batch. Paths supplied by the researcher remain private.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, date
from pathlib import Path

KINDS = {'TECHNICAL', 'CONDITION', 'INSPECTION', 'REPAIR', 'MAINTENANCE'}
DOMAIN_ROLES = {'DOMAIN_EXPERT', 'ASSET_MANAGER'}


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def review_blockers(candidate, approval, optional_reported_field=False):
    """Human declarations are inspected for binding, never authenticated by this audit."""
    if not approval:
        return ['MISSING_HUMAN_FIELD_REVIEW']
    reasons = []
    researcher_l2 = (optional_reported_field
        and candidate.get('kind') == 'TECHNICAL'
        and approval.get('reviewer_role') == 'RESEARCHER'
        and approval.get('approval_scope') == 'OPTIONAL_REPORTED_TECHNICAL_L2'
        and approval.get('verification_level') == 'L2')
    if (approval.get('decision') != 'APPROVED'
            or (approval.get('reviewer_role') not in DOMAIN_ROLES and not researcher_l2)
            or not approval.get('reviewer_name', '').strip()
            or approval.get('reviewer_is_ai') is not False):
        reasons.append('HUMAN_DOMAIN_APPROVAL_REQUIRED')
    try:
        if datetime.fromisoformat(approval.get('reviewed_at', '')).utcoffset() is None:
            raise ValueError
    except ValueError:
        reasons.append('REVIEW_DATE_TIMEZONE_REQUIRED')
    # Binding includes value/unit/asset/locator, not just a candidate label or source filename.
    for field in ['candidate_id', 'asset_code', 'sha256', 'source_locator', 'attribute_key', 'value', 'unit']:
        if approval.get('binding', {}).get(field) != candidate.get(field):
            reasons.append('REVIEW_BINDING_MISMATCH:' + field)
    return reasons


def audit(queue, register, originals, dictionary, sources, approvals=None):
    approvals = approvals or {}
    file_map = {item['sha256']: item for item in register['files']}
    source_map = {item['source_code']: item for item in sources}
    rules = {(item['category_code'], item['attribute_key']): item for item in dictionary}
    results = []
    seen = set()
    for candidate in queue:
        cid = candidate['candidate_id']
        if cid in seen:
            raise ValueError('Duplicate candidate ID: ' + cid)
        seen.add(cid)
        reasons = []
        evidence = file_map.get(candidate['sha256'])
        if not evidence:
            reasons.append('UNREGISTERED_PHYSICAL_FILE')
        else:
            path = (originals / evidence['path']).resolve()
            if (not path.is_relative_to(originals.resolve()) or not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != candidate['sha256']):
                reasons.append('SOURCE_BYTES_MISMATCH')
            if not candidate.get('drive_file_id') and (not candidate.get('source_url', '').startswith('https://') or candidate.get('source_url') != evidence.get('source_url')):
                reasons.append('PUBLIC_SOURCE_BINDING_MISMATCH')
            if candidate['drive_file_id'] != evidence['drive_file_id']:
                reasons.append('DRIVE_BINDING_MISMATCH')
            try:
                page = int(candidate['source_locator'].split(':')[1][1:])
                if not 1 <= page <= evidence['pages']:
                    raise ValueError
            except (IndexError, ValueError):
                reasons.append('INVALID_PDF_LOCATOR')
        if candidate['kind'] not in KINDS:
            reasons.append('REFERENCE_CLASS_NOT_IMPORTABLE')
        if candidate['decision'] != 'VERIFIED':
            reasons.append('CANDIDATE_NOT_VERIFIED')
        category = 'RS-CAT-' + candidate['asset_code'].removeprefix('RS-DT-')
        rule = rules.get((category, candidate['attribute_key']))
        optional_reported = bool(rule and rule.get('required_by_maim') == 'false')
        reasons.extend(review_blockers(candidate, approvals.get(cid), optional_reported))
        if candidate['mapping_verified'] != 'true':
            reasons.append('ASSET_IDENTITY_UNRESOLVED')
        if candidate['source_eligibility'] != 'ELIGIBLE':
            reasons.append('SOURCE_ELIGIBILITY_PENDING')
        if candidate['source_code'] not in source_map:
            reasons.append('CONTROLLED_SOURCE_ADMISSION_PENDING')
        if candidate['kind'] == 'TECHNICAL':
            if (not rule or rule['attribute_label'] != candidate['label']
                    or rule['expected_unit'] != candidate['unit']):
                reasons.append('APPROVED_DICTIONARY_KEY_LABEL_UNIT_REQUIRED')
        if candidate['kind'] in {'CONDITION', 'INSPECTION', 'REPAIR', 'MAINTENANCE'}:
            if candidate['temporal_precision'] != 'FULL_DATE':
                reasons.append('FULL_DATE_REQUIRED')
            try:
                date.fromisoformat(candidate['as_of_date_or_period'])
            except ValueError:
                reasons.append('EXACT_ISO_EVENT_DATE_REQUIRED')
            if candidate['source_state'] in {'PROCEDURE_ONLY', 'HISTORICAL_DESIGN_OVERVIEW'}:
                reasons.append('PROCEDURE_OR_DESIGN_IS_NOT_AN_EVENT')
        if candidate['kind'] in {'INSPECTION', 'REPAIR', 'MAINTENANCE'}:
            if candidate['completion_status'] != 'VERIFIED':
                reasons.append('PERFORMED_ACTIVITY_REVIEW_REQUIRED')
        results.append({'candidate_id': cid, 'eligible_for_compiler': not reasons,
                        'blockers': reasons})
    return {'status': 'READY_FOR_COMPILER' if any(r['eligible_for_compiler'] for r in results) else 'NO_QUALIFIED_IMPORT',
            'candidate_count': len(queue),
            'eligible_count': sum(r['eligible_for_compiler'] for r in results),
            'decisions': dict(Counter(r['decision'] for r in queue)), 'candidates': results,
            'limitations': 'Declaration validation does not authenticate the human reviewer or establish source truth. Explicit researcher approval is accepted only for optional reported L2 technical fields; it does not satisfy domain/methodology gates. Existing compiler/dry-run/apply/retry and scope/denominator approval remain required.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True)
    parser.add_argument('--controlled-dir', type=Path, required=True)
    parser.add_argument('--approvals', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(rows(args.evidence_dir / 'evidence_candidate_review.csv'),
                   json.loads((args.evidence_dir / 'source_evidence_register.json').read_text()),
                   args.evidence_dir / 'originals',
                   rows(args.controlled_dir / 'technical_attribute_dictionary.csv'),
                   rows(args.controlled_dir / 'source_inventory.csv'),
                   json.loads(args.approvals.read_text()) if args.approvals else None)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(result['status'], 'candidates=', result['candidate_count'], 'eligible=', result['eligible_count'])


if __name__ == '__main__':
    main()
