from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.om_common import RecordMixin


class Repair(RecordMixin, Base):
    __tablename__ = "repairs"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','PARTIALLY_VERIFIED','VERIFIED','REJECTED')",
            name="ck_repairs_verification",
        ),
        Index("ix_repairs_asset_date", "asset_id", "repair_date", "created_at", "id"),
    )
    repair_date: Mapped[date] = mapped_column(Date, nullable=False)
    repair_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    problem_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    repair_description: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)
