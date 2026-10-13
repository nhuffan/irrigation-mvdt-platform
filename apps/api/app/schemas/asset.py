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
