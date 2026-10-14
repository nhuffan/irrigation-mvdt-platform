import type { Asset } from "@/types/asset";
import type { ExplorerData } from "@/lib/explorer-data";
import { coverageRows } from "@/lib/asset-coverage";
import { assetLocation } from "@/lib/asset-location";
export function AssetInformationCoverage({asset,data,compact=false}:{asset:Asset;data:ExplorerData;compact?:boolean}) {
 return <section className={compact ? "coverage-summary compact" : "panel coverage-summary"} aria-label="Asset Information Coverage">
 <h3>Độ bao phủ thông tin — Information Coverage</h3>
 <dl>{coverageRows(asset,assetLocation(asset),data).map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
 <p className="summary-note">Availability by category, not a completeness score. Linked files are not the paper source-coverage denominator.</p></section>;
}
