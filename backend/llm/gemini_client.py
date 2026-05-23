"""
gemini_client.py — LLM wrapper using OpenRouter (OpenAI-compatible API).
Routes to google/gemini-2.0-flash-lite-001 via OpenRouter.
All calls go through rate_queue. Only orchestrator.py should import this.
"""

import os
import httpx

from llm.rate_queue import rate_queue

_BASE = "https://openrouter.ai/api/v1/chat/completions"
_MODEL = "google/gemini-2.0-flash-lite-001"


def _api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env")
    return key


async def _do_generate(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            _BASE,
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
            json={
                "model": _MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.3,
            },
        )
        if r.status_code == 429:
            raise Exception("429 rate limit")
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise Exception(f"OpenRouter error: {data['error']}")
        return data["choices"][0]["message"]["content"]


async def generate(prompt: str) -> str:
    """Generate text via OpenRouter → Gemini 2.0 Flash Lite, rate-guarded at 15 RPM."""
    return await rate_queue.call(_do_generate, prompt)
