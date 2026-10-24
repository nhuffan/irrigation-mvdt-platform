"use client";
import { PanelSection, PanelDisclosure } from "@/components/ui/panel-section";
import { AssetDisplayName, TechnicalMetadataPopover, StatusBadge } from "@/components/asset/presentation";
import { OriginLink as Link } from "@/components/documents/document-link";
import { useEffect, useState } from "react";
import { scopedSnapshot } from "@/lib/workspace-view-state";
import {
  getAsset,
  getAssetCurrentCondition,
  getAssetInspections,
  getAssetMaintenance,
} from "@/lib/api";
import { VerificationBadge } from "@/components/asset/source-info";
import type { ModelAssetLink } from "@/types/media";
export function AssetSidePanel({ link, placement }: { link: ModelAssetLink; placement: string }) {
  const [snapshot, setSnapshot] = useState<{ id: string; attempt: number; data: Awaited<ReturnType<typeof load>> } | null>(null);
  const [attempt, setAttempt] = useState(0);
  async function load(id: string) {
    return Promise.allSettled([
      getAsset(id),
      getAssetCurrentCondition(id),
      getAssetInspections(id),
      getAssetMaintenance(id),
    ]);
  }
  useEffect(() => {
    let active = true;
    queueMicrotask(() => {
      if (!active) return;
      void load(link.asset_id).then((value) => {
        if (active) setSnapshot({ id: link.asset_id, attempt, data: value });
      });
    });
    return () => {
      active = false;
    };
  }, [link.asset_id, attempt]);
  const data = scopedSnapshot(snapshot, link.asset_id);
  const pending = !data || snapshot?.attempt !== attempt;
  const unavailable = data?.some(item => item.status === "rejected") ?? false;
  const asset = data?.[0].status === "fulfilled" ? data[0].value : null;
  return (
    <PanelSection title="Linked asset" actions={<StatusBadge>{placement}</StatusBadge>}>
      <p className="mapping-notice">Representative link</p>
      {pending && <p role="status">{data ? "Refreshing asset summary…" : "Loading asset summary…"}</p>}
      {!data ? (
        <div className="skeleton-card" aria-hidden="true"/>
      ) : (
        <dl className="detail-list inspector-facts">
          <div>
            <dt>Asset</dt>
            <dd>
              {asset ? <><AssetDisplayName asset={asset}/><span className="asset-code">{asset.asset_code}</span></> : "Asset identity unavailable"}
            </dd>
          </div>
          <div>
            <dt>Category</dt>
            <dd>{asset?.category.name ?? "Unavailable"}</dd>
          </div>
          <div>
            <dt>Current verified condition</dt>
            <dd>
              {data[1].status === "rejected" ? "Condition unavailable" : data[1].value?.condition_status ?? "No verified condition record"}
            </dd>
          </div>
          <div>
            <dt>Latest inspection</dt>
            <dd>
              {data[2].status === "rejected" ? "Inspection data unavailable" : data[2].value[0] ? (
                <>
                  {data[2].value[0].inspection_date}{" "}
                  <VerificationBadge status={data[2].value[0].verification_status} />
                </>
              ) : (
                "No inspection records available"
              )}
            </dd>
          </div>
          <div>
            <dt>Latest maintenance</dt>
            <dd>
              {data[3].status === "rejected" ? "Maintenance data unavailable" : data[3].value[0] ? (
                <>
                  {data[3].value[0].maintenance_date}{" "}
                  <VerificationBadge status={data[3].value[0].verification_status} />
                </>
              ) : (
                "No maintenance records available"
              )}
            </dd>
          </div>
        </dl>
      )}
      {unavailable && <div role="alert"><p>Some asset sections are unavailable. Available records remain shown.</p><button className="text-link" disabled={pending} onClick={() => setAttempt(n => n + 1)}>Retry asset summary</button></div>}
      <PanelDisclosure title="Mapping details">
        <TechnicalMetadataPopover fields={{"Object key":link.object_key,"Object name":link.object_name,"Model UUID":link.model_id,"Asset UUID":link.asset_id,"Mapping status":link.verification_status}}/>
        <VerificationBadge status={link.verification_status}/>
        <p className="summary-note">This representative link does not prove a specific child building identity. Mapping verification is separate from asset condition.</p>
      </PanelDisclosure>
      <Link className="button compact-button" href={`/assets/${link.asset_id}`}>Open Asset Detail →</Link>
    </PanelSection>
  );
}
