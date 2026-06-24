from __future__ import annotations

from chatkit.agents import AgentContext
from pydantic import BaseModel


class EcommerceAgentContext(BaseModel):
    """Conversation state shared by the e-commerce support agents."""

    # 聊天记录保存自然语言消息；Context 保存程序需要的结构化业务状态。
    # 例如上一轮查到 order_id，下一轮用户只说“什么时候到”，物流 Agent 也能继续处理。
    customer_name: str | None = None
    customer_id: str | None = None
    order_id: str | None = None
    product_name: str | None = None
    order_status: str | None = None
    tracking_number: str | None = None
    logistics_status: str | None = None
    refund_request_id: str | None = None
    refund_status: str | None = None
    # 退款确认令牌是敏感状态，只保存在服务端，用来做第二阶段强校验。
    refund_confirmation_token: str | None = None
    pending_refund_confirmation: bool = False


class EcommerceAgentChatContext(AgentContext[dict]):
    state: EcommerceAgentContext


def create_initial_context() -> EcommerceAgentContext:
    return EcommerceAgentContext()


def public_context(ctx: EcommerceAgentContext) -> dict:
    # 前端只展示安全的 Context。
    # refund_confirmation_token 不能出现在页面或模型可见内容里，避免被用户伪造/复用。
    return {
        key: value
        for key, value in ctx.model_dump().items()
        if key != "refund_confirmation_token"
        and value not in (None, False, [], {})
    }

