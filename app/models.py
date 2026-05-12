from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    name2: Mapped[Optional[str]] = mapped_column(String(120))
    description: Mapped[Optional[str]] = mapped_column(Text)
    age: Mapped[Optional[int]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class ExternalRawRecord(Base):
    __tablename__ = "external_raw_records"
    __table_args__ = (
        UniqueConstraint("source_system", "external_id", name="uq_external_raw_source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_system: Mapped[str] = mapped_column(String(80), nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DwhExternalRecordFact(Base):
    __tablename__ = "dwh_external_record_facts"
    __table_args__ = (
        UniqueConstraint("source_system", "external_id", name="uq_dwh_external_fact_source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_system: Mapped[str] = mapped_column(String(80), nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[Optional[str]] = mapped_column(String(60))
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    occurred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
