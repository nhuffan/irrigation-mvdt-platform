import Link from "next/link";
import { publicEvidenceText, technicalValueDetails } from "@/lib/asset-information";
import { evidenceDisplayText } from "@/lib/evidence-display";
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
            {records.map((record) => {
              const value = technicalValueDetails(record);
              const locator = record.reviewed_provenance?.source_locator;
              const sourceCode = record.source?.source_code ?? record.reviewed_provenance?.source_code ?? "Unavailable";
              return (
              <article
                key={record.id}
                className="om-record"
                id={`record-${record.id}`}
              >

                <h3 className="font-semibold">{evidenceDisplayText(publicEvidenceText(record.attribute_label))}</h3>
                <p className="technical-value">
                  {value.value}
                  {value.valueUnit && <span>{value.valueUnit}</span>}
                </p>
                {value.additionalText && <p className="muted text-sm">Source text: {value.additionalText}</p>}
                <p className="muted text-sm">Unit: {value.unit}{value.valueState !== "AVAILABLE" && <> · Value state: {value.valueState.replaceAll("_", " ")}</>}</p>
                <VerificationBadge status={record.verification_status} />
                {(counts.get(record.attribute_key) ?? 0) > 1 && (
                  <p className="muted mt-2 text-xs">
                    Multiple records for this attribute — review sources.
                  </p>
                )}
                <StatusBadge>{record.reviewed_provenance?.verification_level ?? "Level unavailable"}</StatusBadge>
                <TechnicalMetadataPopover fields={{"Record UUID":record.id,"Asset UUID":record.asset_id,"Attribute key":record.attribute_key,"Source UUID":record.source_id,"Source code":record.source?.source_code,"Evidence ID":record.reviewed_provenance?.evidence_id,Locator:locator ? publicEvidenceText(locator) : "Unavailable",Authority:publicEvidenceText(record.reviewed_provenance?.authority),Verification:record.verification_status}}/>
                <div className="field-locator" style={{ overflowWrap: "anywhere" }}><p>Source: {record.source_id ? <Link className="text-link" href={`/data-sources/${encodeURIComponent(record.source_id)}/documents`}>{sourceCode}</Link> : sourceCode}</p><p>Exact locator: {locator ? publicEvidenceText(locator) : "Unavailable"}</p></div>
                {record.reviewed_provenance?.verification_level === "L2" && <p className="summary-note">SOURCE_REPORTED / HISTORICAL_DOCUMENTED · Reviewed L2 from historical or design documents. This does not certify present condition, completed repairs, elevation datum or geometry; the exact source locator retains the field context.</p>}
                <p className="muted text-sm">Source authority: {record.source?.authority_level ?? "UNKNOWN"} · Source verification: {record.source?.verification_status ?? "UNAVAILABLE"}. Field review and source authority are separate.</p>
                <SourceInfo source={record.source} />
              </article>
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}
