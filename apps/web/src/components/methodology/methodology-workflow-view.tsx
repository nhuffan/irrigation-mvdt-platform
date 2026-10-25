"use client";

import { useSyncExternalStore } from "react";
import { OriginLink } from "@/components/documents/document-link";
import { workflowEvidenceHref, type MethodologyWorkflow } from "@/lib/research-workflow";
import styles from "./methodology-workflow.module.css";

const subscribeHash = (notify: () => void) => {
  window.addEventListener("hashchange", notify);
  return () => window.removeEventListener("hashchange", notify);
};
const currentHash = () => window.location.hash;
const serverHash = () => "";
const label = (value: string) => value.replaceAll("_", " ").toLowerCase().replace(/^./, c => c.toUpperCase());
const countLabels: Record<string, string> = {
  retained_files: "Source manifest files",
  source_manifest_files: "Source manifest files",
  located_by_checksum: "Located by exact checksum",
};
const shown = (value: number | string | null | undefined) => value ?? "Unavailable";
const descriptions: Record<string, string> = {
  DATA_REVIEW_PENDING: "Complete the evidence reviews and approvals before freezing the dataset.",
  DATASET_NOT_FROZEN: "Reviewed inputs are ready for an immutable, versioned dataset freeze.",
  FUNCTIONAL_ACCEPTANCE_PENDING: "Record research acceptance for the reviewed dataset and its exact asset scope.",
  OBSERVATIONS_PENDING: "Collect the planned baseline and MVDT sessions and questionnaire responses.",
  ANALYSIS_READY: "Approved observations are ready for analysis and a version-pinned results export.",
  RESEARCH_COMPLETE: "Required reviews, acceptance and observations are recorded against the frozen dataset.",
};

type Evidence = MethodologyWorkflow["steps"][number]["evidence"][number];
type Blocker = MethodologyWorkflow["steps"][number]["blockers"][number];
function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) return null;
  return <details className={styles.evidence}>
    <summary>Evidence and input templates ({evidence.length})</summary>
    <ul>{evidence.map((e, index) => {
      const href = workflowEvidenceHref(e.path);
      return <li key={`${e.path}-${index}`}>
        {href ? <a href={href} target="_blank" rel="noreferrer">{e.label} ↗</a> : <span>{e.label}</span>}
        {e.path && <small>{e.path}</small>}{e.sha256 && <code>{e.sha256}</code>}
      </li>;
    })}</ul>
  </details>;
}
function BlockerList({ blockers, primaryAction }: { blockers: Blocker[]; primaryAction?: string }) {
  return <ul className={styles.blockers}>{blockers.map((b, index) => <li key={`${b.code}-${index}`}>
    <p><strong>{b.message}</strong></p>
    {b.next_action !== primaryAction && <p>{b.next_action}</p>}
    <small>{b.code}</small>
    <EvidenceList evidence={b.evidence} />
  </li>)}</ul>;
}

function ResearchMetrics({ metrics }: { metrics: MethodologyWorkflow["metrics"] }) {
  const rows = metrics.rows;
  return <div className={styles.results}>
    <div className={styles.resultMeta}><span>Dataset: <strong>{metrics.dataset_version ?? "Not frozen"}</strong></span><span>Observations: <strong>{metrics.observation_count ?? "Not collected"}</strong></span><span>{label(metrics.status)}</span></div>
    {rows.length ? <div className="methodology-table"><table>
      <caption>Research metrics · approved frozen inputs only</caption>
      <thead><tr><th>Metric</th><th>Numerator / denominator</th><th>Value / status</th><th>Version / observations</th><th>Authority and missingness</th></tr></thead>
      <tbody>{rows.map(m => <tr key={m.id}><th scope="row">{m.label}</th><td>{shown(m.numerator)} / {shown(m.denominator)}</td><td>{shown(m.value)} {m.unit}<small>{m.status}</small></td><td>{m.dataset_version}<small>{shown(m.observation_count)} observations</small></td><td>{m.authority}<small>{m.verification}</small><small>{m.missing_reason}</small></td></tr>)}</tbody>
    </table></div> : <p>Research metrics are unavailable until the required dataset and observation gates are satisfied. Missing measurements have no calculated score.</p>}
    {metrics.status === "APPROVED_FROZEN" && metrics.retrieval.length > 0 && <details className={styles.evidence}><summary>Retrieval outcomes and failures</summary><div className="methodology-table"><table><thead><tr><th>Task / cohort</th><th>Workflow</th><th>Successful / attempts</th><th>Success rate</th><th>Successful time median (seconds)</th></tr></thead><tbody>{metrics.retrieval.map((r,i) => <tr key={i}><th scope="row">{r.task_id}<small>{r.participant_group}</small></th><td>{r.workflow}</td><td>{r.successes} / {r.attempts}</td><td>{shown(r.success_rate)}</td><td>{shown(r.successful_time_median)}</td></tr>)}</tbody></table></div></details>}
    {metrics.status === "APPROVED_FROZEN" && metrics.paired_time.length > 0 && <details className={styles.evidence}><summary>Paired time comparison and exclusions</summary><div className="methodology-table"><table><thead><tr><th>Task / cohort</th><th>Eligible / pairs</th><th>Unmatched / excluded</th><th>Median time reduction</th></tr></thead><tbody>{metrics.paired_time.map((r,i) => <tr key={i}><th scope="row">{r.task_id}<small>{r.participant_group}</small></th><td>{r.eligible_pairs} / {r.pairs}</td><td>{r.unmatched_pairs} / {r.failed_or_zero_baseline_pairs}</td><td>{r.median_time_reduction_percent === null ? "Unavailable" : `${r.median_time_reduction_percent}%`}</td></tr>)}</tbody></table></div></details>}
    {metrics.status === "APPROVED_FROZEN" && metrics.questionnaire.length > 0 && <details className={styles.evidence}><summary>Questionnaire responses, N/A and nonresponses</summary><div className="methodology-table"><table><thead><tr><th>Item / cohort</th><th>Responses / missing / N/A</th><th>Mean / median</th><th>Min / max</th><th>Sample standard deviation</th></tr></thead><tbody>{metrics.questionnaire.map((r,i) => <tr key={i}><th scope="row">{r.question}<small>{r.participant_group}</small></th><td>{r.n} / {r.missing} / {r.na}</td><td>{shown(r.mean)} / {shown(r.median)}</td><td>{shown(r.min)} / {shown(r.max)}</td><td>{shown(r.sample_std_dev)}</td></tr>)}</tbody></table></div></details>}
  </div>;
}

function FunctionalAcceptance({ checks }: { checks: MethodologyWorkflow["acceptance"] }) {
  return <details className={styles.evidence}>
    <summary>Current research acceptance matrix ({checks.length} checks)</summary>
    <p>PASS requires a recorded reviewer, timestamp, dataset version, in-scope Asset ID and retained evidence. Unsupported historical outcomes remain NOT_TESTED here.</p>
    <div className="methodology-table"><table>
      <caption>Effective research acceptance · current dataset scope</caption>
      <thead><tr><th>Check / function</th><th>Research status</th><th>Version / asset</th><th>Recorded at / evidence</th><th>Missing requirements</th></tr></thead>
      <tbody>{checks.map(check => <tr key={check.id}>
        <th scope="row">{check.id}<small>{check.label}</small></th>
        <td>{check.status}<small>Recorded: {check.recorded_status}</small></td>
        <td>{check.dataset_version ?? "Unavailable"}{check.asset_id ? <small><OriginLink href={`/assets/${check.asset_id}`}>Open asset →</OriginLink></small> : <small>No in-scope Asset ID</small>}</td>
        <td>{check.checked_at ?? "No valid timestamp"}<small>{check.evidence_count} retained artifact(s)</small>{check.evidence_sha256.length > 0 && <details><summary>Artifact hashes</summary>{check.evidence_sha256.map((sha,i) => <code key={i}>{sha}</code>)}</details>}</td>
        <td>{check.missing.length ? check.missing.join(" · ") : "Required metadata recorded"}</td>
      </tr>)}</tbody>
    </table></div>
  </details>;
}

export function MethodologyWorkflowView({ workflow }: { workflow: MethodologyWorkflow }) {
  const hash = useSyncExternalStore(subscribeHash, currentHash, serverHash);
  const selected = workflow.steps.find(s => hash === `#research-${s.id}`) ?? workflow.steps.find(s => s.status !== "COMPLETE") ?? workflow.steps[0];
  if (!selected) return <p className="notice">Workflow steps are unavailable. Retry when the evidence service is reachable.</p>;
  const remaining = selected.blockers.slice(3);
  return <section className={styles.workflow} aria-label="Research workflow">
    <div className={styles.overview}>
      <div className={styles.statusPair}>
        <p>Software workflow: <strong>{workflow.software_status === "WORKFLOW_READY" ? "Complete" : "Unavailable"}</strong></p>
        <p>Research evidence: <strong className={workflow.research_status === "COMPLETE" ? undefined : styles.pending}>{workflow.research_status === "COMPLETE" ? "Complete" : "Pending"}</strong></p>
      </div>
      <p>{descriptions[workflow.state] ?? label(workflow.state)}</p>
      <div className={styles.metadata}><span>{workflow.state}</span><span>{workflow.compiler_status}</span><span>{workflow.dataset_status}</span><span>Dataset {workflow.dataset_version ?? "Unassigned"}</span></div>
    </div>
    <nav className={styles.steps} aria-label="Research workflow steps">{workflow.steps.map((step,index) => <a
      href={`#research-${step.id}`} id={`research-tab-${step.id}`} key={step.id}
      aria-current={selected.id === step.id ? "step" : undefined}>
      <span className={styles.stepNumber}>{index + 1}</span><span><strong>{step.label}</strong><small>{label(step.status)}</small></span>
    </a>)}</nav>
    <section className={styles.stepPanel} id={`research-${selected.id}`} aria-labelledby={`research-tab-${selected.id}`}>
      <header className={styles.stepHeading}><h2>{selected.label}</h2><span className={styles.badge}>{label(selected.status)}</span></header>
      <div className={styles.stepBody}>
        {Object.keys(selected.counts).length > 0 && <dl className={styles.counts}>{Object.entries(selected.counts).map(([key,value]) => <div key={key}><dt>{countLabels[key] ?? label(key)}</dt><dd>{value ?? "Unavailable"}</dd></div>)}</dl>}
        <div className={styles.nextAction}><h3>{selected.status === "COMPLETE" ? "Recorded evidence" : "Next action"}</h3><p>{selected.next_action}</p></div>
        {selected.blockers.length > 0 && <><h3 className={styles.blockerHeading}>Remaining requirements ({selected.blockers.length})</h3><BlockerList blockers={selected.blockers.slice(0,3)} primaryAction={selected.next_action} />
          {remaining.length > 0 && <details className={styles.evidence}><summary>Show {remaining.length} more requirements</summary><BlockerList blockers={remaining} primaryAction={selected.next_action} /></details>}</>}
        {selected.id === "data" && workflow.approvals.length > 0 && <section className={styles.approvals} aria-label="Scoped approvals">
          <h3>Scoped approvals</h3>
          <ul>{workflow.approvals.map((approval,index) => <li key={`${approval.type}-${approval.scope}-${index}`}>
            <span><strong>{label(approval.type)}</strong><small>{approval.scope === "MAIM" ? "MAIM" : label(approval.scope)}</small></span>
            <span className={styles.badge}>{label(approval.status)}</span>
          </li>)}</ul>
        </section>}
        {selected.id === "functional" && <FunctionalAcceptance checks={workflow.acceptance} />}
        {selected.id === "results" && <ResearchMetrics metrics={workflow.metrics} />}
        <EvidenceList evidence={selected.evidence} />
      </div>
    </section>
    <div className={styles.readback}><span>Checked {new Date(workflow.generated_at).toLocaleString("en-GB", { timeZone: "UTC" })} UTC</span><a href="/api/research-summary">Read research summary JSON →</a></div>
  </section>;
}
