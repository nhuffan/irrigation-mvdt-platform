"""Stored representations remain subordinate to source and asset identity."""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.data_source import DataSource


class Timestamps:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Document(Timestamps, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "source_id", "checksum_sha256", name="uq_documents_source_checksum"
        ),
        CheckConstraint(
            "file_size >= 0 AND (page_count IS NULL OR page_count > 0)",
            name="ck_documents_size",
        ),
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), index=True
    )
    document_code: Mapped[str] = mapped_column(String(100), unique=True)
    original_file_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512))
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    page_count: Mapped[int | None]
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    source: Mapped[DataSource] = relationship()


class Model(Timestamps, Base):
    __tablename__ = "models"
    __table_args__ = (
        UniqueConstraint("id", "reservoir_id", name="uq_models_id_reservoir"),
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','PARTIALLY_VERIFIED','VERIFIED','REJECTED')",
            name="ck_models_verification",
        ),
        CheckConstraint(
            "coordinate_mode IN ('LOCAL','MANUAL_PLACEMENT','GEOREFERENCED')",
            name="ck_models_coordinate_mode",
        ),
        CheckConstraint(
            "longitude BETWEEN -180 AND 180 AND latitude BETWEEN -90 AND 90",
            name="ck_models_coordinates",
        ),
        CheckConstraint(
            "scale > 0 AND scale < 'Infinity'::float8", name="ck_models_scale"
        ),
        CheckConstraint(
            "coordinate_mode = 'LOCAL' OR (longitude IS NOT NULL AND latitude IS NOT NULL AND height IS NOT NULL)",
            name="ck_models_placement",
        ),
        CheckConstraint(
            "height IS NULL OR (height > '-Infinity'::float8 AND height < 'Infinity'::float8)",
            name="ck_models_height",
        ),
        CheckConstraint(
            "heading BETWEEN -360 AND 360 AND pitch BETWEEN -360 AND 360 AND roll BETWEEN -360 AND 360",
            name="ck_models_rotation",
        ),
    )
    reservoir_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservoirs.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), index=True
    )
    model_code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    model_type: Mapped[str] = mapped_column(String(50))
    format: Mapped[str] = mapped_column(String(30))
    storage_key: Mapped[str] = mapped_column(String(512))
    coordinate_mode: Mapped[str] = mapped_column(String(30))
    longitude: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    height: Mapped[float | None] = mapped_column(Float)
    heading: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    pitch: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    roll: Mapped[float] = mapped_column(Float, default=0, server_default="0")
    scale: Mapped[float] = mapped_column(Float, default=1, server_default="1")
    verification_status: Mapped[str] = mapped_column(
        String(30), default="UNVERIFIED", server_default="UNVERIFIED"
    )
    source: Mapped[DataSource | None] = relationship()


class ModelAssetLink(Timestamps, Base):
    __tablename__ = "model_asset_links"
    __table_args__ = (
        UniqueConstraint("model_id", "object_key", name="uq_model_object_key"),
        ForeignKeyConstraint(
            ["model_id", "reservoir_id"],
            ["models.id", "models.reservoir_id"],
            ondelete="CASCADE",
            name="fk_link_model_reservoir",
        ),
        ForeignKeyConstraint(
            ["asset_id", "reservoir_id"],
            ["assets.id", "assets.reservoir_id"],
            ondelete="CASCADE",
            name="fk_link_asset_reservoir",
        ),
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','PARTIALLY_VERIFIED','VERIFIED','REJECTED')",
            name="ck_model_links_verification",
        ),
        CheckConstraint("length(trim(object_key)) > 0", name="ck_model_links_key"),
    )
    model_id: Mapped[uuid.UUID] = mapped_column(index=True)
    asset_id: Mapped[uuid.UUID] = mapped_column(index=True)
    reservoir_id: Mapped[uuid.UUID]
    object_key: Mapped[str] = mapped_column(String(255))
    object_name: Mapped[str | None] = mapped_column(String(255))
    verification_status: Mapped[str] = mapped_column(
        String(30), default="UNVERIFIED", server_default="UNVERIFIED"
    )
