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


# 按电商售后业务职责拆分多个专业 Agent，而不是把所有能力放进单个 Agent。
# 每个 Agent 只保留自己需要的 Prompt 和工具集合，降低错误工具调用概率。
# 入口 Triage Agent 负责判断意图，专业 Agent 负责具体查询或退款流程。


# Order Agent：只负责订单查询。
# 它只注册 get_order 工具，所以模型在这个 Agent 中不能直接操作物流或退款。
order_agent = Agent[EcommerceAgentChatContext](
    name="Order Agent",
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


# Logistics Agent：只负责物流查询。
# 用户第二轮只说“什么时候到”时，系统可以从 Context 里取上一轮订单号。
logistics_agent = Agent[EcommerceAgentChatContext](
    name="Logistics Agent",
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


# Refund Agent：退款是高风险写操作，所以拆成两个工具：
# 1. check_refund：只检查资格并生成确认令牌，不创建退款；
# 2. create_refund_request：用户明确确认后，后端再次校验令牌再写库。
refund_agent = Agent[EcommerceAgentChatContext](
    name="Refund Agent",
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


# AfterSales Policy Agent：回答通用售后政策。
# 这里适合以后扩展成 RAG：把售后规则、FAQ、产品说明书切片后放入向量库检索。
faq_agent = Agent[EcommerceAgentChatContext](
    name="AfterSales Policy Agent",
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


# Triage Agent：系统入口。
# 它不直接查库、不直接写业务数据，只负责识别用户意图并 Handoff 给专业 Agent。
# Handoff 表示把任务转交给另一个 Agent 继续处理，不等同于普通函数调用。
triage_agent = Agent[EcommerceAgentChatContext](
    name="Ecommerce Triage Agent",
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


# 专业 Agent 之间也允许继续 Handoff。
# 例子：用户先查订单，再问“什么时候到”，Order Agent 可以把任务交给 Logistics Agent。
# 这样多轮对话不用重新从入口开始，也能保留上下文。
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
