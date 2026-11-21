import { PageHeader } from "@/components/ui/page-header";
import { RetryView } from "@/components/ui/retry-view";
import { MethodologyWorkflowView } from "@/components/methodology/methodology-workflow-view";
import { MethodologyEvidenceDetail } from "@/components/methodology/methodology-evidence-detail";
import { MethodologyOverview } from "@/components/methodology/methodology-overview";
import { MethodologyDisclosure } from "@/components/methodology/methodology-disclosure";
import { getResearchSummary } from "@/lib/research-summary";
import { SYNTHETIC_DEMO } from "@/lib/site-scope";
export const dynamic = "force-dynamic";

export default async function MethodologyPage() {
  if (SYNTHETIC_DEMO) return <main className="page-shell methodology-page">
    <PageHeader eyebrow="Research" title="Methodology & Evidence"
      description="The research methodology and its evidence gates run on the private research deployment. This public demo holds synthetic data only." />
  </main>;
  const summary = await getResearchSummary();
  const workflow = summary.workflow;
  return <main className="page-shell methodology-page">
    <PageHeader eyebrow="Research" title="Methodology & Evidence"
      description="A Level-1 MVDT framework connecting assets, context and source evidence." />
    <MethodologyOverview summary={summary} />
    <MethodologyDisclosure title="Research Workflow & Acceptance (advanced)">
      {workflow.status === "AVAILABLE" ? <MethodologyWorkflowView workflow={workflow.data} /> :
        <section className="notice" role="status"><h2>Research workflow unavailable</h2>
          <p>The current evidence gates could not be checked. No previous result has been substituted for current research acceptance.</p><RetryView />
        </section>}
      <MethodologyDisclosure title="Detailed evidence, protocols and retained export" retained>
        {summary.export_alignment !== "RECORD_READBACK_MATCH" && <p className="notice">
          {summary.export_alignment === "LIVE_READBACK_UNAVAILABLE"
            ? "Some current API responses are unavailable, so alignment with this retained export cannot be checked."
            : "The retained export differs from current live records. Its counts and historical acceptance are shown only for their original scope and dates."}
        </p>}
        <MethodologyEvidenceDetail summary={summary} />
      </MethodologyDisclosure>
    </MethodologyDisclosure>
  </main>;
}
