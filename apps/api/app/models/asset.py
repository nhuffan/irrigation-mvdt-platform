import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        UniqueConstraint("id", "reservoir_id", name="uq_assets_id_reservoir"),
        ForeignKeyConstraint(
            ["parent_asset_id", "reservoir_id"],
            ["assets.id", "assets.reservoir_id"],
            name="fk_assets_parent_same_reservoir",
            ondelete="SET NULL (parent_asset_id)",
        ),
        CheckConstraint(
            "parent_asset_id IS NULL OR parent_asset_id <> id",
            name="ck_assets_not_self_parent",
        ),
        CheckConstraint(
            "data_status IN ('REGISTERED', 'PARTIAL', 'VERIFIED')",
            name="ck_assets_data_status",
        ),
        CheckConstraint(
            "geometry IS NULL OR (GeometryType(geometry) IN ('POINT', 'LINESTRING', 'POLYGON') AND NOT ST_IsEmpty(geometry) AND ST_IsValid(geometry))",
            name="ck_assets_geometry_valid",
        ),
        CheckConstraint(
            "geometry IS NULL OR (ST_XMin(Box3D(geometry)) >= -180 AND ST_XMax(Box3D(geometry)) <= 180 AND ST_YMin(Box3D(geometry)) >= -90 AND ST_YMax(Box3D(geometry)) <= 90)",
            name="ck_assets_geometry_bounds",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    reservoir_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reservoirs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("asset_categories.id"),
        nullable=False,
        index=True,
    )

    parent_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    asset_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    technical_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    condition_status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    data_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="REGISTERED",
    )

    geometry = mapped_column(
        Geometry(
            geometry_type="GEOMETRY",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
