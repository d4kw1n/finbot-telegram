"""Parse Vietnamese currency amounts from natural language text.

Supports formats commonly used in Vietnamese daily conversations:
  50k, 50K     → 50,000
  2tr, 2 triệu → 2,000,000
  2tr5          → 2,500,000
  2.5tr         → 2,500,000
  1 củ          → 1,000,000
  5 trăm        → 500,000
  50.000        → 50,000
  $25           → 637,500 (converted to VND)
"""
import re

from src.services.currency_service import get_cached_rate


def _get_usd_rate() -> float:
    """Get current USD/VND rate for amount conversion."""
    return get_cached_rate()

# Patterns ordered by specificity (most specific first)
_AMOUNT_PATTERNS = [
    # 2.5tr, 2,5tr, 2.5 triệu
    (r'(\d+)[.,](\d+)\s*(?:tr(?:iệu)?)',
     lambda m: (int(m.group(1)) + int(m.group(2)) / (10 ** len(m.group(2)))) * 1_000_000),

    # 2tr5 → 2,500,000
    (r'(\d+)\s*(?:tr(?:iệu)?)\s*(\d)',
     lambda m: int(m.group(1)) * 1_000_000 + int(m.group(2)) * 100_000),

    # 15tr, 15 triệu
    (r'(\d+)\s*(?:tr(?:iệu)?)',
     lambda m: int(m.group(1)) * 1_000_000),

    # 2 củ → 2,000,000
    (r'(\d+)\s*(?:củ)',
     lambda m: int(m.group(1)) * 1_000_000),

    # 50k, 50K
    (r'(\d+)\s*[kK](?:\b|$)',
     lambda m: int(m.group(1)) * 1_000),

    # 5 trăm → 500,000 (Vietnamese shorthand for "5 trăm ngàn")
    (r'(\d+)\s*(?:trăm)\s*(?:ngàn|nghìn|k)?',
     lambda m: int(m.group(1)) * 100_000),

    # $25 → convert to VND using live exchange rate
    (r'\$\s*(\d+(?:\.\d{1,2})?)',
     lambda m: float(m.group(1)) * _get_usd_rate()),

    # 50.000 or 50,000 (dot/comma as thousands separator)
    (r'(\d{1,3}(?:[.,]\d{3})+)',
     lambda m: float(m.group(1).replace('.', '').replace(',', ''))),

    # Plain number >= 1000 (assumed VND)
    (r'(?<!\d)(\d{4,})(?!\d)',
     lambda m: float(m.group(1))),
]


def parse_amount(text: str) -> tuple[float | None, str]:
    """Parse a Vietnamese currency amount from text.

    Returns:
        (amount, remaining_text) if amount found.
        (None, original_text) if no amount detected.

    Examples:
        >>> parse_amount("ăn phở 50k")
        (50000.0, "ăn phở")
        >>> parse_amount("grab 2tr5")
        (2500000.0, "grab")
        >>> parse_amount("hello world")
        (None, "hello world")
    """
    for pattern, extractor in _AMOUNT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount = float(extractor(match))
                remaining = (text[:match.start()] + text[match.end():]).strip()
                remaining = re.sub(r'\s+', ' ', remaining).strip()
                return amount, remaining
            except (ValueError, IndexError):
                continue

    return None, text
