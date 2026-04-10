"""/budget command — view and manage spending budgets."""
import calendar
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from src.database import (
    get_settings, get_categories, get_category_spending,
    get_type_spending, get_spending_summary
)
from src.utils.formatter import format_currency, progress_bar, percentage
from src.utils.constants import CATEGORY_TYPE_LABELS
from src.bot.keyboards.inline import budget_type_picker


async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show budget overview for current month."""
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = days_in_month - today.day

    settings = await get_settings()
    income = settings.get("monthly_income", 0)
    needs_pct = settings.get("budget_needs_pct", 50)
    wants_pct = settings.get("budget_wants_pct", 30)
    savings_pct = settings.get("budget_savings_pct", 20)

    type_spending = await get_type_spending(month_start, today)
    cat_spending = await get_category_spending(month_start, today)
    summary = await get_spending_summary(month_start, today)

    needs_budget = income * needs_pct / 100
    wants_budget = income * wants_pct / 100
    savings_budget = income * savings_pct / 100

    text = (
        f"📊 *NGÂN SÁCH THÁNG {today.month}/{today.year}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    # Type-level overview
    types_data = [
        ("💡", "NHU CẦU", type_spending["need"], needs_budget, needs_pct),
        ("🎮", "MONG MUỐN", type_spending["want"], wants_budget, wants_pct),
        ("💰", "TIẾT KIỆM", type_spending["saving"], savings_budget, savings_pct),
    ]

    for emoji, label, spent, budget, pct_label in types_data:
        bar = progress_bar(spent, budget)
        pct = percentage(spent, budget)
        status = ""
        if budget > 0:
            ratio = spent / budget
            if ratio >= 1.0:
                status = " 🔴"
            elif ratio >= 0.8:
                status = " ⚠️"

        text += (
            f"{emoji} *{label}* ({pct_label:.0f}% = "
            f"{format_currency(budget, True)})\n"
            f"   {format_currency(spent, True)} / "
            f"{format_currency(budget, True)} "
            f"{bar} {pct}{status}\n"
        )

        # Show categories under each type
        type_key = {"NHU CẦU": "need", "MONG MUỐN": "want",
                    "TIẾT KIỆM": "saving"}[label]
        for cs in cat_spending:
            if cs["type"] == type_key:
                text += (
                    f"   ├ {cs['emoji']} {cs['name']}: "
                    f"{format_currency(cs['total_spent'], True)}\n"
                )
        text += "\n"

    # Footer with daily advice
    total_spent = summary["total_expense"]
    budget_left = income - total_spent
    if days_left > 0 and income > 0:
        daily_budget = max(budget_left / days_left, 0)
        spent_pct = (total_spent / income * 100) if income > 0 else 0
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏳ Còn {days_left} ngày | "
            f"Đã chi: {spent_pct:.0f}% ngân sách\n"
            f"💡 Nên chi tối đa *{format_currency(daily_budget, True)}/ngày*"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


def get_budget_handlers() -> list:
    """Get budget-related handlers."""
    return [
        CommandHandler("budget", budget_command),
    ]
