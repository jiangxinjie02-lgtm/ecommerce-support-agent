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
    # Guardrail 是 Agent 外围的安全边界。这里用本地规则快速拦截提示词注入、
    # 绕过退款确认、危险数据库指令等输入，不额外消耗模型 token。
    # 注意：这只是第一层防护，退款真正的安全校验仍在 services.py。
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
    # 命中危险短语就触发 tripwire，当前这轮 Agent 执行会被中断。
    matched = next((phrase for phrase in blocked_phrases if phrase in lowered), None)
    is_safe = matched is None
    return GuardrailFunctionOutput(
        output_info={
            "reasoning": "未命中危险规则" if is_safe else f"命中危险规则：{matched}",
            "is_safe": is_safe,
        },
        tripwire_triggered=not is_safe,
    )
