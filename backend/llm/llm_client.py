"""
llm_client.py — Claude Sonnet 4.5 wrapper via Emergent LLM Key (universal key).

All calls go through rate_queue. Only orchestrator.py should import this.
"""

import os
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage

from llm.rate_queue import rate_queue
from logger import get_logger

log = get_logger("repochat.llm.client")

_MODEL_PROVIDER = "anthropic"
_MODEL_NAME = "claude-sonnet-4-5-20250929"

_SYSTEM = (
    "You are RepoChat, an expert software architect. "
    "You analyze GitHub repositories and explain them in plain English. "
    "Be precise, cite real file names, and never invent details."
)


def _api_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY is not set in .env")
    return key


async def _do_generate(prompt: str) -> str:
    chat = LlmChat(
        api_key=_api_key(),
        session_id=f"repochat-{uuid.uuid4()}",
        system_message=_SYSTEM,
    ).with_model(_MODEL_PROVIDER, _MODEL_NAME).with_params(max_tokens=2048, temperature=0.3)

    response = await chat.send_message(UserMessage(text=prompt))
    if isinstance(response, str):
        return response
    return str(response)


async def generate(prompt: str) -> str:
    """Generate text via Claude Sonnet 4.5, rate-guarded."""
    return await rate_queue.call(_do_generate, prompt)
