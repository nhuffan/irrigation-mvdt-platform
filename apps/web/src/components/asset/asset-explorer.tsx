"use client";

import { useMemo, useState } from "react";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";
import { AssetMap } from "@/components/map/asset-map";
import { AssetRegistry } from "./asset-registry";

// Controlled code namespaces identify datasets, not verification or authority.
function dataset(asset: Asset) {
  if (asset.asset_code.startsWith("RS-")) return "research";
  if (asset.asset_code.startsWith("DEV-")) return "development";
  return "other";
}

export function AssetExplorer({ reservoir, assets }: { reservoir: Reservoir; assets: Asset[] }) {
  const [scope, setScope] = useState(() =>
    assets.some((asset) => dataset(asset) === "research") ? "research" :
    assets.some((asset) => dataset(asset) === "development") ? "development" : "other",
  );
  const visible = useMemo(() => assets.filter((asset) => dataset(asset) === scope), [assets, scope]);
  return (
    <>
      <label className="block mb-3">
        Dataset scope{" "}
        <select value={scope} onChange={(event) => setScope(event.target.value)}>
          <option value="research">Research registry (RS)</option>
          <option value="development">Development examples (DEV)</option>
          <option value="other">Other / unclassified</option>
        </select>
      </label>
      <p className="muted mb-3" role="status">
        {visible.length} registry assets · {visible.filter((asset) => asset.geometry !== null).length} with spatial geometry.
        {scope === "development" ? " Synthetic development data; not empirical research evidence." :
          scope === "research" ? " Registry identity does not imply reviewed geometry or source authority." :
          " Dataset classification has not been established."}
        {" "}Basemap and reservoir center provide navigation context only.
      </p>
      <div id="asset-gis"><AssetMap key={scope} reservoir={reservoir} assets={visible} /></div>
      <div className="mt-6"><AssetRegistry assets={visible} /></div>
    </>
  );
}
