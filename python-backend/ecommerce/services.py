from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .database import init_database, session_scope
from .models import (
    Logistics,
    Order,
    RefundConfirmation,
    RefundRequest,
)
from .seed import seed_demo_data


CONFIRMATION_TTL_MINUTES = 10
ACTIVE_REFUND_STATUSES = {"审核中", "退款处理中", "退款完成"}


def _utc_now() -> datetime:
    # 数据库里统一存 UTC 时间，避免部署到不同机器时出现时区不一致。
    return datetime.now(UTC).replace(tzinfo=None)


def _ensure_database() -> None:
    # 应用启动时自动建表并写入示例数据。
    # 本地默认使用 SQLite；切换 MySQL 时，Service 层业务逻辑基本不用变化。
    init_database()
    seed_demo_data()


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _order_dict(order: Order) -> dict:
    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name,
        "product_name": order.product_name,
        "amount": _money(order.amount),
        "payment_status": order.payment_status,
        "order_status": order.order_status,
        "created_at": order.created_at.strftime("%Y-%m-%d %H:%M"),
        "tracking_number": order.tracking_number,
        "refundable": order.refundable,
    }


def _refund_dict(refund: RefundRequest) -> dict:
    return {
        "refund_request_id": refund.refund_request_id,
        "order_id": refund.order_id,
        "reason": refund.reason,
        "amount": _money(refund.amount),
        "status": refund.status,
        "created_at": refund.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


def query_order(order_id: str, customer_id: str | None = None) -> dict:
    # 订单查询是只读工具，Agent 不直接拼 SQL。
    # 这里做订单号标准化、权限检查和统一返回结构。
    _ensure_database()
    normalized = order_id.strip().upper()
    with session_scope() as session:
        order = session.get(Order, normalized)
        if not order:
            return {"success": False, "message": f"未找到订单 {normalized}"}
        if customer_id and order.customer_id != customer_id:
            return {
                "success": False,
                "message": "当前用户无权查看该订单",
                "forbidden": True,
            }
        return {"success": True, "order": _order_dict(order)}


def query_logistics(order_id: str, customer_id: str | None = None) -> dict:
    # 物流查询会同时加载物流主表和物流轨迹。
    # selectinload 用来避免循环读取事件时频繁查询数据库。
    _ensure_database()
    normalized = order_id.strip().upper()
    with session_scope() as session:
        statement = (
            select(Order)
            .where(Order.order_id == normalized)
            .options(selectinload(Order.logistics).selectinload(Logistics.events))
        )
        order = session.scalar(statement)
        if not order:
            return {"success": False, "message": f"未找到订单 {normalized}"}
        if customer_id and order.customer_id != customer_id:
            return {
                "success": False,
                "message": "当前用户无权查看该订单",
                "forbidden": True,
            }
        if not order.logistics:
            return {"success": False, "message": "该订单暂无物流信息"}

        logistics = order.logistics
        return {
            "success": True,
            "order_id": order.order_id,
            "tracking_number": logistics.tracking_number,
            "logistics": {
                "carrier": logistics.carrier,
                "status": logistics.status,
                "estimated_delivery": (
                    logistics.estimated_delivery.isoformat()
                    if logistics.estimated_delivery
                    else None
                ),
                "latest_event": logistics.latest_event,
                "events": [
                    f"{event.event_time:%Y-%m-%d %H:%M} {event.description}"
                    for event in logistics.events
                ],
            },
        }


def check_refund_eligibility(
    order_id: str,
    customer_id: str | None = None,
    issue_confirmation: bool = True,
) -> dict:
    # 退款第一阶段：只做资格检查，不写入退款申请。
    # 高风险写操作不能只靠 Prompt 控制，必须由后端业务逻辑做强校验。
    _ensure_database()
    normalized = order_id.strip().upper()
    with session_scope() as session:
        order = session.get(Order, normalized)
        if not order:
            return {"success": False, "eligible": False, "message": "订单不存在"}
        if customer_id and order.customer_id != customer_id:
            return {
                "success": False,
                "eligible": False,
                "forbidden": True,
                "message": "当前用户无权操作该订单",
            }

        # 幂等/重复申请检查：
        # 如果订单已经有进行中的退款申请，直接返回旧申请，避免重复退款。
        existing = session.scalar(
            select(RefundRequest).where(RefundRequest.order_id == normalized)
        )
        if existing and existing.status in ACTIVE_REFUND_STATUSES:
            return {
                "success": False,
                "eligible": False,
                "duplicate": True,
                "message": "该订单已存在退款申请，请勿重复提交",
                "refund": _refund_dict(existing),
            }

        if not order.refundable:
            return {
                "success": False,
                "eligible": False,
                "message": "该订单当前状态不支持退款",
            }

        result = {
            "success": True,
            "eligible": True,
            "message": "订单满足退款申请条件，提交前需要用户明确确认",
            "order": _order_dict(order),
        }
        if issue_confirmation:
            # 生成新的确认令牌前，先把旧的未使用令牌作废。
            # 这样用户必须基于最新一次检查结果进行确认。
            now = _utc_now()
            old_confirmations = session.scalars(
                select(RefundConfirmation).where(
                    RefundConfirmation.order_id == normalized,
                    RefundConfirmation.consumed_at.is_(None),
                )
            )
            for confirmation in old_confirmations:
                confirmation.consumed_at = now

            token = uuid4().hex
            expires_at = now + timedelta(minutes=CONFIRMATION_TTL_MINUTES)
            # 确认令牌保存在后端，不展示给用户。
            # 第二阶段创建退款时必须带着这个令牌回来，才能证明已经走过检查流程。
            session.add(
                RefundConfirmation(
                    order_id=normalized,
                    token=token,
                    expires_at=expires_at,
                )
            )
            result["confirmation_token"] = token
            result["confirmation_expires_at"] = expires_at.isoformat()
        return result


def create_refund(
    order_id: str,
    reason: str,
    confirmed: bool,
    confirmation_token: str | None = None,
    customer_id: str | None = None,
) -> dict:
    # 退款第二阶段：真正写入退款申请。
    # 这里是安全核心：不能只相信模型传来的 confirmed=True。
    _ensure_database()
    normalized = order_id.strip().upper()
    clean_reason = reason.strip()
    if not confirmed:
        # 没有用户明确确认时，直接拒绝写操作。
        return {
            "success": False,
            "confirmation_required": True,
            "message": "退款属于高风险操作，请用户明确回复确认退款后再提交",
        }
    if not confirmation_token:
        # 没有后端确认令牌时，即使模型传了 confirmed=True，也不能创建退款。
        return {
            "success": False,
            "confirmation_required": True,
            "message": "退款确认信息不存在或已失效，请重新检查退款资格",
        }
    if len(clean_reason) < 2:
        return {"success": False, "message": "请提供有效的退款原因"}

    with session_scope() as session:
        order = session.get(Order, normalized)
        if not order:
            return {"success": False, "message": "订单不存在"}
        if customer_id and order.customer_id != customer_id:
            return {
                "success": False,
                "forbidden": True,
                "message": "当前用户无权操作该订单",
            }

        # 再次检查重复申请，防止用户重复点击、网络重试或模型重复调用。
        existing = session.scalar(
            select(RefundRequest).where(RefundRequest.order_id == normalized)
        )
        if existing:
            return {
                "success": True,
                "idempotent": True,
                "message": "该订单的退款申请已存在，返回原申请",
                "refund": _refund_dict(existing),
            }

        # 确认令牌必须满足：
        # 1. 属于当前订单；
        # 2. token 内容匹配；
        # 3. 尚未被消费；
        # 4. 未过期。
        confirmation = session.scalar(
            select(RefundConfirmation).where(
                RefundConfirmation.order_id == normalized,
                RefundConfirmation.token == confirmation_token,
                RefundConfirmation.consumed_at.is_(None),
            )
        )
        now = _utc_now()
        if not confirmation or confirmation.expires_at < now:
            return {
                "success": False,
                "confirmation_required": True,
                "message": "退款确认已过期，请重新检查退款资格",
            }
        if not order.refundable:
            return {"success": False, "message": "该订单当前状态不支持退款"}

        # session_scope 会统一提交事务。
        # 创建退款、消费确认令牌、更新订单状态要么全部成功，要么全部回滚。
        request = RefundRequest(
            refund_request_id=f"RF{uuid4().hex[:8].upper()}",
            order_id=normalized,
            reason=clean_reason,
            amount=order.amount,
            status="审核中",
            idempotency_key=f"refund:{normalized}",
        )
        session.add(request)
        confirmation.consumed_at = now
        order.refundable = False
        order.order_status = "退款审核中"
        session.flush()
        return {"success": True, "refund": _refund_dict(request)}


def query_refund(order_id: str, customer_id: str | None = None) -> dict:
    # 退款查询是只读能力，方便以后扩展“查看退款进度”工具。
    _ensure_database()
    normalized = order_id.strip().upper()
    with session_scope() as session:
        statement = (
            select(RefundRequest)
            .join(Order)
            .where(RefundRequest.order_id == normalized)
        )
        if customer_id:
            statement = statement.where(Order.customer_id == customer_id)
        refund = session.scalar(statement)
        if not refund:
            return {"success": False, "message": "未找到退款申请"}
        return {"success": True, "refund": _refund_dict(refund)}
