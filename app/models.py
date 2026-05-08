from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
