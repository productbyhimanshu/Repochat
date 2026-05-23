"""
gemini_client.py — Single Gemini API wrapper.

All calls must go through rate_queue.call().
"""

import os
import google.generativeai as genai
from backend.llm.rate_queue import rate_queue

# Initialize the SDK
_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if _API_KEY:
    genai.configure(api_key=_API_KEY)

async def _do_generate(prompt: str) -> str:
    """Actual API call wrapped by generate."""
    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    response = await model.generate_content_async(prompt)
    return response.text

async def generate(prompt: str) -> str:
    """
    Generate text using gemini-2.0-flash-lite.
    Enforces the 15 RPM limit via the rate queue.
    """
    return await rate_queue.call(_do_generate, prompt)
