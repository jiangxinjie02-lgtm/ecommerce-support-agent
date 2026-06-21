from __future__ import annotations

from agents import Agent
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

from .context import EcommerceAgentChatContext
from .guardrails import ecommerce_safety_guardrail
from .model_config import get_agent_model
from .tools import (
    after_sales_policy,
    check_refund,
    create_refund_request,
    get_logistics,
    get_order,
)


MODEL = get_agent_model()


order_agent = Agent[EcommerceAgentChatContext](
    name="订单查询 Agent",
    model=MODEL,
    handoff_description="查询订单、商品、金额、支付和订单状态。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你负责订单查询。需要订单号时只询问一次；拿到订单号后立即调用 get_order。"
        "基于工具结果回答，不得编造订单。物流问题转给物流查询 Agent，退款问题转给退款处理 Agent。"
    ),
    tools=[get_order],
    input_guardrails=[ecommerce_safety_guardrail],
)


logistics_agent = Agent[EcommerceAgentChatContext](
    name="物流查询 Agent",
    model=MODEL,
    handoff_description="查询快递公司、运单号、预计送达时间和物流轨迹。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你负责物流查询。获取订单号后调用 get_logistics，并用简洁中文说明最新物流状态。"
        "如果没有物流信息，如实说明，不得虚构。其他问题交回分流 Agent。"
    ),
    tools=[get_logistics],
    input_guardrails=[ecommerce_safety_guardrail],
)


refund_agent = Agent[EcommerceAgentChatContext](
    name="退款处理 Agent",
    model=MODEL,
    handoff_description="检查退款条件，并在用户明确确认后创建退款申请。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你负责退款。先调用 check_refund 检查条件。退款是高风险操作："
        "在用户明确回复确认退款之前，create_refund_request 的 confirmed 必须为 false。"
        "用户明确确认后才可传 confirmed=true。成功后返回退款申请编号和状态。"
    ),
    tools=[check_refund, create_refund_request],
    input_guardrails=[ecommerce_safety_guardrail],
)


faq_agent = Agent[EcommerceAgentChatContext](
    name="售后政策 Agent",
    model=MODEL,
    handoff_description="回答退换货期限、运费和退款到账时间。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你负责售后政策问答，必须调用 after_sales_policy 获取答案。"
        "涉及具体订单时转交订单或退款 Agent。"
    ),
    tools=[after_sales_policy],
    input_guardrails=[ecommerce_safety_guardrail],
)


triage_agent = Agent[EcommerceAgentChatContext](
    name="电商客服分流 Agent",
    model=MODEL,
    handoff_description="识别用户意图并转交订单、物流、退款或售后政策 Agent。",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX}\n"
        "你是电商售后客服入口。订单状态交给订单查询 Agent；"
        "快递和到货时间交给物流查询 Agent；退款退货交给退款处理 Agent；"
        "规则政策交给售后政策 Agent。意图明确时立即 handoff，不要自己编造业务结果。"
    ),
    handoffs=[order_agent, logistics_agent, refund_agent, faq_agent],
    input_guardrails=[ecommerce_safety_guardrail],
)


order_agent.handoffs.extend([logistics_agent, refund_agent, triage_agent])
logistics_agent.handoffs.extend([order_agent, refund_agent, triage_agent])
refund_agent.handoffs.extend([order_agent, faq_agent, triage_agent])
faq_agent.handoffs.extend([order_agent, refund_agent, triage_agent])


ALL_AGENTS = [
    triage_agent,
    order_agent,
    logistics_agent,
    refund_agent,
    faq_agent,
]

