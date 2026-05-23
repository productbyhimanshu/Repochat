"""
rate_queue.py — 15 RPM guard for Gemini API.

Guards every Gemini call, implementing a simple sliding window / minimum interval
and retries on HTTP 429 ResourceExhausted with exponential backoff.
"""

import time
import asyncio
from typing import Callable, Any
from backend.logger import get_logger

log = get_logger("repochat.llm.rate_queue")

class RateQueue:
    def __init__(self, rpm_limit: int = 15):
        self.rpm_limit = rpm_limit
        self.interval = 60.0 / rpm_limit
        self.last_call_time = 0.0
        self._lock = asyncio.Lock()

    async def call(self, fn: Callable, *args, **kwargs) -> Any:
        """
        Execute `fn(*args, **kwargs)` ensuring we don't exceed the rate limit.
        Retries on 429 with exponential backoff.
        """
        max_retries = 5
        base_backoff = 2.0
        
        for attempt in range(max_retries):
            async with self._lock:
                now = time.time()
                elapsed = now - self.last_call_time
                if elapsed < self.interval:
                    wait_time = self.interval - elapsed
                    log.rate_queue(f"Rate limit approaching. Queuing for {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                
                self.last_call_time = time.time()

            try:
                # Support both async and sync wrappers
                if asyncio.iscoroutinefunction(fn):
                    return await fn(*args, **kwargs)
                else:
                    return fn(*args, **kwargs)
                    
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "ResourceExhausted" in err_str or "quota" in err_str.lower():
                    if attempt < max_retries - 1:
                        sleep_t = base_backoff * (2 ** attempt)
                        log.rate_queue(f"429 Rate Limit hit. Retrying in {sleep_t}s (Attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(sleep_t)
                        continue
                log.api_error("Gemini API", error=err_str)
                raise e

# Global singleton
rate_queue = RateQueue(rpm_limit=15)
