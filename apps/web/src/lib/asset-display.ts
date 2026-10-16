import type { Asset } from "../types/asset";
const aliases: Record<string, string> = {
  "RS-DT-DAM": "Đập chính — Main Dam",
  "RS-DT-SPILLWAY": "Tràn xả lũ — Spillway",
  "RS-DT-INTAKE": "Công trình lấy nước — Intake Structure",
  "RS-DT-MGMT": "Khu nhà quản lý/vận hành — Management / Operations Complex",
};
// Presentation only: never change canonical names, identity, joins or review state.
export function assetDisplayName(asset: Pick<Asset, "asset_code" | "name">) {
  return aliases[asset.asset_code] ?? asset.name;
}
export function locationSourceTitle(source: string | null) {
  if (!source) return "Unavailable";
  return source.includes(" — ") ? source.split(" — ").slice(1).join(" — ") : source;
}
