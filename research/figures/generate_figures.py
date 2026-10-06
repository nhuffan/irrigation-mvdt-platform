"""Reproducible vector diagrams; no research observations are represented."""

from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).parent


def diagram(filename, title, rows):
    width = 1000
    height = 130 + len(rows) * 150
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#476273"/></marker></defs>',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="500" y="45" text-anchor="middle" font-family="Arial,sans-serif" font-size="26" font-weight="bold" fill="#153d50">{escape(title)}</text>',
    ]
    for i, row in enumerate(rows):
        y = 90 + i * 150
        box_width = min(850, 880 / len(row) - 20)
        if i:
            previous = rows[i - 1]
            prev_centers = [
                60 + (j + 0.5) * 880 / len(previous) for j in range(len(previous))
            ]
            centers = [60 + (j + 0.5) * 880 / len(row) for j in range(len(row))]
            bus_y = y - 33
            for center in prev_centers:
                parts.append(
                    f'<path d="M{center} {y - 65} V{bus_y}" stroke="#476273" fill="none" stroke-width="2"/>'
                )
            parts.append(
                f'<path d="M{min(prev_centers + centers)} {bus_y} H{max(prev_centers + centers)}" stroke="#476273" stroke-width="2"/>'
            )
            for center in centers:
                parts.append(
                    f'<path d="M{center} {bus_y} V{y - 5}" stroke="#476273" fill="none" stroke-width="2" marker-end="url(#arrow)"/>'
                )
        for j, label in enumerate(row):
            x = 60 + j * (880 / len(row)) + (880 / len(row) - box_width) / 2
            parts.append(
                f'<rect x="{x}" y="{y}" width="{box_width}" height="85" rx="12" fill="#edf5f6" stroke="#377486"/>'
            )
            lines = label.split("|")
            for k, line in enumerate(lines):
                parts.append(
                    f'<text x="{x + box_width / 2}" y="{y + 35 + k * 23}" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" fill="#173f50">{escape(line)}</text>'
                )
    parts.append("</svg>")
    (ROOT / filename).write_text("\n".join(parts))


diagram(
    "workflow.svg",
    "Research workflow — evaluation pending",
    [
        ["Legacy source inventory + audit"],
        ["Verified Asset IDs + approved scope"],
        ["GIS", "Technical + O&M", "Sources + documents"],
        ["Asset-centric MVDT + optional 3D"],
        ["Frozen dataset + retained evidence"],
        ["Coverage metrics", "Paired retrieval study", "User/expert feedback"],
    ],
)
diagram(
    "architecture.svg",
    "Implemented prototype architecture",
    [
        ["Next.js web platform"],
        ["MapLibre GIS", "Asset + O&M UI", "Cesium 3D"],
        ["FastAPI | Asset ID is the domain key"],
        [
            "PostgreSQL/PostGIS|Assets, histories, provenance",
            "Local storage adapter|Documents + GLB files",
        ],
        [
            "Read-only snapshot + offline evaluation|Research scope and observations supplied separately"
        ],
    ],
)
diagram(
    "asset-information-model.svg",
    "Asset-centric information model",
    [
        ["Reservoir"],
        ["Asset UUID + category + hierarchy"],
        ["Geometry + technical", "Condition + O&M", "Model-object links"],
        ["Data source provenance | Record and mapping verification"],
        ["Stored document evidence | Checksums + file access"],
    ],
)
