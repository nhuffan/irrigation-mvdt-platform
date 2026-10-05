import {
  getAssetTechnical,
  getAssetConditions,
  getAssetCurrentCondition,
  getAssetInspections,
  getAssetRepairs,
  getAssetMaintenance,
  getAssetTimeline,
} from "@/lib/api";
import { ConditionCard } from "./condition-card";
import { TechnicalInfo } from "./technical-info";
import { OmHistory } from "./om-history";
import { OmTimeline } from "./om-timeline";
import { SectionError } from "./section-error";

export async function AssetOm({ assetId }: { assetId: string }) {
  const [
    current,
    technical,
    conditions,
    inspections,
    repairs,
    maintenance,
    timeline,
  ] = await Promise.allSettled([
    getAssetCurrentCondition(assetId),
    getAssetTechnical(assetId),
    getAssetConditions(assetId),
    getAssetInspections(assetId),
    getAssetRepairs(assetId),
    getAssetMaintenance(assetId),
    getAssetTimeline(assetId),
  ]);
  return (
    <div id="asset-om">
      <nav className="om-nav" aria-label="Asset information sections">
        <a href="#current-condition">Condition</a>
        <a href="#technical">Technical</a>
        <a href="#timeline">Timeline</a>
        <a href="#inspections">Inspections</a>
        <a href="#repairs">Repairs</a>
        <a href="#maintenance">Maintenance</a>
      </nav>
      {current.status === "fulfilled" ? (
        <ConditionCard condition={current.value} />
      ) : (
        <SectionError title="Current condition" />
      )}
      {technical.status === "fulfilled" ? (
        <TechnicalInfo records={technical.value} />
      ) : (
        <SectionError title="Technical information" />
      )}
      {timeline.status === "fulfilled" ? (
        <OmTimeline events={timeline.value} />
      ) : (
        <SectionError title="O&M timeline" />
      )}
      {conditions.status === "fulfilled" ? (
        <OmHistory
          title="Condition history"
          sectionId="conditions"
          emptyMessage="No condition records available."
          records={conditions.value.map((r) => ({
            ...r,
            eventDate: r.condition_date,
            heading: r.condition_status,
            fields: [
              ["Summary", r.summary],
              ["Defect", r.defect_description],
              ["Recommended action", r.recommended_action],
            ],
          }))}
        />
      ) : (
        <SectionError title="Condition history" />
      )}
      {inspections.status === "fulfilled" ? (
        <OmHistory
          title="Inspection history"
          sectionId="inspections"
          emptyMessage="No inspection records available."
          records={inspections.value.map((r) => ({
            ...r,
            eventDate: r.inspection_date,
            heading: r.inspection_type ?? "Inspection type not available",
            fields: [
              ["Inspector", r.inspector],
              ["Summary", r.summary],
              ["Observation", r.observation],
              ["Condition", r.condition_status],
              ["Recommended action", r.recommended_action],
            ],
          }))}
        />
      ) : (
        <SectionError title="Inspection history" />
      )}
      {repairs.status === "fulfilled" ? (
        <OmHistory
          title="Repair history"
          sectionId="repairs"
          emptyMessage="No repair records available."
          records={repairs.value.map((r) => ({
            ...r,
            eventDate: r.repair_date,
            heading: r.repair_type ?? "Repair type not available",
            fields: [
              ["Problem", r.problem_description],
              ["Repair action", r.repair_description],
              ["Result", r.result],
              ["Responsible unit", r.responsible_unit],
            ],
          }))}
        />
      ) : (
        <SectionError title="Repair history" />
      )}
      {maintenance.status === "fulfilled" ? (
        <OmHistory
          title="Maintenance history"
          sectionId="maintenance"
          emptyMessage="No maintenance records available."
          records={maintenance.value.map((r) => ({
            ...r,
            eventDate: r.maintenance_date,
            heading: r.maintenance_type ?? "Maintenance type not available",
            fields: [
              ["Description", r.description],
              ["Result", r.result],
              ["Responsible unit", r.responsible_unit],
            ],
          }))}
        />
      ) : (
        <SectionError title="Maintenance history" />
      )}
    </div>
  );
}
