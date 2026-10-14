import { TechnicalMetadataPopover } from "./presentation";
import type { SourcedRecord } from "@/types/data-source";
import { SourceInfo, VerificationBadge } from "./source-info";
export type HistoryItem = SourcedRecord & {
  eventDate: string;
  heading: string;
  fields: [string, string | null][];
};
export function OmHistory({
  title,
  sectionId,
  records,
  emptyMessage,
}: {
  title: string;
  sectionId: string;
  records: HistoryItem[];
  emptyMessage: string;
}) {
  return (
    <section className="panel mt-6" id={sectionId}>
      <div className="section-heading">
        <h2>{title}</h2>
        <span className="muted text-sm">{records.length} records</span>
      </div>
      {records.length === 0 ? (
        <p className="muted">{emptyMessage}</p>
      ) : (
        <div className="om-history">
          {records.map((record) => (
            <article
              className="om-record"
              id={`record-${record.id}`}
              key={record.id}
            >
              <div className="om-record-heading">
                <time dateTime={record.eventDate}>{record.eventDate}</time>
                <h3 className="font-semibold">{record.heading}</h3>
                <VerificationBadge status={record.verification_status} />
              </div>
              <dl className="source-grid">
                {record.fields.map(([label, value]) => (
                  <div key={label}>
                    <dt>{label}</dt>
                    <dd>{value ?? "Not available"}</dd>
                  </div>
                ))}
              </dl>
              <TechnicalMetadataPopover fields={{"Record UUID":record.id,"Asset UUID":record.asset_id,"Source UUID":record.source_id}}/><SourceInfo source={record.source} />
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
