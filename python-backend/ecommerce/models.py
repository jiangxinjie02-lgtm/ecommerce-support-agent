from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(32), index=True)
    customer_name: Mapped[str] = mapped_column(String(64))
    product_name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    payment_status: Mapped[str] = mapped_column(String(32))
    order_status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    tracking_number: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    refundable: Mapped[bool] = mapped_column(Boolean, default=True)

    logistics: Mapped["Logistics | None"] = relationship(
        back_populates="order", uselist=False, cascade="all, delete-orphan"
    )
    refund_requests: Mapped[list["RefundRequest"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class Logistics(Base):
    __tablename__ = "logistics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.order_id"), unique=True, index=True
    )
    tracking_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    carrier: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    estimated_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    latest_event: Mapped[str] = mapped_column(String(255))

    order: Mapped[Order] = relationship(back_populates="logistics")
    events: Mapped[list["LogisticsEvent"]] = relationship(
        back_populates="logistics",
        cascade="all, delete-orphan",
        order_by="LogisticsEvent.event_time.desc()",
    )


class LogisticsEvent(Base):
    __tablename__ = "logistics_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    logistics_id: Mapped[int] = mapped_column(ForeignKey("logistics.id"), index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(String(255))

    logistics: Mapped[Logistics] = relationship(back_populates="events")


class RefundConfirmation(Base):
    __tablename__ = "refund_confirmations"
    __table_args__ = (UniqueConstraint("token", name="uq_refund_confirmation_token"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class RefundRequest(Base):
    __tablename__ = "refund_requests"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_refund_request_order"),
        UniqueConstraint("idempotency_key", name="uq_refund_idempotency_key"),
    )

    refund_request_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(32), default="审核中")
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    order: Mapped[Order] = relationship(back_populates="refund_requests")
