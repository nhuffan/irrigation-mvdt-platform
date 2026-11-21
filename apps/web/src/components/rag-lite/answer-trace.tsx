import { TRACE_STEP_LABELS, type AnswerTrace } from "@/lib/rag-lite";
import styles from "./rag-lite.module.css";

const ICONS = { passed: "✓", failed: "✕", skipped: "–" } as const;

/** Shows how a grounded answer was produced or why it was withheld. */
export function AnswerTraceView({ trace }: { trace: AnswerTrace }) {
  const failed = trace.checks.find(check => check.status === "failed");
  const evidence = trace.attribute_evidence + trace.passage_evidence;
  const meta = [
    `${evidence} evidence item${evidence === 1 ? "" : "s"} (${trace.attribute_evidence} field${trace.attribute_evidence === 1 ? "" : "s"}, ${trace.passage_evidence} PDF passage${trace.passage_evidence === 1 ? "" : "s"})`,
    trace.model ? `Model ${trace.model}${trace.provider ? ` · ${trace.provider}` : ""}` : "No model called",
    trace.aliases.length ? `Sent as ${trace.aliases.join(", ")}` : null,
    trace.latency_ms !== null ? `${trace.latency_ms} ms` : null,
  ].filter(Boolean);
  return <details className={`panel ${styles.trace}`} open>
    <summary>How this answer was produced</summary>
    <p className={styles.traceOutcome}>{!failed ? "Every check passed." : failed.name === "retrieval" ? "Stopped before the model: no admissible evidence, so no answer is generated." : `Stopped at: ${TRACE_STEP_LABELS[failed.name]}. Retrieved evidence is shown instead of an answer.`}</p>
    <p className={styles.traceMeta}>{meta.join(" · ")}</p>
    <ol className={styles.traceSteps}>
      {trace.checks.map(check => <li key={check.name} data-status={check.status}>
        <span className={styles.traceIcon} aria-hidden="true">{ICONS[check.status]}</span>
        <div><strong>{TRACE_STEP_LABELS[check.name]}</strong><span>{check.detail}</span></div>
        <span className={styles.srOnly}>{check.status}</span>
      </li>)}
    </ol>
    <p className={styles.traceNote}>The model sees short evidence aliases, never record IDs or links. The server maps aliases back and validates the answer. This trace lists checks and counts only; prompts, evidence text and raw model output are not exposed.</p>
  </details>;
}
