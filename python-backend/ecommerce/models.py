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

    # 订单表：这是 Agent 查询订单、物流、退款资格时依赖的真实业务数据。
    # 模型不直接编造订单状态，而是通过 Tool -> Service -> DB 读取这里的数据。
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

    # 物流主表：一个订单对应一条物流主信息。
    # 详细轨迹放在 LogisticsEvent，便于展示“最新状态 + 历史轨迹”。
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

    # 物流轨迹表：按时间倒序返回，前端可以展示最近物流节点。
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    logistics_id: Mapped[int] = mapped_column(ForeignKey("logistics.id"), index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(String(255))

    logistics: Mapped[Logistics] = relationship(back_populates="events")


class RefundConfirmation(Base):
    __tablename__ = "refund_confirmations"
    __table_args__ = (UniqueConstraint("token", name="uq_refund_confirmation_token"),)

    # 退款确认令牌表：
    # 第一阶段 check_refund 生成 token；第二阶段 create_refund 必须校验 token。
    # consumed_at 用来标记令牌已经使用，防止同一个确认被重复提交。
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

    # 退款申请表：
    # order_id 和 idempotency_key 都加唯一约束，作为数据库层兜底。
    # 即使接口被重复调用，也不会给同一订单创建多笔退款。
    refund_request_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(32), default="审核中")
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    order: Mapped[Order] = relationship(back_populates="refund_requests")
