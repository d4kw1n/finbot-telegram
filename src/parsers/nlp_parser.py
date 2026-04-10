"""Natural language parser for transaction messages.

Parses messages like "ăn phở 50k ck hôm qua" into structured transaction data:
  amount=50000, description="ăn phở", payment="bank", date=yesterday
"""
import re
from datetime import date, timedelta

from src.parsers.amount_parser import parse_amount
from src.utils.constants import PAYMENT_METHODS


def _parse_payment_method(text: str) -> tuple[str, str]:
    """Detect payment method from keywords in text.

    Returns (method_key, remaining_text).
    """
    text_lower = text.lower()
    for method_key, method_info in PAYMENT_METHODS.items():
        for keyword in method_info["keywords"]:
            # Word boundary matching to avoid partial matches
            pattern = r'(?:^|\s)(' + re.escape(keyword) + r')(?:\s|$|[.,!?])'
            match = re.search(pattern, text_lower)
            if match:
                # Remove the keyword from original text (preserving case)
                start = match.start(1)
                end = match.end(1)
                remaining = (text[:start] + text[end:]).strip()
                remaining = re.sub(r'\s+', ' ', remaining).strip()
                return method_key, remaining
    return "cash", text


def _parse_date(text: str) -> tuple[date, str]:
    """Parse date references from text.

    Returns (parsed_date, remaining_text).
    """
    today = date.today()
    text_lower = text.lower().strip()

    # Vietnamese date keywords
    date_keywords = [
        (r'hôm\s*qua', today - timedelta(days=1)),
        (r'hôm\s*kia', today - timedelta(days=2)),
        (r'hôm\s*nay', today),
    ]

    for pattern, d in date_keywords:
        match = re.search(pattern, text_lower)
        if match:
            remaining = (text[:match.start()] + text[match.end():]).strip()
            remaining = re.sub(r'\s+', ' ', remaining).strip()
            return d, remaining

    # DD/MM or DD/MM/YYYY
    match = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', text)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            d = date(year, month, day)
            remaining = (text[:match.start()] + text[match.end():]).strip()
            return d, remaining.strip()
        except ValueError:
            pass

    return today, text


def _parse_transaction_type(text: str) -> tuple[str, str]:
    """Detect if this is income (+) or expense (default).

    Returns (type, remaining_text).
    """
    text = text.strip()
    if text.startswith('+'):
        return "income", text[1:].strip()
    if text.startswith('-'):
        return "expense", text[1:].strip()
    return "expense", text


def has_amount(text: str) -> bool:
    """Quick check if text likely contains a monetary amount."""
    # Check for number patterns common in Vietnamese money
    return bool(re.search(
        r'\d+\s*[kK]|\d+\s*tr|\d+\s*triệu|\d+\s*củ|\$\s*\d|\d{4,}|\d{1,3}[.,]\d{3}',
        text, re.IGNORECASE
    ))


def parse_message(text: str) -> dict:
    """Parse a natural language transaction message.

    Args:
        text: Raw message text, e.g. "ăn phở 50k ck hôm qua"

    Returns:
        dict with keys: amount, description, type, payment_method, date, raw
        If parsing fails, amount will be None and error will be set.

    Examples:
        >>> parse_message("ăn phở 50k")
        {"amount": 50000, "description": "ăn phở", "type": "expense",
         "payment_method": "cash", "date": date.today(), "raw": "ăn phở 50k"}

        >>> parse_message("+15tr lương")
        {"amount": 15000000, "description": "lương", "type": "income",
         "payment_method": "cash", "date": date.today(), "raw": "+15tr lương"}
    """
    raw = text.strip()

    # 1. Income/expense
    tx_type, text = _parse_transaction_type(text)

    # 2. Amount
    amount, text = parse_amount(text)
    if amount is None:
        return {"amount": None, "raw": raw, "error": "no_amount"}

    # 3. Payment method
    payment_method, text = _parse_payment_method(text)

    # 4. Date
    tx_date, text = _parse_date(text)

    # 5. Remaining = description
    description = re.sub(r'\s+', ' ', text).strip()
    description = description.strip('.,;:!?-+ ')

    return {
        "amount": amount,
        "description": description,
        "type": tx_type,
        "payment_method": payment_method,
        "date": tx_date,
        "raw": raw,
    }
