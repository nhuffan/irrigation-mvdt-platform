"use client";
import { PanelSection, PanelDisclosure } from "@/components/ui/panel-section";
import { AssetDisplayName, TechnicalMetadataPopover, StatusBadge } from "@/components/asset/presentation";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  getAsset,
  getAssetCurrentCondition,
  getAssetInspections,
  getAssetMaintenance,
} from "@/lib/api";
import { VerificationBadge } from "@/components/asset/source-info";
import type { ModelAssetLink } from "@/types/media";
export function AssetSidePanel({ link, placement }: { link: ModelAssetLink; placement: string }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof load>> | null>(
    null,
  );
  const [error, setError] = useState(false);
  async function load(id: string) {
    return Promise.all([
      getAsset(id),
      getAssetCurrentCondition(id),
      getAssetInspections(id),
      getAssetMaintenance(id),
    ]);
  }
  useEffect(() => {
    let active = true;
    void load(link.asset_id)
      .then((value) => {
        if (active) setData(value);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
    };
  }, [link.asset_id]);
  return (
    <PanelSection title="Linked asset" actions={<StatusBadge>{placement}</StatusBadge>}>
      <p className="mapping-notice">Representative link</p>
      {error ? (
        <p role="alert">Unable to load asset summary.</p>
      ) : !data ? (
        <p role="status">Loading asset summary…</p>
      ) : (
        <dl className="detail-list inspector-facts">
          <div>
            <dt>Asset</dt>
            <dd>
              <AssetDisplayName asset={data[0]}/><span className="asset-code">{data[0].asset_code}</span>
            </dd>
          </div>
          <div>
            <dt>Category</dt>
            <dd>{data[0].category.name}</dd>
          </div>
          <div>
            <dt>Current verified condition</dt>
            <dd>
              {data[1]?.condition_status ?? "No verified condition record"}
            </dd>
          </div>
          <div>
            <dt>Latest inspection</dt>
            <dd>
              {data[2][0] ? (
                <>
                  {data[2][0].inspection_date}{" "}
                  <VerificationBadge status={data[2][0].verification_status} />
                </>
              ) : (
                "No inspection records available"
              )}
            </dd>
          </div>
          <div>
            <dt>Latest maintenance</dt>
            <dd>
              {data[3][0] ? (
                <>
                  {data[3][0].maintenance_date}{" "}
                  <VerificationBadge status={data[3][0].verification_status} />
                </>
              ) : (
                "No maintenance records available"
              )}
            </dd>
          </div>
        </dl>
      )}
      <PanelDisclosure title="Mapping details">
        <TechnicalMetadataPopover fields={{"Object key":link.object_key,"Object name":link.object_name,"Model UUID":link.model_id,"Asset UUID":link.asset_id,"Mapping status":link.verification_status}}/>
        <VerificationBadge status={link.verification_status}/>
        <p className="summary-note">This representative link does not prove a specific child building identity. Mapping verification is separate from asset condition.</p>
      </PanelDisclosure>
      <Link className="button compact-button" href={`/assets/${link.asset_id}`}>Open Asset Detail →</Link>
    </PanelSection>
  );
}
