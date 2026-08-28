"""
src/utils/llm.py
─────────────────
Shared factory for Groq chat models.

All three agents build their LLM through `build_groq_llm` so they share a
single process-wide rate limiter. Groq's free tier for `openai/gpt-oss-120b`
allows roughly 30 requests/minute; without throttling the pipeline bursts
past that and every call starts coming back as HTTP 429.
"""

import logging

from langchain_groq import ChatGroq
from langchain_core.rate_limiters import InMemoryRateLimiter

from config.settings import settings

logger = logging.getLogger(__name__)


# One bucket for the whole pipeline. Agents 1/2/3 all draw from this, so the
# combined request rate — not each agent individually — stays under the limit.
_rate_limiter = InMemoryRateLimiter(
    requests_per_second=float(settings.groq_requests_per_second),
    check_every_n_seconds=0.1,
    max_bucket_size=1,
)


def build_groq_llm(model: str, temperature: float = 0.2) -> ChatGroq:
    """Create a ChatGroq client wired to the shared rate limiter."""
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=model,
        temperature=temperature,
        rate_limiter=_rate_limiter,
        max_retries=settings.groq_max_retries,
        timeout=settings.groq_timeout_seconds,
    )
