from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.om_common import RecordMixin


class Inspection(RecordMixin, Base):
    __tablename__ = "inspections"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','PARTIALLY_VERIFIED','VERIFIED','REJECTED')",
            name="ck_inspections_verification",
        ),
        Index(
            "ix_inspections_asset_date",
            "asset_id",
            "inspection_date",
            "created_at",
            "id",
        ),
    )
    inspection_date: Mapped[date] = mapped_column(Date, nullable=False)
    inspection_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    inspector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
