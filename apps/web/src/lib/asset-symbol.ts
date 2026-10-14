export const assetSymbols = {
  DAM: { label: "Dam", path: "M3 20h18M5 20l3-15h8l3 15M9 9h6M8 14h8" },
  SPILLWAY: { label: "Spillway", path: "M3 4h18M5 4v12m7-12v12m7-12v12M3 20q3-4 6 0t6 0t6 0M5 8h14" },
  INTAKE: { label: "Intake", path: "M3 6h18M6 6v14m12-14v14M3 20h18M9 10h6v6H9z" },
  MGMT: { label: "Management", path: "M3 10l9-7 9 7M5 9v12h14V9M10 21v-7h4v7M8 11h1m6 0h1" },
};
export function assetSymbol(category: string) {
  const code = category.replace(/^RS-CAT-/, "");
  return code === "SPILLWAY" ? assetSymbols.SPILLWAY : code === "INTAKE_SLUICE" || code === "INTAKE" ? assetSymbols.INTAKE : code === "MANAGEMENT_BUILDING" || code === "MGMT" ? assetSymbols.MGMT : assetSymbols.DAM;
}
export function assetSymbolSvg(category: string) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" aria-hidden="true"><path d="${assetSymbol(category).path}" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}
