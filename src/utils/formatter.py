"""Utility functions for formatting currency, dates, and display elements."""
from datetime import date, datetime


def format_currency(amount: float, short: bool = False) -> str:
    """Format amount as Vietnamese currency.

    Args:
        amount: The amount in VND.
        short: If True, use compact format (50k, 2.5tr).

    Examples:
        format_currency(50000) → "50,000đ"
        format_currency(2500000, short=True) → "2.5tr"
    """
    if amount < 0:
        sign = "-"
        amount = abs(amount)
    else:
        sign = ""

    if short:
        if amount >= 1_000_000_000:
            v = amount / 1_000_000_000
            return f"{sign}{v:.1f}tỷ" if v != int(v) else f"{sign}{int(v)}tỷ"
        elif amount >= 1_000_000:
            v = amount / 1_000_000
            return f"{sign}{v:.1f}tr" if v != int(v) else f"{sign}{int(v)}tr"
        elif amount >= 1_000:
            v = amount / 1_000
            return f"{sign}{v:.0f}k"
        return f"{sign}{int(amount)}đ"

    formatted = f"{amount:,.0f}".replace(",", ".")
    return f"{sign}{formatted}đ"


def progress_bar(current: float, total: float, length: int = 10) -> str:
    """Create a text-based progress bar.

    Example: progress_bar(7500, 10000) → "▓▓▓▓▓▓▓░░░"
    """
    if total <= 0:
        return "░" * length

    pct = min(max(current / total, 0), 1.0)
    filled = int(pct * length)
    return "▓" * filled + "░" * (length - filled)


def percentage(current: float, total: float) -> str:
    """Format as percentage string."""
    if total <= 0:
        return "0%"
    return f"{(current / total) * 100:.0f}%"


def format_date(d: date) -> str:
    """Format date as DD/MM/YYYY."""
    return d.strftime("%d/%m/%Y")


def format_date_short(d: date) -> str:
    """Format date as DD/MM."""
    return d.strftime("%d/%m")


def month_name(month: int) -> str:
    """Get Vietnamese month name."""
    return f"Tháng {month}"


def format_payment_method(method: str) -> str:
    """Get display name for payment method."""
    from src.utils.constants import PAYMENT_METHODS
    info = PAYMENT_METHODS.get(method, {})
    return f"{info.get('emoji', '💵')} {info.get('name', 'Tiền mặt')}"


def truncate(text: str, max_len: int = 30) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "…"
