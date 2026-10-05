from sqlalchemy import CheckConstraint, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.om_common import RecordMixin


class AssetTechnicalAttribute(RecordMixin, Base):
    __tablename__ = "asset_technical_attributes"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','PARTIALLY_VERIFIED','VERIFIED','REJECTED')",
            name="ck_asset_technical_attributes_verification",
        ),
        Index("ix_asset_technical_attributes_asset_key", "asset_id", "attribute_key"),
        CheckConstraint(
            "num_nonnulls(value_text, value_number) <= 1", name="ck_technical_one_value"
        ),
        CheckConstraint(
            "value_number IS NULL OR (value_number > '-Infinity'::float8 AND value_number < 'Infinity'::float8)",
            name="ck_technical_finite_number",
        ),
    )
    attribute_key: Mapped[str] = mapped_column(String(100), nullable=False)
    attribute_label: Mapped[str] = mapped_column(String(255), nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
