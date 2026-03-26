"""Shared LLM client initialization.

Follows the pattern from trading-agent/agents/research_agent.py:
Anthropic as primary, OpenAI as fallback.
"""
from __future__ import annotations

from config.settings import get_settings


def get_llm_client() -> tuple[str, object]:
    """Return (provider, client) tuple.

    Returns:
        ("anthropic", anthropic.Anthropic) or ("openai", openai.OpenAI)

    Raises:
        RuntimeError if no API key is configured.
    """
    settings = get_settings()

    if settings.anthropic_api_key:
        import anthropic
        return "anthropic", anthropic.Anthropic(api_key=settings.anthropic_api_key)

    if settings.openai_api_key:
        import openai
        return "openai", openai.OpenAI(api_key=settings.openai_api_key)

    raise RuntimeError(
        "No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env"
    )


def chat(system_prompt: str, user_prompt: str) -> str:
    """Send a chat completion and return the text response."""
    provider, client = get_llm_client()

    if provider == "anthropic":
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    # OpenAI
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4096,
    )
    return response.choices[0].message.content
