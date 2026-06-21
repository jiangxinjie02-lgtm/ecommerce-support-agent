from __future__ import annotations

import os
from functools import lru_cache

from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"


@lru_cache(maxsize=1)
def get_agent_model() -> OpenAIChatCompletionsModel:
    """Build the DeepSeek-backed model used by every agent."""
    # Keep imports and offline tests usable before the developer adds a key.
    # DeepSeek will reject actual model calls until a real key is configured.
    api_key = os.getenv("DEEPSEEK_API_KEY", "missing-deepseek-api-key")

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
    )
    return OpenAIChatCompletionsModel(
        model=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
        openai_client=client,
    )
