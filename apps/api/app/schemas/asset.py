from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field

Position = tuple[float, float]


class PointGeometry(BaseModel):
    type: Literal["Point"]
    coordinates: Position


class LineGeometry(BaseModel):
    type: Literal["LineString"]
    coordinates: list[Position]


class PolygonGeometry(BaseModel):
    type: Literal["Polygon"]
    coordinates: list[list[Position]]


GeoJsonGeometry = Annotated[
    PointGeometry | LineGeometry | PolygonGeometry, Field(discriminator="type")
]


class SpatialCandidateSummary(BaseModel):
    candidate_id: str
    source_label: str
    source: str
    source_url: str | None = None
    source_id: UUID | None = None
    document_id: UUID | None = None
    physical_page: int
    locator: str
    coordinate_basis: str
    source_crs: str
    identity_basis: str
    accuracy_limitation: str
    estimated_accuracy_m: float | None = None
    issues: list[str] = []


class AssetLocation(BaseModel):
    location_status: Literal["VERIFIED_GEOMETRY", "REFERENCE_LOCATION", "NO_LOCATION"]
    geometry: GeoJsonGeometry | None = None
    geometry_type: Literal["Point", "LineString", "Polygon"] | None = None
    crs: str | None = None
    source: str | None = None
    source_url: str | None = None
    locator: str | None = None
    evidence_id: str | None = None
    accuracy_limitation: str
    verification_note: str
    reviewer: str | None = None
    reviewed_at: str | None = None
    review_state: Literal["AVAILABLE", "PENDING", "UNAVAILABLE"] = "PENDING"
    spatial_disposition: Literal[
        "VERIFIED_GEOMETRY",
        "REFERENCE_LOCATION",
        "CANDIDATE_NEEDS_REVIEW",
        "CONFLICTED",
        "NO_DEFENSIBLE_LOCATION",
    ] = "NO_DEFENSIBLE_LOCATION"
    candidate_count: int = 0
    reason: str | None = None
    next_action: str | None = None
    candidates: list[SpatialCandidateSummary] = []
    coordinate_basis: str | None = None
    estimated_accuracy_m: float | None = None
    physical_page: int | None = None
    document_id: UUID | None = None
    source_id: UUID | None = None
    source_sha256: str | None = None
    reviewer_role: str | None = None


class AssetCategoryResponse(BaseModel):
    id: UUID
    code: str
    name: str


class AssetResponse(BaseModel):
    id: UUID
    reservoir_id: UUID
    parent_asset_id: UUID | None
    asset_code: str
    name: str
    description: str | None
    technical_description: str | None
    condition_status: str | None
    data_status: Literal["REGISTERED", "PARTIAL", "VERIFIED"]
    category: AssetCategoryResponse
    geometry: GeoJsonGeometry | None
    location: AssetLocation | None = None
