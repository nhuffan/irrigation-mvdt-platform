export type WorkflowEvidence = { label: string; path: string | null; sha256: string | null };
export type WorkflowBlocker = { code: string; message: string; next_action: string; evidence: WorkflowEvidence[] };
export type WorkflowStep = { id: "scope" | "data" | "functional" | "evaluation" | "results"; label: string; status: "COMPLETE" | "PENDING" | "BLOCKED" | "STALE"; counts: Record<string, number | null>; blockers: WorkflowBlocker[]; evidence: WorkflowEvidence[]; next_action: string };
export type WorkflowMetric = { id: string; numerator: number | null; denominator: number | null; value: number | null; status: string };
export type WorkflowMetricRow = WorkflowMetric & { label: string; missing_reason: string | null; observation_count: number | null; dataset_version: string | null; unit?: string | null; authority?: string | null; verification?: string | null };
export type WorkflowAcceptance = {id:string;label:string;recorded_status:string;status:string;dataset_version:string|null;asset_id:string|null;missing:string[];evidence_count:number;evidence_sha256:string[];checked_at:string|null};
export type WorkflowApproval = {type:string;scope:string;status:"APPROVED"|"PENDING"};
export type MethodologyWorkflow = {
  schema_version: "METHODOLOGY-WORKFLOW-v1"; generated_at: string; reservoir_ids: string[];
  dataset_version: string | null; state: string; compiler_status: string; software_status: "WORKFLOW_READY" | "UNAVAILABLE";
  research_status: "PENDING" | "COMPLETE"; dataset_status: "NOT_FROZEN" | "FROZEN" | "INVALID" | "VERSION_MISMATCH" | "STALE_SCOPE" | "HASH_MISMATCH";
  steps: WorkflowStep[]; acceptance: WorkflowAcceptance[]; approvals: WorkflowApproval[]; fingerprints: Record<string, string | null>;
  metrics: { status: "NOT_COLLECTED" | "APPROVED_FROZEN"; dataset_version: string | null; snapshot_sha256: string | null; observation_count: number | null; coverage: WorkflowMetric[]; rows: WorkflowMetricRow[];
    retrieval: {task_id:string;participant_group:string;workflow:string;attempts:number;successes:number;success_rate:number|null;successful_time_median:number|null}[];
    paired_time: {participant_group:string;task_id:string;pairs:number;eligible_pairs:number;unmatched_pairs:number;failed_or_zero_baseline_pairs:number;median_time_reduction_percent:number|null}[];
    questionnaire: {question:string;participant_group:string;n:number;missing:number;na:number;mean:number|null;median:number|null;min:number|null;max:number|null;sample_std_dev:number|null}[] };
};
export type WorkflowResult = {status:"AVAILABLE";data:MethodologyWorkflow} | {status:"UNAVAILABLE";data:null};
const repo = "https://github.com/nhuffan/irrigation-mvdt-platform/blob/main/";
/** Public originals only. Private receipts and source paths have no browser route. */
export function workflowEvidenceHref(path: string | null): string | null {
  if (!path || path.includes("..") || path.includes("\\") || path.includes("?") || path.includes("#")) return null;
  return /^(research\/dataset\/[\w.-]+\.template\.(csv|json)|research\/evaluation\/templates\/[\w.-]+\.(csv|json)|research\/evaluation\/(protocol|stage5b_protocol|retrieval_tasks|questionnaire|results_outline|methodology_closure_review|methodology_checkpoint_review)\.md|research\/evaluation\/functional_validation\.csv|(?:apps\/api\/)?scripts\/[\w-]+\.py)$/.test(path) ? repo + path : null;
}
const object = (x:unknown):x is Record<string,unknown> => x !== null && typeof x === "object" && !Array.isArray(x);
const num = (x:unknown) => x === null || typeof x === "number" && Number.isFinite(x);
const count = (x:unknown) => x === null || typeof x === "number" && Number.isSafeInteger(x) && x >= 0;
const str = (x:unknown) => typeof x === "string";
const textOrNull = (x:unknown) => x === null || str(x);
const evidence = (x:unknown):boolean => object(x) && str(x.label) && textOrNull(x.path) && (x.path === null || workflowEvidenceHref(String(x.path)) !== null) && textOrNull(x.sha256);
const evidenceList = (x:unknown) => Array.isArray(x) && x.every(evidence);
const blocker = (x:unknown) => object(x) && str(x.code) && str(x.message) && str(x.next_action) && evidenceList(x.evidence);
const aggregate = (x:unknown, strings:string[], counts:string[], statistics:string[]) => object(x) && strings.every(k=>str(x[k])) && counts.every(k=>count(x[k]) && x[k] !== null) && statistics.every(k=>num(x[k]));
const projectEvidence = (e:WorkflowEvidence) => ({label:e.label,path:e.path,sha256:e.sha256});
const stepIds = ["scope","data","functional","evaluation","results"];
const states = ["WORKFLOW_READY","DATA_REVIEW_PENDING","DATASET_NOT_FROZEN","FUNCTIONAL_ACCEPTANCE_PENDING","OBSERVATIONS_PENDING","ANALYSIS_READY","RESEARCH_COMPLETE"];
/** Reject malformed or cross-reservoir responses; unavailable never becomes zero. */
export function workflowFromResponse(value: unknown, reservoirId: string): WorkflowResult {
  if (!object(value) || value.schema_version !== "METHODOLOGY-WORKFLOW-v1" || !str(value.generated_at) || !Number.isFinite(Date.parse(value.generated_at as string)) ||
      !Array.isArray(value.reservoir_ids) || !value.reservoir_ids.includes(reservoirId) || value.reservoir_ids.some(id => id !== reservoirId) ||
      !textOrNull(value.dataset_version) || !str(value.compiler_status) || !states.includes(String(value.state)) || !["WORKFLOW_READY","UNAVAILABLE"].includes(String(value.software_status)) ||
      !["PENDING","COMPLETE"].includes(String(value.research_status)) || !["NOT_FROZEN","FROZEN","INVALID","VERSION_MISMATCH","STALE_SCOPE","HASH_MISMATCH"].includes(String(value.dataset_status)) ||
      !Array.isArray(value.approvals) || !Array.isArray(value.acceptance) || !Array.isArray(value.steps) || value.steps.length !== 5 || !object(value.fingerprints) || !Object.values(value.fingerprints).every(textOrNull)) return {status:"UNAVAILABLE",data:null};
  for (const [i,s] of value.steps.entries()) {
    if (!object(s) || s.id !== stepIds[i] || !str(s.label) || !["COMPLETE","PENDING","BLOCKED","STALE"].includes(String(s.status)) || !object(s.counts) || !Object.values(s.counts).every(x=>num(x) && (x === null || Number(x)>=0)) || !Array.isArray(s.blockers) || !s.blockers.every(blocker) || !evidenceList(s.evidence) || !str(s.next_action)) return {status:"UNAVAILABLE",data:null};
  }
  for (const row of value.acceptance) if (!object(row) || !["id","label","recorded_status","status"].every(k=>str(row[k])) || !["dataset_version","asset_id","checked_at"].every(k=>textOrNull(row[k])) || !Array.isArray(row.missing) || !row.missing.every(str) || !count(row.evidence_count) || row.evidence_count === null || !Array.isArray(row.evidence_sha256) || !row.evidence_sha256.every(str)) return {status:"UNAVAILABLE",data:null};
  for (const row of value.approvals) if (!object(row) || !str(row.type) || !str(row.scope) || !["APPROVED","PENDING"].includes(String(row.status))) return {status:"UNAVAILABLE",data:null};
  const m = value.metrics;
  if (!object(m) || !["NOT_COLLECTED","APPROVED_FROZEN"].includes(String(m.status)) || !textOrNull(m.dataset_version) || !textOrNull(m.snapshot_sha256) || !count(m.observation_count) || !Array.isArray(m.rows) || !Array.isArray(m.coverage) || !Array.isArray(m.retrieval) || !Array.isArray(m.paired_time) || !Array.isArray(m.questionnaire)) return {status:"UNAVAILABLE",data:null};
  for (const entry of m.coverage) if (!object(entry) || !str(entry.id) || !str(entry.status) || ![entry.numerator,entry.denominator,entry.value].every(num)) return {status:"UNAVAILABLE",data:null};
  for (const row of m.rows) if (!object(row) || !str(row.id) || !str(row.label) || !str(row.status) || !textOrNull(row.missing_reason) || !textOrNull(row.dataset_version) || !count(row.observation_count) || !count(row.numerator) || !count(row.denominator) || !num(row.value) || ["unit","authority","verification"].some(k=>row[k] !== undefined && !textOrNull(row[k]))) return {status:"UNAVAILABLE",data:null};
  for (const row of m.retrieval) if (!aggregate(row,["task_id","participant_group","workflow"],["attempts","successes"],["success_rate","successful_time_median"]) || !object(row) || Number(row.successes)>Number(row.attempts) || row.success_rate !== null && (Number(row.success_rate)<0 || Number(row.success_rate)>1) || row.successful_time_median !== null && Number(row.successful_time_median)<0) return {status:"UNAVAILABLE",data:null};
  for (const row of m.paired_time) if (!aggregate(row,["task_id","participant_group"],["pairs","eligible_pairs","unmatched_pairs","failed_or_zero_baseline_pairs"],["median_time_reduction_percent"])) return {status:"UNAVAILABLE",data:null};
  for (const row of m.questionnaire) if (!aggregate(row,["question","participant_group"],["n","missing","na"],["mean","median","min","max","sample_std_dev"]) || !object(row) || [row.mean,row.median,row.min,row.max].some(x=>x !== null && (Number(x)<1 || Number(x)>5)) || row.sample_std_dev !== null && Number(row.sample_std_dev)<0) return {status:"UNAVAILABLE",data:null};
  if ((value.state === "RESEARCH_COMPLETE") !== (value.research_status === "COMPLETE") || value.software_status === "UNAVAILABLE" && value.research_status === "COMPLETE") return {status:"UNAVAILABLE",data:null};
  if (m.status === "NOT_COLLECTED" && (m.retrieval.length || m.paired_time.length || m.questionnaire.length || m.coverage.some(row=>object(row) && row.value !== null) || m.rows.some(row=>object(row) && row.value !== null))) return {status:"UNAVAILABLE",data:null};
  // Public aggregates must not carry participant identity or private approval metadata.
  if (/\/Users\/|\/private\/|storage_key|reviewer_name|reviewer_receipt|participant_id|password|api_key|access_token/i.test(JSON.stringify(value))) return {status:"UNAVAILABLE",data:null};
  if (m.status === "APPROVED_FROZEN" && (value.dataset_status !== "FROZEN" || !value.dataset_version || m.dataset_version !== value.dataset_version || !m.snapshot_sha256)) return {status:"UNAVAILABLE",data:null};
  if (value.research_status === "COMPLETE" && (value.state !== "RESEARCH_COMPLETE" || m.status !== "APPROVED_FROZEN" || value.steps.some(s=> !object(s) || s.status !== "COMPLETE"))) return {status:"UNAVAILABLE",data:null};
  const v = value as MethodologyWorkflow;
  const select = <T extends object>(row:T, keys:readonly (keyof T)[]):T => Object.fromEntries(keys.map(k=>[k,row[k]])) as T;
  // Project the public contract rather than carrying unknown transport metadata.
  return {status:"AVAILABLE",data:{schema_version:v.schema_version,generated_at:v.generated_at,reservoir_ids:v.reservoir_ids,dataset_version:v.dataset_version,state:v.state,compiler_status:v.compiler_status,software_status:v.software_status,research_status:v.research_status,dataset_status:v.dataset_status,
    steps:v.steps.map(step=>({...select(step,["id","label","status","counts","next_action"]),evidence:step.evidence.map(projectEvidence),blockers:step.blockers.map(b=>({code:b.code,message:b.message,next_action:b.next_action,evidence:b.evidence.map(projectEvidence)}))})),acceptance:v.acceptance.map(row=>select(row,["id","label","recorded_status","status","dataset_version","asset_id","missing","evidence_count","evidence_sha256","checked_at"])),approvals:v.approvals.map(row=>select(row,["type","scope","status"])),fingerprints:v.fingerprints,
    metrics:{status:v.metrics.status,dataset_version:v.metrics.dataset_version,snapshot_sha256:v.metrics.snapshot_sha256,observation_count:v.metrics.observation_count,
      coverage:v.metrics.coverage.map(row=>select(row,["id","numerator","denominator","value","status"])),rows:v.metrics.rows.map(row=>select(row,["id","label","numerator","denominator","value","status","missing_reason","observation_count","dataset_version","unit","authority","verification"])),
      retrieval:v.metrics.retrieval.map(row=>select(row,["task_id","participant_group","workflow","attempts","successes","success_rate","successful_time_median"])),paired_time:v.metrics.paired_time.map(row=>select(row,["participant_group","task_id","pairs","eligible_pairs","unmatched_pairs","failed_or_zero_baseline_pairs","median_time_reduction_percent"])),questionnaire:v.metrics.questionnaire.map(row=>select(row,["question","participant_group","n","missing","na","mean","median","min","max","sample_std_dev"]))}}};
}
export function workflowExportAlignment(unavailable: boolean, differs: boolean) {
  return unavailable ? "LIVE_READBACK_UNAVAILABLE" : differs ? "HISTORICAL_EXPORT_DIFFERS" : "RECORD_READBACK_MATCH";
}
