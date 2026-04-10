"""Currency exchange rate service — fetches live USD/VND rate.

Uses free APIs (no API key required):
  1. Primary: frankfurter.app (ECB data)
  2. Fallback: open.er-api.com

Caches the rate for 6 hours to minimize API calls.
"""
import logging
import time
import httpx

logger = logging.getLogger(__name__)

# Cache
_cached_rate: float | None = None
_cache_time: float = 0
_CACHE_TTL = 6 * 3600  # 6 hours

# Fallback if all APIs fail
_FALLBACK_RATE = 25_500.0

_APIs = [
    {
        "name": "open.er-api.com",
        "url": "https://open.er-api.com/v6/latest/USD",
        "extract": lambda data: data["rates"]["VND"],
    },
    {
        "name": "cdn.jsdelivr.net (fawazahmed0)",
        "url": "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
        "extract": lambda data: data["usd"]["vnd"],
    },
]


async def get_usd_to_vnd() -> float:
    """Get current USD to VND exchange rate.

    Returns cached rate if fresh, otherwise fetches from API.
    Falls back to hardcoded rate if all APIs fail.
    """
    global _cached_rate, _cache_time

    # Return cached rate if still valid
    if _cached_rate and (time.time() - _cache_time) < _CACHE_TTL:
        return _cached_rate

    # Try each API
    for api in _APIs:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(api["url"])
                resp.raise_for_status()
                data = resp.json()
                rate = float(api["extract"](data))

                if rate > 0:
                    _cached_rate = rate
                    _cache_time = time.time()
                    logger.info(
                        f"💱 USD/VND rate updated: {rate:,.0f} "
                        f"(from {api['name']})"
                    )
                    return rate

        except Exception as e:
            logger.warning(f"Failed to fetch rate from {api['name']}: {e}")
            continue

    # All APIs failed — use cached or fallback
    if _cached_rate:
        logger.warning(
            f"Using stale cached rate: {_cached_rate:,.0f}"
        )
        return _cached_rate

    logger.warning(
        f"All exchange APIs failed. Using fallback: {_FALLBACK_RATE:,.0f}"
    )
    return _FALLBACK_RATE


def get_cached_rate() -> float:
    """Get the current cached rate (sync, for parsers).

    Returns fallback if no rate has been fetched yet.
    """
    return _cached_rate or _FALLBACK_RATE
