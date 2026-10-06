"""Inventory counts are implementation readiness, not case-study results."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.asset_category import AssetCategory  # noqa: F401
from app.models.data_source import DataSource
from app.models.media import Document, Model, ModelAssetLink
from app.models.reservoir import Reservoir
from app.services.om_service import RECORD_TYPES
from scripts.research_common import KINDS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        models = {
            "reservoirs": Reservoir,
            "assets": Asset,
            "sources": DataSource,
            "documents": Document,
            "models": Model,
            "model_asset_links": ModelAssetLink,
            **{k: RECORD_TYPES[k][0] for k in KINDS},
        }
        counts = {
            key: db.scalar(select(func.count()).select_from(model))
            for key, model in models.items()
        }
        research_candidates = db.scalar(
            select(func.count())
            .select_from(Asset)
            .where(Asset.asset_code.startswith("RS-"))
        )
        development_assets = db.scalar(
            select(func.count())
            .select_from(Asset)
            .where(Asset.asset_code.startswith("DEV-"))
        )
    output = {
        "audited_at": datetime.now(UTC).isoformat(),
        "purpose": "IMPLEMENTATION_READINESS_ONLY",
        "database_counts_including_development": counts,
        "research_prefix_asset_candidates": research_candidates,
        "development_prefix_assets": development_assets,
        "unclassified_prefix_assets": counts["assets"]
        - research_candidates
        - development_assets,
        "approved_dataset_status": "NOT_ASSESSED_BY_THIS_AUDIT",
        "declared_dataset_status": json.loads(
            (
                Path(__file__).resolve().parents[3] / "research/dataset/version.json"
            ).read_text()
        )["status"],
        "research_metrics": None,
        "required_evidence": [
            "Approved Phase 1 target inventory and MAIM",
            "Reviewed explicit research scope",
            "Browser/manual acceptance evidence",
            "Observed baseline and MVDT retrieval sessions",
            "Actual participant questionnaires",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
