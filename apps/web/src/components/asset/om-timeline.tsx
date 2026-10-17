import { TechnicalMetadataPopover } from "./presentation";
import type { TimelineEvent } from "@/types/timeline";
import { SourceInfo, VerificationBadge } from "./source-info";
export function OmTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <section className="panel mt-6" id="timeline">
      <p className="eyebrow">Condition · Inspection · Repair · Maintenance</p>
      <h2>O&M timeline</h2>
      <p className="muted mt-2 text-sm">
        Newest event first. Verification is shown for each record.
      </p>
      {events.length === 0 ? (
        <div className="muted mt-4" role="status">
          <p>Chưa có sự kiện O&M được xác minh — No verified O&M record available.</p>
          <p className="mt-2 text-sm">Candidate historical records may exist, but none currently meet verification requirements.</p>
        </div>
      ) : (
        <ol className="om-timeline">
          {events.map((event) => (
            <li key={`${event.event_type}-${event.record_id}`}>
              <time dateTime={event.event_date}>{event.event_date}</time>
              <div className="om-record-heading">
                <span className="eyebrow">{event.event_type}</span>
                <VerificationBadge status={event.verification_status} />
              </div>
              <h3 className="font-semibold">{event.title}</h3>
              <p className="muted mt-2">
                {event.summary ?? "Summary not available."}
              </p>
              <a
                className="text-link inline-block mt-3"
                href={`#record-${event.record_id}`}
              >
                View record →
              </a>
              <TechnicalMetadataPopover fields={{"Event UUID":event.record_id,"Asset UUID":event.asset_id,"Source UUID":event.source_id}}/><SourceInfo source={event.source} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
