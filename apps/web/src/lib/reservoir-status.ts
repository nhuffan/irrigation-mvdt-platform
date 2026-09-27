export const RESERVOIR_DATA_STATUS = {
  REGISTERED: "REGISTERED",
  DATA_COLLECTION: "DATA_COLLECTION",
  ASSET_INVENTORY: "ASSET_INVENTORY",
  MVDT_AVAILABLE: "MVDT_AVAILABLE",
  CONNECTED: "CONNECTED",
} as const;

export const RESERVOIR_STATUS_LABEL: Record<string, string> = {
  REGISTERED: "Registered",
  DATA_COLLECTION: "Data Collection",
  ASSET_INVENTORY: "Asset Inventory",
  MVDT_AVAILABLE: "MVDT Available",
  CONNECTED: "Connected Twin",
};
const COLORS: Record<string, string> = {
  REGISTERED: "#64748b",
  DATA_COLLECTION: "#b45309",
  ASSET_INVENTORY: "#7c3aed",
  MVDT_AVAILABLE: "#047857",
  CONNECTED: "#0369a1",
};
export function statusLabel(status: string) {
  return RESERVOIR_STATUS_LABEL[status] ?? status;
}
export function statusColor(status: string) {
  return COLORS[status] ?? "#64748b";
}
export const MATURITY: Record<number, { title: string; description: string }> =
  {
    0: {
      title: "Registered",
      description:
        "Basic reservoir record. Detailed MVDT is not yet available.",
    },
    1: {
      title: "Data Collection",
      description: "Legacy information collection is in progress.",
    },
    2: {
      title: "Asset Inventory",
      description:
        "Major assets are identified. Detailed MVDT is not yet available.",
    },
    3: {
      title: "MVDT Available",
      description:
        "Readiness level for integrated asset, GIS and O&M information.",
    },
    4: {
      title: "Connected Twin",
      description: "Readiness level for realtime or SCADA integration.",
    },
  };
