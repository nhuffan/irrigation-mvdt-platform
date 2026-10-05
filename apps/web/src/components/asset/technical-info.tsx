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
                <p className="eyebrow">{record.attribute_key}</p>
                <h3 className="font-semibold">{record.attribute_label}</h3>
                <p className="technical-value">
                  {record.value_number ?? record.value_text ?? "Not available"}
                  <span>{record.unit ?? ""}</span>
                </p>
                <VerificationBadge status={record.verification_status} />
                {(counts.get(record.attribute_key) ?? 0) > 1 && (
                  <p className="muted mt-2 text-xs">
                    Multiple records for this attribute — review sources.
                  </p>
                )}
                <SourceInfo source={record.source} />
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
