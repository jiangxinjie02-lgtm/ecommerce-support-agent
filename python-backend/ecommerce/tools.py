from __future__ import annotations

import json

from agents import RunContextWrapper, function_tool
from chatkit.types import ProgressUpdateEvent

from .context import EcommerceAgentChatContext
from .services import (
    check_refund_eligibility,
    create_refund,
    query_logistics,
    query_order,
)


def _dump(data: dict) -> str:
    # 工具统一返回 JSON 字符串。
    # 模型负责理解用户语言，工具负责返回结构化、可追踪的真实业务数据。
    return json.dumps(data, ensure_ascii=False)


@function_tool
async def get_order(
    context: RunContextWrapper[EcommerceAgentChatContext], order_id: str
) -> str:
    """根据订单号查询订单、商品、金额和订单状态。"""
    await context.context.stream(ProgressUpdateEvent(text=f"正在查询订单 {order_id}..."))
    # Tool Calling 入口：
    # 模型只生成 get_order(order_id=...) 这样的结构化调用；
    # 真正的数据库查询在 services.query_order 里完成，避免模型编造订单状态。
    result = query_order(order_id)
    if result["success"]:
        order = result["order"]
        state = context.context.state
        # 把订单信息写入结构化 Context。
        # 后续用户只说“这个订单什么时候到”时，Agent 可以复用上一轮状态。
        state.order_id = order["order_id"]
        state.customer_id = order["customer_id"]
        state.customer_name = order["customer_name"]
        state.product_name = order["product_name"]
        state.order_status = order["order_status"]
        state.tracking_number = order["tracking_number"]
    return _dump(result)


@function_tool
async def get_logistics(
    context: RunContextWrapper[EcommerceAgentChatContext], order_id: str
) -> str:
    """根据订单号查询快递公司、运单号、物流状态和最新轨迹。"""
    await context.context.stream(ProgressUpdateEvent(text=f"正在查询订单 {order_id} 的物流..."))
    # 物流查询同样通过工具读取数据库，而不是让模型凭空回答。
    # 连续追问“什么时候到”时，可以复用上一轮 Context 中保存的订单信息。
    result = query_logistics(order_id)
    if result["success"]:
        state = context.context.state
        state.order_id = result["order_id"]
        state.tracking_number = result["tracking_number"]
        state.logistics_status = result["logistics"]["status"]
    return _dump(result)


@function_tool
async def check_refund(
    context: RunContextWrapper[EcommerceAgentChatContext], order_id: str
) -> str:
    """检查订单是否满足退款条件，不会实际创建退款。"""
    # 退款第一阶段：只检查资格，不创建退款申请。
    # 如果符合条件，Service 会生成一个限时确认令牌，保存在后端状态里。
    result = check_refund_eligibility(order_id)
    context.context.state.order_id = order_id.upper()
    context.context.state.pending_refund_confirmation = bool(result.get("eligible"))
    # 令牌只放在服务端 Context，不返回给模型/前端展示。
    # 这样用户看不到令牌，也不能伪造令牌绕过确认。
    context.context.state.refund_confirmation_token = result.pop(
        "confirmation_token", None
    )
    return _dump(result)


@function_tool
async def create_refund_request(
    context: RunContextWrapper[EcommerceAgentChatContext],
    order_id: str,
    reason: str,
    confirmed: bool = False,
) -> str:
    """创建退款申请。只有用户明确确认时 confirmed 才能为 true。"""
    await context.context.stream(ProgressUpdateEvent(text="正在提交退款申请..."))
    # 退款第二阶段：真正创建退款申请。
    # confirmed=True 也是模型传入的参数，不能完全信任；
    # 所以还要把第一阶段生成的 confirmation_token 传给 Service 做强校验。
    state = context.context.state
    result = create_refund(
        order_id,
        reason,
        confirmed,
        confirmation_token=state.refund_confirmation_token,
    )
    state.order_id = order_id.upper()
    state.pending_refund_confirmation = bool(result.get("confirmation_required"))
    if result["success"]:
        # 创建成功后清空确认状态，避免同一个确认令牌被重复使用。
        state.refund_request_id = result["refund"]["refund_request_id"]
        state.refund_status = result["refund"]["status"]
        state.pending_refund_confirmation = False
        state.refund_confirmation_token = None
    return _dump(result)


@function_tool
async def after_sales_policy(question: str) -> str:
    """查询退换货、运费和退款到账时间等售后政策。"""
    # 当前是本地规则版 FAQ。
    # 如果做生产版，可以替换成 RAG：向量库检索售后政策文档，再让模型组织回答。
    q = question.lower()
    if "七天" in q or "退货" in q or "退款" in q:
        return "商品签收后 7 天内，在不影响二次销售的情况下可申请退货退款。"
    if "运费" in q:
        return "质量问题由商家承担退回运费；无理由退货通常由买家承担运费。"
    if "到账" in q:
        return "退款审核通过后，通常会在 1 至 5 个工作日原路退回。"
    return "暂未匹配到对应政策，请转人工客服进一步确认。"

