from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    network: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(30, 18), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(30, 18), nullable=False)
    gross_usdt: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    fee_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 18), nullable=False)
    fee_usdt: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 18), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_withdrawals_user_time", "user_id", "created_at"),
    )
