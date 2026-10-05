import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DataSource(Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('UNVERIFIED','PARTIALLY_VERIFIED','VERIFIED','REJECTED')",
            name="ck_data_sources_verification",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    reservoir_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reservoirs.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    source_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    source_date: Mapped[date | None] = mapped_column(Date)
    source_owner: Mapped[str | None] = mapped_column(String(255))
    authority_level: Mapped[str | None] = mapped_column(String(50))
    verification_status: Mapped[str] = mapped_column(
        String(30), default="UNVERIFIED", server_default="UNVERIFIED", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
