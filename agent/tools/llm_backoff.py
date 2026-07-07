"""Retry-with-backoff wrapper around ctx.run_node for LLM sub-agent calls.

The Gemini free tier caps at 5 requests/minute per model, and this
pipeline can make well over that per issue (triage + up to 3 retries of
coding+review + a PR draft). Rather than let the whole run die on a 429,
back off and retry -- rate limits are an expected, transient condition
here, not a bug.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_RETRYABLE_MARKERS = ("RESOURCE_EXHAUSTED", "429")
_BACKOFF_SECONDS = 20
_MAX_RETRIES = 5


def _is_rate_limit_error(exc: Exception) -> bool:
    candidates = [exc, getattr(exc, "error", None), exc.__cause__]
    return any(
        any(marker in str(c) for marker in _RETRYABLE_MARKERS)
        for c in candidates
        if c is not None
    )


async def run_node_with_backoff(ctx, node, node_input):
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return await ctx.run_node(node, node_input)
        except Exception as e:  # noqa: BLE001 -- deliberately broad: only retries transient rate limits, re-raises everything else
            if not _is_rate_limit_error(e):
                raise
            last_exc = e
            wait = _BACKOFF_SECONDS * (attempt + 1)
            node_name = getattr(node, "name", str(node))
            logger.warning(
                "Rate-limited calling %s, backing off %ss (attempt %s/%s)",
                node_name,
                wait,
                attempt + 1,
                _MAX_RETRIES,
            )
            await asyncio.sleep(wait)
    assert last_exc is not None
    raise last_exc
