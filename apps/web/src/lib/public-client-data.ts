import type { Asset, AssetLocation, GeoJsonGeometry } from "../types/asset";
import type { DataSource } from "../types/data-source";
import type { Condition } from "../types/condition";
import type { TechnicalAttribute } from "../types/technical-attribute";
import type { TimelineEvent } from "../types/timeline";
import type { DocumentRecord, ModelRecord, ModelAssetLink } from "../types/media";
import type { ExplorerData, ExplorerRecords } from "./explorer-data";
import { publicEvidenceHref, publicEvidenceText } from "./asset-information.ts";

const text = (value: string | null) => value === null ? null : publicEvidenceText(value);
/** Explicit client-payload allowlists; raw API/readback records are never modified. */
export function publicDataSource(source: DataSource | null): DataSource | null {
  return source === null ? null : {
    id: source.id, reservoir_id: source.reservoir_id, source_code: source.source_code,
    source_type: source.source_type, title: publicEvidenceText(source.title),
    file_name: text(source.file_name), source_date: source.source_date,
    source_owner: null, authority_level: text(source.authority_level),
    verification_status: source.verification_status, notes: null,
    created_at: source.created_at, updated_at: source.updated_at,
  };
}
function publicGeometry(geometry: GeoJsonGeometry | null): GeoJsonGeometry | null {
  if (geometry === null || geometry === undefined) return geometry;
  return { type: geometry.type, coordinates: geometry.coordinates } as GeoJsonGeometry;
}
function publicLocation(location: AssetLocation | null | undefined): AssetLocation | null | undefined {
  return location == null ? location : {
    location_status: location.location_status, geometry: location.location_status === "NO_LOCATION" ? null : publicGeometry(location.geometry),
    geometry_type: location.geometry_type, crs: location.crs, source: text(location.source),
    source_url: publicEvidenceHref(location.source_url), locator: text(location.locator),
    evidence_id: location.evidence_id, accuracy_limitation: publicEvidenceText(location.accuracy_limitation),
    verification_note: publicEvidenceText(location.verification_note), reviewer: null,
    reviewed_at: location.reviewed_at, review_state: location.review_state,
    spatial_disposition: location.spatial_disposition, candidate_count: location.candidate_count,
    reason: location.reason == null ? null : publicEvidenceText(location.reason),
    next_action: location.next_action == null ? null : publicEvidenceText(location.next_action),
    coordinate_basis: location.coordinate_basis == null ? null : publicEvidenceText(location.coordinate_basis),
    estimated_accuracy_m: location.estimated_accuracy_m, physical_page: location.physical_page,
    document_id: location.document_id, source_id: location.source_id, source_sha256: location.source_sha256,
    reviewer_role: location.reviewer_role,
    candidates: location.candidates?.map(candidate => ({
      candidate_id: candidate.candidate_id, source_label: publicEvidenceText(candidate.source_label),
      source: publicEvidenceText(candidate.source), source_url: publicEvidenceHref(candidate.source_url),
      document_id: candidate.document_id, physical_page: candidate.physical_page,
      locator: publicEvidenceText(candidate.locator), coordinate_basis: publicEvidenceText(candidate.coordinate_basis),
      source_crs: publicEvidenceText(candidate.source_crs), identity_basis: publicEvidenceText(candidate.identity_basis),
      accuracy_limitation: publicEvidenceText(candidate.accuracy_limitation),
      issues: candidate.issues.map(publicEvidenceText),
    })),
  };
}
export function publicAssets(assets: Asset[]): Asset[] {
  return assets.map(asset => ({
    id: asset.id, reservoir_id: asset.reservoir_id, parent_asset_id: asset.parent_asset_id,
    asset_code: asset.asset_code, name: asset.name, description: text(asset.description),
    technical_description: text(asset.technical_description), condition_status: asset.condition_status,
    data_status: asset.data_status,
    category: { id: asset.category.id, code: asset.category.code, name: asset.category.name },
    geometry: publicGeometry(asset.geometry), location: publicLocation(asset.location),
  }));
}
function publicTechnical(record: TechnicalAttribute): TechnicalAttribute {
  const provenance = record.reviewed_provenance;
  return {
    id: record.id, asset_id: record.asset_id, source_id: record.source_id,
    source: publicDataSource(record.source), verification_status: record.verification_status,
    created_at: record.created_at, updated_at: record.updated_at,
    attribute_key: record.attribute_key, attribute_label: record.attribute_label,
    value_number: record.value_number, value_text: text(record.value_text), unit: record.unit,
    reviewed_provenance: provenance === null ? null : {
      verification_level: provenance.verification_level, source_code: provenance.source_code,
      evidence_id: provenance.evidence_id, source_locator: publicEvidenceText(provenance.source_locator),
      authority: publicEvidenceText(provenance.authority), reviewer: "Not published",
      reviewed_at: provenance.reviewed_at,
    },
  };
}
function publicCondition(condition: Condition | null): Condition | null {
  return condition === null ? null : {
    id: condition.id, asset_id: condition.asset_id, source_id: condition.source_id,
    source: publicDataSource(condition.source), verification_status: condition.verification_status,
    created_at: condition.created_at, updated_at: condition.updated_at,
    condition_date: condition.condition_date, condition_status: condition.condition_status,
    summary: text(condition.summary), defect_description: text(condition.defect_description),
    recommended_action: text(condition.recommended_action),
  };
}
function publicEvent(event: TimelineEvent): TimelineEvent {
  return {
    event_type: event.event_type, event_date: event.event_date, title: publicEvidenceText(event.title),
    summary: text(event.summary), record_id: event.record_id, asset_id: event.asset_id,
    source_id: event.source_id, source: publicDataSource(event.source), verification_status: event.verification_status,
  };
}
function publicDocument(document: DocumentRecord): DocumentRecord {
  return {
    id: document.id, source_id: document.source_id, document_code: document.document_code,
    original_file_name: publicEvidenceText(document.original_file_name), mime_type: document.mime_type,
    file_size: document.file_size, checksum_sha256: document.checksum_sha256,
    page_count: document.page_count, uploaded_at: document.uploaded_at,
    source: publicDataSource(document.source)!,
  };
}
function publicLink(link: ModelAssetLink): ModelAssetLink {
  return {
    id: link.id, model_id: link.model_id, asset_id: link.asset_id, reservoir_id: link.reservoir_id,
    object_key: link.object_key, object_name: text(link.object_name), verification_status: link.verification_status,
  };
}
export function publicExplorerRecords(records: ExplorerRecords): ExplorerRecords {
  return Object.fromEntries(Object.entries(records).map(([id, value]): [string, ExplorerData] => [id, {
    technical: value.technical === null ? null : value.technical.map(publicTechnical),
    events: value.events === null ? null : value.events.map(publicEvent),
    condition: publicCondition(value.condition), conditionError: value.conditionError,
    documents: value.documents === null ? null : value.documents.map(publicDocument),
    links: value.links === null ? null : value.links.map(publicLink),
  }]));
}
export function publicModels(models: ModelRecord[]): ModelRecord[] {
  return models.map(model => ({
    id: model.id, reservoir_id: model.reservoir_id, source_id: model.source_id,
    model_code: model.model_code, name: model.name, model_type: model.model_type, format: model.format,
    coordinate_mode: model.coordinate_mode, longitude: model.longitude, latitude: model.latitude,
    height: model.height, heading: model.heading, pitch: model.pitch, roll: model.roll, scale: model.scale,
    verification_status: model.verification_status, source: publicDataSource(model.source),
  }));
}
