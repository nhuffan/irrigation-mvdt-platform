from datetime import date

from sqlalchemy import CheckConstraint, Date, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.om_common import RecordMixin


class MaintenanceRecord(RecordMixin, Base):
    __tablename__ = "maintenance_records"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','PARTIALLY_VERIFIED','VERIFIED','REJECTED')",
            name="ck_maintenance_records_verification",
        ),
        Index(
            "ix_maintenance_records_asset_date",
            "asset_id",
            "maintenance_date",
            "created_at",
            "id",
        ),
    )
    maintenance_date: Mapped[date] = mapped_column(Date, nullable=False)
    maintenance_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsible_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)
