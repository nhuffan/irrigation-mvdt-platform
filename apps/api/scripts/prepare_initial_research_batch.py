"""Prepare candidate categories/sources only; never approve assets or empirical scope."""

import argparse
import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from scripts.research_common import research_code, write_csv


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_batch(targets, sources, maim, reservoir_id, reviewer, id_map):
    UUID(reservoir_id)
    if not reviewer.strip():
        raise ValueError("Identify the structural import reviewer")
    codes = [r["target_asset_code"] for r in targets]
    source_codes = [r["source_code"] for r in sources]
    for values in (codes, source_codes):
        if (
            not values
            or len(set(values)) != len(values)
            or not all(map(research_code, values))
        ):
            raise ValueError("Inventories require unique RS codes")
    categories = sorted({r["category"] for r in targets})
    if not all(map(research_code, categories)):
        raise ValueError("Categories require RS codes")
    for row in targets:
        if row["verification_status"] != "UNVERIFIED":
            raise ValueError(
                "This initial-load tool accepts unverified candidates only"
            )
        for key in ("in_scope", "requires_3d"):
            if row[key] not in ("true", "false"):
                raise ValueError("Explicit boolean required")
    for row in maim:
        if row["category"] not in categories or row["required"] not in (
            "true",
            "false",
        ):
            raise ValueError("Invalid MAIM category/boolean")
    if {r["category"] for r in maim} != set(categories):
        raise ValueError("MAIM must cover candidate categories")
    records = {"asset_categories": [], "data_sources": []}
    for code in categories:
        records["asset_categories"].append(
            {
                "id": id_map[("asset_categories", code)],
                "code": code,
                "name": code.removeprefix("RS-CAT-").replace("_", " ").title(),
                "description": "Initial research category; taxonomy awaits domain validation.",
            }
        )
    for row in sources:
        if row["verification_status"] != "UNVERIFIED":
            raise ValueError("Initial source metadata must remain UNVERIFIED")
        if not row["source_type"] or not row["title"] or not row["evidence_reference"]:
            raise ValueError("Source type/title/reference required")
        if not set(filter(None, row["related_asset_codes"].split("|"))) <= set(codes):
            raise ValueError("Source references unknown candidate asset")
        for key in ("file_expected", "file_available"):
            if row[key] not in ("true", "false"):
                raise ValueError("Explicit file boolean required")
        raw_date = row["source_date"].strip()
        normalized = (
            date.fromisoformat(raw_date).isoformat()
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_date)
            else None
        )
        records["data_sources"].append(
            {
                "id": id_map[("data_sources", row["source_code"])],
                "reservoir_id": reservoir_id,
                "source_code": row["source_code"],
                "source_type": row["source_type"],
                "title": row["title"],
                "file_name": None,
                "source_date": normalized,
                "source_owner": row["source_owner"].strip() or None,
                "authority_level": row["authority_level"].strip() or None,
                "verification_status": row["verification_status"],
                "notes": json.dumps(
                    {
                        "inventory_notes": row["notes"],
                        "original_source_date": raw_date or None,
                        "evidence_reference": row["evidence_reference"],
                        "review_scope": "Structural import review only; original files and domain evidence not reviewed.",
                        "availability_caveat": "Inventory file_available is a supplied claim, not a local file check.",
                    },
                    ensure_ascii=False,
                ),
            }
        )
    return {
        "import_batch": "B01A",
        "data_origin": "RESEARCH",
        "reviewed_by": reviewer,
        "source_reference": "User-supplied draft inventories; structural conversion only, domain approval pending.",
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser()
    for key in ("targets", "sources", "maim", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--reservoir-id", required=True)
    parser.add_argument("--reviewed-by", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Output already exists; preserve UUIDs/batch and reuse it")
    targets, sources, maim = (
        read_csv(p) for p in (args.targets, args.sources, args.maim)
    )
    labels = [("asset_categories", c) for c in sorted({r["category"] for r in targets})]
    labels += [("data_sources", r["source_code"]) for r in sources]
    labels += [("assets", r["target_asset_code"]) for r in targets]
    ids = {key: str(uuid4()) for key in labels}
    batch = build_batch(
        targets, sources, maim, args.reservoir_id, args.reviewed_by, ids
    )
    batch["input_sha256"] = {
        key: hashlib.sha256(path.read_bytes()).hexdigest()
        for key, path in [
            ("targets", args.targets),
            ("sources", args.sources),
            ("maim", args.maim),
        ]
    }
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "B01A.json").write_text(
        json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
    )
    write_csv(
        args.output / "id_map.csv",
        [{"record_type": k, "code": c, "uuid": v} for (k, c), v in ids.items()],
        ["record_type", "code", "uuid"],
    )
    print(
        "Prepared candidate categories/sources. Reserved asset IDs only; no assets or O&M in batch."
    )


if __name__ == "__main__":
    main()
