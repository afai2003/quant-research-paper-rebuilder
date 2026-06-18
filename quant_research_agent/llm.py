from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm(temperature: float = 0.1) -> ChatOpenAI:
    """Create the chat model used by every agent.

    Environment variables:
        DEEPSEEK_API_KEY: Required.
        DEEPSEEK_MODEL: Optional, defaults to ``deepseek-chat``.
        DEEPSEEK_BASE_URL: Optional, defaults to DeepSeek's API URL.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is missing. Copy .env.example to .env and set your API key."
        )

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )
