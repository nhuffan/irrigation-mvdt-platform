"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";
import type { ExplorerRecords } from "@/lib/explorer-data";
import { AssetMap } from "@/components/map/asset-map";
import { AssetRegistry } from "./asset-registry";
import { dataset, selectedAsset, filterAssets, recordTotal } from "@/lib/explorer-state";
import { ExplorerPanel } from "./explorer-panel";
export function AssetExplorer({ reservoir, assets, records }: { reservoir: Reservoir; assets: Asset[]; records: ExplorerRecords }) {
  const params = useSearchParams();
  const selected = selectedAsset(assets, params.get("asset"));
  const paper = params.get("paper") === "1";
  const [scopeChoice, setScope] = useState<string | null>(null);
  const scope = selected ? dataset(selected) : scopeChoice ?? (assets.some(a => dataset(a) === "research") ? "research" : assets.some(a => dataset(a) === "development") ? "development" : "other");
  const [geometryOnly, setGeometryOnly] = useState(false);
  const [modelOnly, setModelOnly] = useState(false);
  const scoped = assets.filter(a => dataset(a) === scope);
  const visible = filterAssets(assets, scope, geometryOnly, modelOnly, records);
  function select(asset?: Asset) {
    const url = new URL(window.location.href);
    if (asset) url.searchParams.set("asset", asset.id); else url.searchParams.delete("asset");
    window.history.pushState(null, "", url);
  }
  function total(key: "technical" | "events" | "links") {
    return recordTotal(scoped, records, key) ?? "Unavailable";
  }
  return <div className={paper ? "asset-explorer paper-mode" : "asset-explorer"}>
    <div className="explorer-summary" aria-label="Dataset summary">
      <span><strong>{scoped.length}</strong> {scope === "research" ? "Research assets" : scope === "development" ? "DEV assets" : "Unclassified assets"}</span>
      <span><strong>{scoped.filter(a => a.geometry).length} / {scoped.filter(a => !a.geometry).length}</strong> Geometry available / missing</span>
      <span><strong>{total("technical")}</strong> Technical records</span><span><strong>{total("events")}</strong> Verified O&M</span><span><strong>{total("links")}</strong> 3D links</span>
    </div>
    <div className="explorer-filters"><label>Dataset scope <select value={scope} onChange={e => { setScope(e.target.value); select(); }}><option value="research">Research registry (RS)</option><option value="development">Development examples (DEV)</option><option value="other">Other / unclassified</option></select></label>
    <label><input type="checkbox" checked={geometryOnly} onChange={e => setGeometryOnly(e.target.checked)} /> With geometry</label>
    <label><input type="checkbox" checked={modelOnly} onChange={e => setModelOnly(e.target.checked)} /> With 3D</label></div>
    <p className="muted mb-3">{scope === "development" ? "DEV · Synthetic development data; not research evidence." : "Registry identity does not imply reviewed geometry or source authority."} Basemap and reservoir center are navigation context only.</p>
    {params.get("asset") && !selected && <p role="alert">Selected asset is unavailable in this reservoir.</p>}
    {selected && !visible.includes(selected) && <p role="status">Selected asset is excluded by the layer filters. Its information remains open.</p>}
    <div className="explorer-layout"><div className="explorer-main">
      <AssetRegistry assets={visible} records={records} selectedId={selected?.id} onSelect={select} />
      <div id="asset-gis" className="mt-4"><AssetMap reservoir={reservoir} assets={visible} selectedId={selected?.id} onSelect={select} records={records} /></div>
    </div>{selected ? <ExplorerPanel asset={selected} data={records[selected.id]} /> : <aside className="panel explorer-panel"><h2>Explore an asset</h2><p className="muted">Select a registry row or real map geometry to inspect its evidence and digital links.</p></aside>}</div>
  </div>;
}
