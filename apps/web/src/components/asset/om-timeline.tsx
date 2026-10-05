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
        <p className="muted mt-4">No O&M timeline records available.</p>
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
              <SourceInfo source={event.source} />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
