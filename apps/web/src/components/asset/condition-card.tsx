import { TechnicalMetadataPopover } from "./presentation";
import type { Condition } from "@/types/condition";
import { SourceInfo, VerificationBadge } from "./source-info";
export function ConditionCard({ condition }: { condition: Condition | null }) {
  return (
    <section className="panel mt-6" id="current-condition">
      <p className="eyebrow">Latest verified assessment</p>
      <h2>Current condition</h2>
      {condition ? (
        <>
          <div className="om-record-heading">
            <h3 className="font-semibold">{condition.condition_status}</h3>
            <time dateTime={condition.condition_date}>
              {condition.condition_date}
            </time>
            <VerificationBadge status={condition.verification_status} />
          </div>
          <dl className="source-grid">
            <div>
              <dt>Summary</dt>
              <dd>{condition.summary ?? "Not available"}</dd>
            </div>
            <div>
              <dt>Defect</dt>
              <dd>{condition.defect_description ?? "Not available"}</dd>
            </div>
            <div>
              <dt>Recommended action</dt>
              <dd>{condition.recommended_action ?? "Not available"}</dd>
            </div>
          </dl>
          <TechnicalMetadataPopover fields={{"Record UUID":condition.id,"Asset UUID":condition.asset_id,"Source UUID":condition.source_id}}/><SourceInfo source={condition.source} />
        </>
      ) : (
        <p className="muted mt-4">No verified condition record is available.</p>
      )}
    </section>
  );
}
