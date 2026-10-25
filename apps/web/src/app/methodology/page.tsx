import { PageHeader } from "@/components/ui/page-header";
import { PanelDisclosure, MetricCard } from "@/components/ui/panel-section";
import { RetryView } from "@/components/ui/retry-view";
import { MethodologyWorkflowView } from "@/components/methodology/methodology-workflow-view";
import { MethodologyEvidenceDetail } from "@/components/methodology/methodology-evidence-detail";
import { getResearchSummary } from "@/lib/research-summary";
export const dynamic = "force-dynamic";

export default async function MethodologyPage() {
  const summary = await getResearchSummary();
  const workflow = summary.workflow;
  return <main className="page-shell methodology-page">
    <PageHeader eyebrow="Research" title="Methodology & Evidence"
      description="Follow the research from scope and reviewed data to acceptance, observed sessions and results." />
    {workflow.status === "AVAILABLE" ? <MethodologyWorkflowView workflow={workflow.data} /> :
      <section className="notice" role="status"><h2>Research workflow unavailable</h2>
        <p>The current evidence gates could not be checked. No previous result has been substituted for current research acceptance.</p><RetryView />
      </section>}
    <div className="methodology-metrics" aria-label="Live research inventory">
      <MetricCard label="Primary assets" value={summary.totals.primary} note="Research denominator" />
      <MetricCard label="Components" value={summary.totals.components} note="Reported separately" />
      <MetricCard label="Reviewed L2 records" value={summary.totals.all_l2 ?? "Unavailable"} note="Source-reported evidence" />
      <MetricCard label="Linked distinct files" value={summary.unique_linked_documents ?? "Unavailable"} note="Live API readback" />
    </div>
    <PanelDisclosure title="Detailed evidence, protocols and retained export">
      {summary.export_alignment !== "RECORD_READBACK_MATCH" && <p className="notice">
        {summary.export_alignment === "LIVE_READBACK_UNAVAILABLE"
          ? "Some current API responses are unavailable, so alignment with this retained export cannot be checked."
          : "The retained export differs from current live records. Its counts and historical acceptance are shown only for their original scope and dates."}
      </p>}
      <MethodologyEvidenceDetail summary={summary} />
    </PanelDisclosure>
  </main>;
}
