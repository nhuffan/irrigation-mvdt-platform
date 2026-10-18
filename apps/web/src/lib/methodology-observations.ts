import type { Asset } from "../types/asset";
import type { ModelRecord } from "../types/media";
import type { ExplorerRecords } from "./explorer-data";
import { stableReadback } from "./methodology-completion.ts";
type SourceObservation = { id: string; source_code: string; title: string; source_type: string; source_date: string | null; authority_level: string | null; verification_status: string };
export function completionReadback(assets: Asset[], records: ExplorerRecords, models: ModelRecord[] | null, sources: SourceObservation[] | null = null) {
  return {
    assets: Object.fromEntries([...assets].sort((a, b) => a.asset_code.localeCompare(b.asset_code)).map(a => {
      const r = records[a.id];
      const l = a.location;
      return [a.asset_code, {
        id: a.id, name: a.name, parent_asset_id: a.parent_asset_id, category_code: a.category?.code ?? null, category_name: a.category?.name ?? null, geometry: a.geometry ?? null,
        location: { location_status: l?.location_status ?? null, review_state: l?.review_state ?? null, evidence_id: l?.evidence_id ?? null,
          crs: l?.crs ?? null, geometry: l?.geometry ?? null, reviewed_at: l?.reviewed_at ?? null },
        technical_labels: r?.technical == null ? null : [...r.technical].sort((a,b) => a.id.localeCompare(b.id)).map(t => ({ id:t.id, key:t.attribute_key,
          label:t.attribute_label ?? null, source_id:t.source_id, nested_source_id:t.source?.id ?? null })),
        documents: r?.documents == null ? null : [...r.documents].sort((a,b) => a.id.localeCompare(b.id)).map(d => ({ id:d.id, source_id:d.source_id, original_file_name:d.original_file_name ?? null,
          checksum_sha256:d.checksum_sha256, mime_type:d.mime_type, file_size:d.file_size, page_count:d.page_count })),
        links: r?.links == null ? null : [...r.links].sort((a,b) => a.id.localeCompare(b.id)).map(l => ({ id:l.id, model_id:l.model_id, asset_id:l.asset_id, object_key:l.object_key, verification_status:l.verification_status })),
        events: r?.events == null ? null : [...r.events].sort((a,b) => a.record_id.localeCompare(b.record_id)).map(e => ({ record_id:e.record_id, event_type:e.event_type, event_date:e.event_date, asset_id:e.asset_id, source_id:e.source_id, verification_status:e.verification_status })),
        condition: r?.conditionError || !r ? undefined : r.condition ? { id:r.condition.id, asset_id:r.condition.asset_id, source_id:r.condition.source_id, verification_status:r.condition.verification_status } : null,
      }];
    })),
    sources: sources == null ? null : [...sources].sort((a,b) => a.id.localeCompare(b.id)),
    models: models == null ? null : [...models].sort((a,b) => a.id.localeCompare(b.id)).map(m => ({ id:m.id, source_id:m.source_id, model_code:m.model_code, name:m.name ?? null, format:m.format ?? null, coordinate_mode:m.coordinate_mode,
      longitude:m.longitude, latitude:m.latitude, height:m.height, heading:m.heading, pitch:m.pitch, roll:m.roll, scale:m.scale, verification_status:m.verification_status })),
  };
}
export function completionAlignment(snapshot: unknown, observed: unknown): "RECORD_READBACK_MATCH" | "DIFFERENT_OR_UNAVAILABLE" | "UNAVAILABLE" {
  if (!snapshot || typeof snapshot !== "object" || !("completion" in snapshot)) return "UNAVAILABLE";
  const c = (snapshot as { completion?: { live_readback?: unknown } }).completion;
  if (!c?.live_readback) return "UNAVAILABLE";
  return stableReadback(c.live_readback) === stableReadback(observed) ? "RECORD_READBACK_MATCH" : "DIFFERENT_OR_UNAVAILABLE";
}
