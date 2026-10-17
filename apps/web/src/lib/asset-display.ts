import type { Asset } from "../types/asset";
const aliases: Record<string, string> = {
  "RS-DT-DAM": "Main Dam — Đập chính",
  "RS-DT-SPILLWAY": "Spillway — Tràn xả lũ",
  "RS-DT-INTAKE": "Intake Structure — Công trình lấy nước",
  "RS-DT-MGMT": "Management / Operations Complex — Khu nhà quản lý/vận hành",
  "RS-DT-INTAKE-C01": "Intake No. 1, East Canal — Cống số 1, Kênh Đông",
  "RS-DT-INTAKE-C02": "Intake No. 2, West Canal — Cống số 2, Kênh Tây",
  "RS-DT-INTAKE-C03": "Intake No. 3, Tan Hung Canal — Cống số 3, Kênh Tân Hưng",
  "RS-DT-MGMT-OFFICE": "Office Building — Nhà làm việc",
  "RS-DT-MGMT-SAIL": "Sail Building — Nhà cánh buồm",
  "RS-DT-MGMT-DINING": "Dining Building — Nhà ăn",
};
// Presentation only: never change canonical names, identity, joins or review state.
export function assetDisplayName(asset: Pick<Asset, "asset_code" | "name">) {
  return aliases[asset.asset_code] ?? asset.name;
}
export function locationSourceTitle(source: string | null) {
  if (!source) return "Unavailable";
  return source.includes(" — ") ? source.split(" — ").slice(1).join(" — ") : source;
}
