"""Read retained snapshot/review CSVs and export Table 2. No DB connection or mutation.
Run from repo root: python3 scripts/export_paper_ui_counts.py
Requires the private PAPER-UI-CLEAN snapshot and reviewed input package.
"""
from pathlib import Path
import json,csv
R=Path(__file__).resolve().parents[1]
P=R/'research/evaluation/results/paper'
E=R/'research/evaluation/evidence/PAPER-UI-CLEAN'
V=R/'research/dataset/reviewed'
# Metrics reproducible from retained DB snapshot and reviewed inputs; no live DB writes.
readcsv=lambda name:list(csv.DictReader((V/name).open()))
rows=json.loads((E/'db-after.json').read_text())['rows'];a=[v for v in rows['assets'] if v['asset_code'].startswith('RS-DT-')];ids={v['id'] for v in a};tech=[v for v in rows['technical'] if v['asset_id'] in ids];src=readcsv('source_inventory.csv');docs=[v for v in readcsv('document_review.csv') if v['document_status']=='IMPORT'];elig=[v for v in readcsv('three_d_eligibility_review.csv') if v['decision']=='APPROVED' and v['proposed_requires_3d']=='true'];loc=json.loads((R/'storage/asset_locations.json').read_text())['records'];prov=json.loads((R/'storage/reviewed_provenance.json').read_text())['records']
metrics=[('Target assets',len(a),'controlled RS asset count'),('Reviewed identities',sum(v['identity_status']=='VERIFIED' and v['in_scope']=='true' for v in readcsv('asset_identity_review.csv')),'researcher identity inclusion review / 4; not independent domain approval'),('Verified geometry',sum(v['geometry'] is not None for v in a),'canonical RS geometry / 4; all null, no surveyed geometry'),('Reference locations',sum(v.get('location_status')=='REFERENCE_LOCATION' for k,v in loc.items() if k in ids),'separate / 4; excluded from verified numerator'),('Technical records',len(tech),'RS records; level from bound reviewed provenance'),('L2 technical records',sum(prov.get(v['id'],{}).get('provenance',{}).get('verification_level')=='L2' for v in tech),'historical L2; no promotion'),('Verified current condition',len({v['asset_id'] for v in rows['conditions'] if v['asset_id'] in ids and v['verification_status']=='VERIFIED'}),'assets with verified condition / 4'),('Verified O&M events',sum(v['asset_id'] in ids and v['verification_status']=='VERIFIED' for k in ['conditions','inspections','repairs','maintenance'] for v in rows[k]),'verified condition/inspection/repair/maintenance records; not real-world activity count'),('Controlled sources',len(src),'reviewed source inventory rows, including candidate/reference sources'),('Expected-file sources',sum(v['file_expected']=='true' for v in src),'file_expected=true; distinct from linked documents'),('Reviewed distinct documents',len({v['checksum_sha256'] for v in docs if v['checksum_sha256']}),'distinct SHA-256 among IMPORT file-retention reviews; not validated content'),('Selected 3D targets',len(elig),'approved requires_3d=true scope'),('Representative verified links',sum(v['asset_id'] in ids and v['verification_status']=='VERIFIED' for v in rows['model_asset_links']),'representative link records / 1 selected target; LOCAL, not full geometry')]
with (P/'table_paper_2_counts.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['Metric','Count','Definition']);w.writerows(metrics)
(P/'table_paper_2_counts.md').write_text('| Metric | Count | Definition |\n|---|---:|---|\n'+''.join(f'| {k} | {v} | {d} |\n' for k,v,d in metrics))
