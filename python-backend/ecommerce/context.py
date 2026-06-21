from __future__ import annotations

from chatkit.agents import AgentContext
from pydantic import BaseModel


class EcommerceAgentContext(BaseModel):
    """Conversation state shared by the e-commerce support agents."""

    customer_name: str | None = None
    customer_id: str | None = None
    order_id: str | None = None
    product_name: str | None = None
    order_status: str | None = None
    tracking_number: str | None = None
    logistics_status: str | None = None
    refund_request_id: str | None = None
    refund_status: str | None = None
    pending_refund_confirmation: bool = False


class EcommerceAgentChatContext(AgentContext[dict]):
    state: EcommerceAgentContext


def create_initial_context() -> EcommerceAgentContext:
    return EcommerceAgentContext()


def public_context(ctx: EcommerceAgentContext) -> dict:
    return {
        key: value
        for key, value in ctx.model_dump().items()
        if value not in (None, False, [], {})
    }

