"use client";
import { Workspace } from "@/components/workspace";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";
import type { ExplorerRecords } from "@/lib/explorer-data";
import { AssetMap } from "@/components/map/asset-map";
import { AssetRegistry } from "./asset-registry";
import { dataset, selectedAsset, filterAssets, recordTotal } from "@/lib/explorer-state";
import { assetLocation, matchesSearch } from "@/lib/asset-location";
import { ExplorerPanel } from "./explorer-panel";
export function AssetExplorer({ reservoir, assets, records }: { reservoir: Reservoir; assets: Asset[]; records: ExplorerRecords }) {
  const params = useSearchParams();
  const selected = selectedAsset(assets, params.get("asset"));
  const paper = params.get("paper") === "1";
  const [scopeChoice, setScope] = useState<string | null>(null);
  const scope = selected ? dataset(selected) : scopeChoice ?? (assets.some(a => dataset(a) === "research") ? "research" : assets.some(a => dataset(a) === "development") ? "development" : "other");
  const [locationFilter, setLocationFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [contextVisible, setContextVisible] = useState(true);
  const [modelOnly, setModelOnly] = useState(false);
  const scoped = assets.filter(a => dataset(a) === scope);
  const visible = filterAssets(assets, scope, false, modelOnly, records).filter(a =>
    (locationFilter === "all" || assetLocation(a).location_status === locationFilter) && matchesSearch(a, query, type));
  const types = [...new Map(scoped.map(a => [a.category.code, a.category.name])).entries()];
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
      <span><strong>{scoped.filter(a => assetLocation(a).location_status === "VERIFIED_GEOMETRY").length} / {scoped.filter(a => assetLocation(a).location_status === "REFERENCE_LOCATION").length} / {scoped.filter(a => assetLocation(a).location_status === "NO_LOCATION").length}</strong> Verified / reference / missing locations</span>
      <span><strong>{total("technical")}</strong> Technical records</span><span><strong>{total("events")}</strong> Verified O&M</span><span><strong>{total("links")}</strong> 3D links</span>
    </div>

    <p className="muted mb-3">{scope === "development" ? "DEV · Synthetic development data; not research evidence." : "Reference locations are for navigation / presentation only, not verified GIS evidence."} Basemap and reservoir center are navigation context only.</p>
    {params.get("asset") && !selected && <p role="alert">Selected asset is unavailable in this reservoir.</p>}
    {selected && !visible.includes(selected) && <p role="status">Selected asset is excluded by the layer filters. Its information remains open.</p>}
    <Workspace title="map" panel={<>
    <details className="filter-drawer"><summary>Search & filters</summary><div className="explorer-filters"><label>Dataset scope <select value={scope} onChange={e => { setScope(e.target.value); setType(""); select(); }}><option value="research">Research registry (RS)</option><option value="development">Development data (DEV)</option><option value="other">Other / unclassified</option></select></label>
    <label>Search assets <input type="search" placeholder="Name, ID or component" value={query} onChange={e => setQuery(e.target.value)} /></label>
    <label>Location <select value={locationFilter} onChange={e => setLocationFilter(e.target.value)}><option value="all">All location states</option><option value="VERIFIED_GEOMETRY">Verified geometry</option><option value="REFERENCE_LOCATION">Reference location</option><option value="NO_LOCATION">Missing location</option></select></label>
    <label>Asset type <select value={type} onChange={e => setType(e.target.value)}><option value="">All types</option>{types.map(([code,name]) => <option key={code} value={code}>{name}</option>)}</select></label>
    <label><input type="checkbox" checked={contextVisible} onChange={e => setContextVisible(e.target.checked)} /> Reservoir context</label>
    <label><input type="checkbox" checked={modelOnly} onChange={e => setModelOnly(e.target.checked)} /> With 3D</label></div></details>
      <details open><summary>Asset registry · {visible.length}</summary><AssetRegistry assets={visible} records={records} selectedId={selected?.id} onSelect={select} /></details>
      {selected ? <ExplorerPanel key={selected.id} asset={selected} assets={assets} data={records[selected.id]} onSelect={select} paper={paper} /> : <p className="muted">Select an asset to inspect its evidence. Assets without locations remain in this list.</p>}
    </>}>
      <div id="asset-gis"><AssetMap reservoir={reservoir} assets={visible} selectedId={selected?.id} onSelect={select} records={records} contextVisible={contextVisible} /></div>
    </Workspace>
  </div>;
}
