"""Read-only, identity-bound location overlay; never writes research geometry."""

import json
import math
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationError,
    field_validator,
)

from app.core.config import settings
from app.schemas.asset import AssetLocation, AssetResponse, GeoJsonGeometry
from app.services.spatial_candidates import candidate_metadata, public_source_url


class LocationReview(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    asset_id: UUID
    reservoir_id: UUID
    asset_code: str
    location_status: Literal["VERIFIED_GEOMETRY", "REFERENCE_LOCATION"]
    geometry: GeoJsonGeometry
    crs: Literal["EPSG:4326"]
    source: str = Field(min_length=1)
    source_url: HttpUrl | None = None
    locator: str = Field(min_length=1)
    evidence_id: str | None = None
    accuracy_limitation: str = Field(min_length=1)
    verification_note: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    reviewed_at: datetime
    coordinate_basis: str | None = None
    estimated_accuracy_m: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    physical_page: int | None = Field(default=None, ge=1)
    document_id: UUID | None = None
    source_id: UUID | None = None
    source_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    reviewer_role: str | None = None

    @field_validator("geometry")
    @classmethod
    def valid_coordinates(cls, geometry):
        if geometry.type == "Point":
            positions = [geometry.coordinates]
        elif geometry.type == "LineString":
            positions = geometry.coordinates
        else:
            positions = [p for ring in geometry.coordinates for p in ring]
        if not positions or any(
            not math.isfinite(lon)
            or not math.isfinite(lat)
            or not -180 <= lon <= 180
            or not -90 <= lat <= 90
            for lon, lat in positions
        ):
            raise ValueError("Coordinates must be finite EPSG:4326 longitude/latitude")
        return geometry


def asset_location(asset: AssetResponse) -> AssetLocation:
    # DB geometry presence and asset identity status are not spatial verification.
    result = AssetLocation(
        location_status="REFERENCE_LOCATION" if asset.geometry else "NO_LOCATION",
        geometry=asset.geometry,
        geometry_type=asset.geometry.type if asset.geometry else None,
        crs="EPSG:4326" if asset.geometry else None,
        source="Asset registry geometry (unreviewed)" if asset.geometry else None,
        accuracy_limitation=(
            "Navigation / presentation only. Not verified GIS evidence."
            if asset.geometry
            else "Pending evidence: no asset-specific location supplied."
        ),
        verification_note="No reviewed spatial verification available; F02 unchanged.",
    )
    path = (
        settings.asset_locations_path or settings.storage_root / "asset_locations.json"
    )
    try:
        bundle = json.loads(path.read_text())
        if bundle.get("version") != 1 or not isinstance(bundle.get("records"), dict):
            raise ValueError("Unsupported location sidecar")
    except FileNotFoundError:
        result.spatial_disposition = (
            result.location_status if result.geometry else "NO_DEFENSIBLE_LOCATION"
        )
        return result
    except (OSError, ValueError, TypeError, AttributeError):
        result.review_state = "UNAVAILABLE"
        result.verification_note = "Location review unavailable or invalid; no sidecar coordinates applied. F02 unchanged."
        return result
    try:
        metadata = candidate_metadata(bundle, asset)
        result = AssetLocation.model_validate(result.model_dump() | metadata)
    except (ValueError, TypeError, AttributeError, ValidationError):
        result.review_state = "UNAVAILABLE"
        result.reason = "Candidate review metadata is unavailable or invalid."
        result.next_action = "Repair identity-bound candidate metadata; unapproved coordinates remain hidden."
    try:
        entry = bundle["records"].get(str(asset.id))
        if entry is None:
            if result.geometry:
                result.spatial_disposition = result.location_status
            return result
        review = LocationReview.model_validate(entry)
        if (review.asset_id, review.reservoir_id, review.asset_code) != (
            asset.id,
            asset.reservoir_id,
            asset.asset_code,
        ):
            raise ValueError("Location review identity does not match current asset")
        if review.location_status == "VERIFIED_GEOMETRY":
            if (
                not asset.asset_code.startswith("RS-")
                or review.geometry != asset.geometry
            ):
                raise ValueError(
                    "Verified review must bind exact existing RS DB geometry"
                )
        elif review.geometry.type != "Point":
            raise ValueError(
                "Reference overlays must be points, not invented boundaries"
            )
        public_review = review.model_dump(
            mode="json", exclude={"asset_id", "reservoir_id", "asset_code"}
        )
        public_review["source_url"] = public_source_url(review.source_url)
        comparisons = result.candidates
        if review.evidence_id and review.source_sha256:
            # An accepted reference already exposes its own bound provenance.
            # Suppress only that exact evidence revision from pending/comparison
            # cards; differing originals/bindings remain visible for review.
            binding = review.model_dump(mode="json")
            raw_candidates = bundle.get("candidates", [])
            if not isinstance(raw_candidates, list):
                raw_candidates = []
            if any(
                isinstance(value, dict)
                and value.get("candidate_id") == review.evidence_id
                and all(
                    value.get(key) == binding[key]
                    for key in (
                        "asset_id",
                        "reservoir_id",
                        "asset_code",
                        "source_sha256",
                        "source_id",
                        "document_id",
                        "physical_page",
                    )
                )
                for value in raw_candidates
            ):
                comparisons = [
                    value
                    for value in comparisons
                    if value.candidate_id != review.evidence_id
                ]
        return AssetLocation(
            **public_review,
            geometry_type=review.geometry.type,
            review_state="AVAILABLE",
            spatial_disposition=review.location_status,
            candidate_count=len(comparisons),
            reason=result.reason if comparisons else None,
            next_action=result.next_action if comparisons else None,
            candidates=comparisons,
        )
    except (OSError, ValueError, TypeError, AttributeError, ValidationError):
        result.review_state = "UNAVAILABLE"
        result.verification_note = (
            "Location review unavailable or invalid; no sidecar coordinates applied. "
            "F02 unchanged."
        )
        return result
