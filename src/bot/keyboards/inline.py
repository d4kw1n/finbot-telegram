"""Inline keyboard builders for the Telegram bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def category_picker(categories: list[dict], tx_id: int | None = None,
                    prefix: str = "cat") -> InlineKeyboardMarkup:
    """Build a category selection keyboard.

    Args:
        categories: List of category dicts
        tx_id: If set, callback_data includes tx_id for updating
        prefix: Callback data prefix
    """
    keyboard = []
    row = []
    for cat in categories:
        cb = f"{prefix}_{cat['id']}"
        if tx_id is not None:
            cb = f"{prefix}_{tx_id}_{cat['id']}"
        row.append(InlineKeyboardButton(
            f"{cat['emoji']} {cat['name']}", callback_data=cb
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)


def transaction_actions(tx_id: int) -> InlineKeyboardMarkup:
    """Build action buttons for a recorded transaction."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Đổi danh mục",
                                 callback_data=f"txchcat_{tx_id}"),
            InlineKeyboardButton("🗑 Xóa",
                                 callback_data=f"txdel_{tx_id}"),
        ]
    ])


def confirm_delete(tx_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for deletion."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Xác nhận xóa",
                                 callback_data=f"txdelconfirm_{tx_id}"),
            InlineKeyboardButton("❌ Hủy",
                                 callback_data=f"txdelcancel_{tx_id}"),
        ]
    ])


def budget_type_picker() -> InlineKeyboardMarkup:
    """Pick budget view type: by category type or by category."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💡 Nhu cầu", callback_data="budgettype_need"),
            InlineKeyboardButton("🎮 Mong muốn", callback_data="budgettype_want"),
            InlineKeyboardButton("💰 Tiết kiệm", callback_data="budgettype_saving"),
        ],
        [InlineKeyboardButton("📊 Tổng quan", callback_data="budgettype_all")]
    ])


def report_period_picker() -> InlineKeyboardMarkup:
    """Pick report period."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Tháng này", callback_data="report_month"),
            InlineKeyboardButton("📅 Tuần này", callback_data="report_week"),
        ],
        [
            InlineKeyboardButton("📊 Biểu đồ tròn", callback_data="chart_pie"),
            InlineKeyboardButton("📈 Biểu đồ cột", callback_data="chart_bar"),
        ],
        [
            InlineKeyboardButton("📉 Xu hướng", callback_data="chart_trend"),
        ]
    ])


def goal_actions(goal_id: int) -> InlineKeyboardMarkup:
    """Action buttons for a savings goal."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 Nạp tiền",
                                 callback_data=f"goaladd_{goal_id}"),
            InlineKeyboardButton("🗑 Xóa",
                                 callback_data=f"goaldel_{goal_id}"),
        ]
    ])


def income_options() -> InlineKeyboardMarkup:
    """Income level picker for onboarding."""
    from src.utils.formatter import format_currency
    options = [5_000_000, 10_000_000, 15_000_000,
               20_000_000, 30_000_000, 50_000_000]
    keyboard = []
    row = []
    for inc in options:
        row.append(InlineKeyboardButton(
            format_currency(inc, short=True),
            callback_data=f"income_{inc}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(
        "✏️ Nhập tay", callback_data="income_custom"
    )])
    return InlineKeyboardMarkup(keyboard)


def budget_style_picker() -> InlineKeyboardMarkup:
    """Budget style for onboarding."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Dùng 50/30/20",
                              callback_data="budget_default")],
        [InlineKeyboardButton("✏️ Tùy chỉnh tỷ lệ",
                              callback_data="budget_custom")],
    ])
