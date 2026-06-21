from __future__ import annotations

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
)

@input_guardrail(name="Ecommerce Safety Guardrail")
async def ecommerce_safety_guardrail(
    context: RunContextWrapper[None],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Use a local rule guardrail so normal requests do not consume extra tokens."""
    if isinstance(input, str):
        text = input
    else:
        text = " ".join(str(item) for item in input)
    lowered = text.lower()
    blocked_phrases = (
        "system prompt",
        "系统提示词",
        "忽略之前",
        "ignore previous",
        "绕过确认",
        "跳过确认",
        "drop table",
    )
    matched = next((phrase for phrase in blocked_phrases if phrase in lowered), None)
    is_safe = matched is None
    return GuardrailFunctionOutput(
        output_info={
            "reasoning": "未命中危险规则" if is_safe else f"命中危险规则：{matched}",
            "is_safe": is_safe,
        },
        tripwire_triggered=not is_safe,
    )
