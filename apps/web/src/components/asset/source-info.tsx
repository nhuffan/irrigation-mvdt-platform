import { publicEvidenceText } from "@/lib/asset-information";
import { evidenceDisplayText } from "@/lib/evidence-display";
import { OriginLink as Link } from "@/components/documents/document-link";
import type { DataSource, VerificationStatus } from "@/types/data-source";
export function VerificationBadge({ status }: { status: VerificationStatus }) {
  return (
    <span className={`verification-badge verification-${status.toLowerCase()}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}
export function SourceInfo({ source }: { source: DataSource | null }) {
  if (!source)
    return <p className="muted mt-3 text-sm">Source not available.</p>;
  return (
    <details className="source-info">
      <summary>Source details</summary>
      <dl className="source-grid"><div><dt>Source UUID</dt><dd>{source.id}</dd></div>
        <div>
          <dt>Source code</dt>
          <dd>{source.source_code}</dd>
        </div>
        <div>
          <dt>Title</dt>
          <dd>{evidenceDisplayText(publicEvidenceText(source.title))}</dd>
        </div>
        <div>
          <dt>Type</dt>
          <dd>{source.source_type}</dd>
        </div>
        <div>
          <dt>Source date</dt>
          <dd>{source.source_date ?? "Not available"}</dd>
        </div>
        <div>
          <dt>Authority</dt>
          <dd>{publicEvidenceText(source.authority_level?.trim() || "UNKNOWN")}</dd>
        </div>
        <div>
          <dt>Source verification</dt>
          <dd>
            <VerificationBadge status={source.verification_status} />
          </dd>
        </div>
        <div>
          <dt>File name</dt>
          <dd>{publicEvidenceText(source.file_name)}</dd>
        </div>
      </dl>
      <p className="summary-note">This is a source inventory entry, not proof of a retained PDF or an asset–document link. Open its documents to inspect available files.</p>
      <Link className="text-link" href={`/data-sources/${source.id}/documents`}>
        Open documents →
      </Link>
    </details>
  );
}
