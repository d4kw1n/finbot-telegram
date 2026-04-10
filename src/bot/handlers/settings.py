"""/settings command — manage bot configuration."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler

from src.database import get_settings, update_settings
from src.utils.formatter import format_currency
from src.parsers.amount_parser import parse_amount


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current settings."""
    settings = await get_settings()

    income = settings.get("monthly_income", 0)
    needs = settings.get("budget_needs_pct", 50)
    wants = settings.get("budget_wants_pct", 30)
    savings = settings.get("budget_savings_pct", 20)
    reminder = settings.get("reminder_time", "21:00")
    reminder_on = "✅" if settings.get("reminder_enabled") else "❌"

    text = (
        "⚙️ *CÀI ĐẶT*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Thu nhập: {format_currency(income)}/tháng\n"
        f"📊 Tỷ lệ: {needs:.0f}/{wants:.0f}/{savings:.0f}\n"
        f"   💡 Nhu cầu: {format_currency(income * needs / 100)}\n"
        f"   🎮 Mong muốn: {format_currency(income * wants / 100)}\n"
        f"   💰 Tiết kiệm: {format_currency(income * savings / 100)}\n\n"
        f"⏰ Nhắc nhở: {reminder_on} lúc {reminder}\n\n"
        "*Thay đổi:*\n"
        "• `/setincome <số tiền>` — Đổi thu nhập\n"
        "  Ví dụ: `/setincome 20tr`\n"
        "• `/setratio <N W S>` — Đổi tỷ lệ\n"
        "  Ví dụ: `/setratio 60 20 20`\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def set_income_command(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    """Change monthly income."""
    if not context.args:
        await update.message.reply_text(
            "Cú pháp: `/setincome <số tiền>`\nVí dụ: `/setincome 20tr`",
            parse_mode="Markdown"
        )
        return

    text = " ".join(context.args)
    amount, _ = parse_amount(text)

    if not amount or amount <= 0:
        await update.message.reply_text("❌ Số tiền không hợp lệ.")
        return

    await update_settings(monthly_income=amount)

    settings = await get_settings()
    needs = settings.get("budget_needs_pct", 50)
    wants = settings.get("budget_wants_pct", 30)
    savings = settings.get("budget_savings_pct", 20)

    await update.message.reply_text(
        f"✅ Thu nhập đã cập nhật: *{format_currency(amount)}*/tháng\n\n"
        f"📊 Ngân sách mới:\n"
        f"  💡 Nhu cầu: {format_currency(amount * needs / 100)}\n"
        f"  🎮 Mong muốn: {format_currency(amount * wants / 100)}\n"
        f"  💰 Tiết kiệm: {format_currency(amount * savings / 100)}",
        parse_mode="Markdown"
    )


async def set_ratio_command(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    """Change budget ratio."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "Cú pháp: `/setratio <nhu cầu> <mong muốn> <tiết kiệm>`\n"
            "Ví dụ: `/setratio 60 20 20`\n"
            "⚠️ Tổng phải bằng 100",
            parse_mode="Markdown"
        )
        return

    try:
        needs = float(context.args[0])
        wants = float(context.args[1])
        savings = float(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập 3 số.")
        return

    if abs(needs + wants + savings - 100) > 0.01:
        await update.message.reply_text(
            f"❌ Tổng = {needs + wants + savings:.0f}%, cần bằng 100%"
        )
        return

    await update_settings(
        budget_needs_pct=needs,
        budget_wants_pct=wants,
        budget_savings_pct=savings
    )

    settings = await get_settings()
    income = settings.get("monthly_income", 0)

    await update.message.reply_text(
        f"✅ Tỷ lệ ngân sách đã cập nhật: *{needs:.0f}/{wants:.0f}/{savings:.0f}*\n\n"
        f"  💡 Nhu cầu: {format_currency(income * needs / 100)}\n"
        f"  🎮 Mong muốn: {format_currency(income * wants / 100)}\n"
        f"  💰 Tiết kiệm: {format_currency(income * savings / 100)}",
        parse_mode="Markdown"
    )


def get_settings_handlers() -> list:
    """Get settings-related handlers."""
    return [
        CommandHandler("settings", settings_command),
        CommandHandler("setincome", set_income_command),
        CommandHandler("setratio", set_ratio_command),
    ]
