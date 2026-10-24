"use client";
import { MetricCard, PanelSection, PanelDisclosure } from "@/components/ui/panel-section";
import { Workspace } from "@/components/workspace";
import { useSearchParams } from "next/navigation";
import type { Asset } from "@/types/asset";
import type { Reservoir } from "@/types/reservoir";
import type { ExplorerRecords } from "@/lib/explorer-data";
import { AssetMap } from "@/components/map/asset-map";
import { AssetRegistry } from "./asset-registry";
import { selectedAsset, filterAssets, recordTotal, explorerFilters, explorerFilterUrl } from "@/lib/explorer-state";
import { assetLocation, matchesSearch } from "@/lib/asset-location";
import { ExplorerPanel } from "./explorer-panel";
export function AssetExplorer({ reservoir, assets, records }: { reservoir: Reservoir; assets: Asset[]; records: ExplorerRecords }) {
  const params = useSearchParams();
  const selected = selectedAsset(assets, params.get("asset"));
  const paper = params.get("paper") === "1";
  const scope = "research";
  const { query, type, location: locationFilter, contextVisible, modelOnly } = explorerFilters(params);
  function filter(key: "q" | "type" | "location" | "context" | "modelOnly", value: string) {
    window.history.replaceState(null, "", explorerFilterUrl(window.location.href, key, value));
  }
  const scoped = assets;
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
      <MetricCard label="Research assets" value={scoped.length}/>
      <MetricCard label="Locations" value={`${scoped.filter(a => assetLocation(a).location_status === "VERIFIED_GEOMETRY").length} / ${scoped.filter(a => assetLocation(a).location_status === "REFERENCE_LOCATION").length} / ${scoped.filter(a => assetLocation(a).location_status === "NO_LOCATION").length}`} note="Verified / reference / missing"/>
      <MetricCard label="Technical records" value={total("technical")}/>
      <MetricCard label="Verified O&M" value={total("events")}/>
      <MetricCard label="3D links" value={total("links")}/>
    </div>


    {params.get("asset") && !selected && <p role="alert">Selected asset is unavailable in this reservoir.</p>}
    {selected && !visible.includes(selected) && <p role="status">Selected asset is excluded by the layer filters. Its information remains open.</p>}
    <Workspace title="map" panel={<>
    <PanelSection title="Search & filters"><div className="explorer-filters">
    <label>Search assets <input type="search" placeholder="Name, ID or component" value={query} onChange={e => filter("q", e.target.value)} /></label>
    <label>Location <select value={locationFilter} onChange={e => filter("location", e.target.value)}><option value="all">All location states</option><option value="VERIFIED_GEOMETRY">Verified geometry</option><option value="REFERENCE_LOCATION">Reference location</option><option value="NO_LOCATION">Missing location</option></select></label>
    <label>Asset type <select value={type} onChange={e => filter("type", e.target.value)}><option value="">All types</option>{types.map(([code,name]) => <option key={code} value={code}>{name}</option>)}</select></label>
    <label><input type="checkbox" checked={contextVisible} onChange={e => filter("context", e.target.checked ? "1" : "0")} /> Reservoir context</label>
    <label><input type="checkbox" checked={modelOnly} onChange={e => filter("modelOnly", e.target.checked ? "1" : "0")} /> With 3D</label></div></PanelSection>
      <PanelDisclosure title={`Asset list · ${visible.length}`} open={!selected}><AssetRegistry assets={visible} records={records} selectedId={selected?.id} onSelect={select} /></PanelDisclosure>
      {selected ? <ExplorerPanel key={selected.id} asset={selected} assets={assets} data={records[selected.id]} onSelect={select} paper={paper} /> : <p className="muted">Select an asset to inspect its evidence. Assets without locations remain in this list.</p>}
    <PanelDisclosure title="Map evidence limits"><p className="summary-note">Reference locations are for navigation / presentation only, not verified GIS evidence. Basemap and reservoir center are navigation context only.</p></PanelDisclosure></>}>
      <div id="asset-gis"><AssetMap reservoir={reservoir} assets={visible} selectedId={selected?.id} onSelect={select} records={records} contextVisible={contextVisible} /></div>
    </Workspace>
  </div>;
}
