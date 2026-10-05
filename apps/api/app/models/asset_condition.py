from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.om_common import RecordMixin


class AssetCondition(RecordMixin, Base):
    __tablename__ = "asset_conditions"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','PARTIALLY_VERIFIED','VERIFIED','REJECTED')",
            name="ck_asset_conditions_verification",
        ),
        Index(
            "ix_asset_conditions_asset_date",
            "asset_id",
            "condition_date",
            "created_at",
            "id",
        ),
    )
    condition_date: Mapped[date] = mapped_column(Date, nullable=False)
    condition_status: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    defect_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
