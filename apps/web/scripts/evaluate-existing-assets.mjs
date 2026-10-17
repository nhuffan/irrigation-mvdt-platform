// Read-only evaluation of the existing capture_api.py output; no paper denominator changes.
import { readFile, writeFile } from 'node:fs/promises';
import { descendantIds, hierarchyCoverage, l2Count } from '../src/lib/asset-hierarchy.ts';
const [input, output] = process.argv.slice(2);
if (!input || !output) throw new Error('Usage: node scripts/evaluate-existing-assets.mjs API_READBACK OUTPUT_JSON');
const readback=JSON.parse(await readFile(input,'utf8'));
const entries=Object.values(readback).filter(v=>v.asset.asset_code.startsWith('RS-'));
const assets=entries.map(v=>v.asset);
const records=Object.fromEntries(entries.map(v=>[v.asset.id,v.technical]));
const result={evaluated_at:new Date().toISOString(),basis:'Read-only API snapshot; not browser acceptance or source admission',totals:hierarchyCoverage(assets,records),assets:entries.map(v=>({
 id:v.asset.id,code:v.asset.asset_code,parent_id:v.asset.parent_asset_id,
 direct_l2:l2Count([v.asset.id],records),descendant_l2:l2Count(descendantIds(assets,v.asset.id),records),
 provenance_with_source_and_locator:v.technical.filter(t=>t.source_id&&t.reviewed_provenance?.source_locator).length,
 location:v.asset.location?.location_status??'NO_LOCATION',
 verified_om:v.timeline.filter(t=>t.verification_status==='VERIFIED').length,
 model_state:v['model-links'].length?'REPRESENTATIVE_LINK_ONLY':'NO_ESTABLISHED_LINK',
 attachments:v.documents.length
}))};
await writeFile(output,JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result.totals));
