import { TechnicalMetadataPopover, StatusBadge } from "./presentation";
import type { TechnicalAttribute } from "@/types/technical-attribute";
import { SourceInfo, VerificationBadge } from "./source-info";
export function TechnicalInfo({ records }: { records: TechnicalAttribute[] }) {
  const counts = new Map<string, number>();
  records.forEach((record) =>
    counts.set(
      record.attribute_key,
      (counts.get(record.attribute_key) ?? 0) + 1,
    ),
  );
  return (
    <section className="panel mt-6" id="technical">
      <p className="eyebrow">Source-backed attributes</p>
      <h2>Technical information</h2>
      {records.length === 0 ? (
        <p className="muted mt-4">No technical attribute records available.</p>
      ) : (
        <>
          <p className="muted mt-3 text-sm">
            Multiple entries for a key are retained separately. No preferred
            value is inferred.
          </p>
          <div className="technical-grid">
            {records.map((record) => (
              <article
                key={record.id}
                className="om-record"
                id={`record-${record.id}`}
              >

                <h3 className="font-semibold">{record.attribute_label}</h3>
                <p className="technical-value">
                  {record.value_number ?? record.value_text ?? "Not available"}
                  <span>{record.unit === "text" ? "" : record.unit ?? ""}</span>
                </p>
                <VerificationBadge status={record.verification_status} />
                {(counts.get(record.attribute_key) ?? 0) > 1 && (
                  <p className="muted mt-2 text-xs">
                    Multiple records for this attribute — review sources.
                  </p>
                )}
                <StatusBadge>{record.reviewed_provenance?.verification_level ?? "Level unavailable"}</StatusBadge>
                <TechnicalMetadataPopover fields={{"Record UUID":record.id,"Asset UUID":record.asset_id,"Attribute key":record.attribute_key,"Source UUID":record.source_id,"Source code":record.source?.source_code,"Evidence ID":record.reviewed_provenance?.evidence_id,Locator:record.reviewed_provenance?.source_locator,Authority:record.reviewed_provenance?.authority,Reviewer:record.reviewed_provenance?.reviewer,"Reviewed at":record.reviewed_provenance?.reviewed_at,Verification:record.verification_status}}/>
                <details className="field-locator"><summary>Source: {record.source?.source_code ?? "Unavailable"} · Page / locator</summary><p>{record.reviewed_provenance?.source_locator ?? "Unavailable"}</p></details>
                {record.reviewed_provenance?.verification_level === "L2" && <p className="summary-note">L2 đã review theo nguồn — SOURCE_REPORTED / HISTORICAL_DOCUMENTED. Không chứng nhận hiện trạng hôm nay hoặc chuẩn cao độ; ngữ cảnh và giới hạn theo hồ sơ nguồn.</p>}
                <p className="muted text-sm">Source authority: {record.source?.authority_level ?? "UNKNOWN"} · Source verification: {record.source?.verification_status ?? "UNAVAILABLE"}. Field review and source authority are separate.</p>
                <SourceInfo source={record.source} />
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
