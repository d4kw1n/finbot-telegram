"""/start command and onboarding conversation flow.

Flow:
  1. Welcome → Ask monthly income
  2. Propose 50/30/20 budget split
  3. User confirms or customizes
  4. Onboarding complete → show dashboard
"""
import logging
from datetime import date

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

from src.database import get_settings, update_settings, get_spending_summary, get_type_spending
from src.utils.formatter import format_currency, progress_bar, percentage
from src.parsers.amount_parser import parse_amount
from src.bot.keyboards.inline import income_options, budget_style_picker, dashboard_actions

logger = logging.getLogger(__name__)

# Conversation states
ASK_INCOME, CONFIRM_BUDGET = range(2)


# ═══════════════════════════════════════════════════════════════════════
# /start entry point
# ═══════════════════════════════════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start — begin onboarding or show dashboard."""
    settings = await get_settings()

    if settings.get("onboarding_complete"):
        await _show_dashboard(update)
        return ConversationHandler.END

    # Save user info
    user = update.effective_user
    await update_settings(
        telegram_id=user.id,
        username=user.username or "",
        full_name=user.full_name or ""
    )

    await update.message.reply_text(
        "👋 Chào bạn! Tôi là *FinBot* — trợ lý quản lý tài chính cá nhân.\n\n"
        "Tôi sẽ giúp bạn:\n"
        "• 📝 Ghi chép chi tiêu nhanh chóng\n"
        "• 📊 Phân tích xu hướng tài chính\n"
        "• ⚠️ Cảnh báo khi vượt ngân sách\n"
        "• 🎯 Theo dõi mục tiêu tiết kiệm\n"
        "• 🤖 Tư vấn tài chính bằng AI\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Hãy bắt đầu nhé! 💰\n\n"
        "*Thu nhập hàng tháng* của bạn khoảng bao nhiêu?",
        parse_mode="Markdown",
        reply_markup=income_options()
    )

    return ASK_INCOME


# ═══════════════════════════════════════════════════════════════════════
# Income selection
# ═══════════════════════════════════════════════════════════════════════

async def _income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income selection via inline keyboard."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "income_custom":
        await query.edit_message_text(
            "💰 Nhập thu nhập hàng tháng của bạn (VND):\n\n"
            "Ví dụ: `15000000` hoặc `15tr` hoặc `15m`",
            parse_mode="Markdown"
        )
        return ASK_INCOME

    income = int(data.split("_")[1])
    context.user_data["income"] = income
    await _show_budget_proposal(query.message, income, edit=True)
    return CONFIRM_BUDGET


async def _income_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle income typed as text."""
    amount, _ = parse_amount(update.message.text)
    if not amount or amount <= 0:
        await update.message.reply_text(
            "❌ Không nhận diện được số tiền. Vui lòng nhập lại:\n"
            "Ví dụ: `15000000` hoặc `15tr`",
            parse_mode="Markdown"
        )
        return ASK_INCOME

    context.user_data["income"] = amount
    await _show_budget_proposal(update.message, amount)
    return CONFIRM_BUDGET


# ═══════════════════════════════════════════════════════════════════════
# Budget proposal
# ═══════════════════════════════════════════════════════════════════════

async def _show_budget_proposal(message, income: float, edit: bool = False):
    """Show the 50/30/20 budget breakdown."""
    needs = income * 0.5
    wants = income * 0.3
    savings = income * 0.2

    text = (
        f"✅ Thu nhập: *{format_currency(income)}*/tháng\n\n"
        "📊 *Gợi ý phân bổ theo nguyên tắc 50/30/20:*\n\n"
        f"💡 Nhu cầu thiết yếu (50%): *{format_currency(needs)}*\n"
        f"   _Ăn uống, nhà ở, di chuyển, hóa đơn_\n\n"
        f"🎮 Mong muốn cá nhân (30%): *{format_currency(wants)}*\n"
        f"   _Cafe, giải trí, shopping, du lịch_\n\n"
        f"💰 Tiết kiệm & đầu tư (20%): *{format_currency(savings)}*\n"
        f"   _Tiết kiệm, đầu tư, giáo dục, bảo hiểm_\n"
    )

    if edit:
        await message.edit_text(
            text, parse_mode="Markdown",
            reply_markup=budget_style_picker()
        )
    else:
        await message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=budget_style_picker()
        )


async def _budget_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle budget style selection."""
    query = update.callback_query
    await query.answer()

    income = context.user_data.get("income", 0)

    if query.data == "budget_default":
        await update_settings(
            monthly_income=income,
            budget_needs_pct=50,
            budget_wants_pct=30,
            budget_savings_pct=20,
            onboarding_complete=1
        )

        await query.edit_message_text(
            "🎉 *Thiết lập hoàn tất!*\n\n"
            "Bây giờ bạn có thể bắt đầu ghi chép chi tiêu.\n\n"
            "📝 *Cách ghi nhanh* — chỉ cần gửi tin nhắn:\n"
            "• `ăn phở 50k`\n"
            "• `grab 35000`\n"
            "• `cafe 29k visa`\n"
            "• `+15tr lương` (thu nhập)\n\n"
            "📋 *Lệnh hữu ích:*\n"
            "• /today — Chi tiêu hôm nay\n"
            "• /month — Tổng quan tháng\n"
            "• /budget — Xem ngân sách\n"
            "• /report — Báo cáo chi tiết\n"
            "• /help — Tất cả lệnh\n\n"
            "💡 Gõ /help để xem hướng dẫn đầy đủ!",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    # Custom budget
    await query.edit_message_text(
        "✏️ Nhập tỷ lệ % theo thứ tự: *Nhu cầu / Mong muốn / Tiết kiệm*\n\n"
        "Ví dụ: `60 20 20` hoặc `40 30 30`\n\n"
        "⚠️ Tổng phải bằng 100%",
        parse_mode="Markdown"
    )
    return CONFIRM_BUDGET


async def _custom_budget_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom budget ratio input."""
    text = update.message.text.strip()
    parts = text.replace("/", " ").replace(",", " ").split()

    try:
        needs = float(parts[0])
        wants = float(parts[1])
        savings = float(parts[2])
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Định dạng không đúng. Nhập 3 số, ví dụ: `60 20 20`",
            parse_mode="Markdown"
        )
        return CONFIRM_BUDGET

    if abs(needs + wants + savings - 100) > 0.01:
        await update.message.reply_text(
            f"❌ Tổng = {needs + wants + savings:.0f}%, cần bằng 100%\n"
            "Vui lòng nhập lại:",
        )
        return CONFIRM_BUDGET

    income = context.user_data.get("income", 0)
    await update_settings(
        monthly_income=income,
        budget_needs_pct=needs,
        budget_wants_pct=wants,
        budget_savings_pct=savings,
        onboarding_complete=1
    )

    await update.message.reply_text(
        f"🎉 *Thiết lập hoàn tất!*\n\n"
        f"📊 Tỷ lệ: {needs:.0f}/{wants:.0f}/{savings:.0f}\n"
        f"💡 Nhu cầu: *{format_currency(income * needs / 100)}*\n"
        f"🎮 Mong muốn: *{format_currency(income * wants / 100)}*\n"
        f"💰 Tiết kiệm: *{format_currency(income * savings / 100)}*\n\n"
        "📝 Gửi tin nhắn như `ăn phở 50k` để ghi chi tiêu!\n"
        "💡 Gõ /help để xem hướng dẫn đầy đủ!",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════

async def _show_dashboard(update: Update):
    """Show the main dashboard with monthly overview."""
    today = date.today()
    month_start = today.replace(day=1)

    settings = await get_settings()
    summary = await get_spending_summary(month_start, today)
    type_spending = await get_type_spending(month_start, today)

    income = settings.get("monthly_income", 0)
    needs_pct = settings.get("budget_needs_pct", 50)
    wants_pct = settings.get("budget_wants_pct", 30)
    savings_pct = settings.get("budget_savings_pct", 20)

    needs_budget = income * needs_pct / 100
    wants_budget = income * wants_pct / 100
    savings_budget = income * savings_pct / 100

    name = update.effective_user.first_name
    text = (
        f"👋 Chào, *{name}*!\n\n"
        f"📊 *TỔNG QUAN THÁNG {today.month}/{today.year}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Thu nhập: {format_currency(summary['total_income'])}\n"
        f"💸 Chi tiêu: {format_currency(summary['total_expense'])}\n"
        f"📊 Số GD: {summary['tx_count']}\n\n"
    )

    if income > 0:
        text += (
            f"💡 Nhu cầu: {format_currency(type_spending['need'], True)}"
            f" / {format_currency(needs_budget, True)}\n"
            f"   {progress_bar(type_spending['need'], needs_budget)}"
            f" {percentage(type_spending['need'], needs_budget)}\n"
            f"🎮 Mong muốn: {format_currency(type_spending['want'], True)}"
            f" / {format_currency(wants_budget, True)}\n"
            f"   {progress_bar(type_spending['want'], wants_budget)}"
            f" {percentage(type_spending['want'], wants_budget)}\n"
            f"💰 Tiết kiệm: {format_currency(type_spending['saving'], True)}"
            f" / {format_currency(savings_budget, True)}\n"
            f"   {progress_bar(type_spending['saving'], savings_budget)}"
            f" {percentage(type_spending['saving'], savings_budget)}\n\n"
        )

    text += "📝 Gửi tin nhắn để ghi chi tiêu nhanh!"
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=dashboard_actions()
    )


# ═══════════════════════════════════════════════════════════════════════
# ConversationHandler builder
# ═══════════════════════════════════════════════════════════════════════

def get_start_handler() -> ConversationHandler:
    """Build the /start conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_INCOME: [
                CallbackQueryHandler(_income_callback, pattern=r"^income_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _income_text),
            ],
            CONFIRM_BUDGET: [
                CallbackQueryHandler(_budget_callback, pattern=r"^budget_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               _custom_budget_text),
            ],
        },
        fallbacks=[CommandHandler("start", start_command)],
        allow_reentry=True,
        per_message=False,
    )


async def handle_dashboard_callback(update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
    """Handle dashboard quick action buttons."""
    query = update.callback_query
    await query.answer()

    action = query.data.split("_")[1]
    chat_id = query.message.chat_id

    if action == "report":
        from src.bot.handlers.report import report_command
        # Create a fake update.message from the callback message
        update._effective_message = query.message
        await report_command(update, context)
    elif action == "budget":
        from src.bot.handlers.budget import budget_command
        update._effective_message = query.message
        await budget_command(update, context)
    elif action == "history":
        from src.bot.handlers.transaction import history_command
        update._effective_message = query.message
        await history_command(update, context)
    elif action == "export":
        from src.bot.handlers.utility import export_command
        update._effective_message = query.message
        await export_command(update, context)


def get_dashboard_handlers() -> list:
    """Get dashboard callback handlers (separate from ConversationHandler)."""
    return [
        CallbackQueryHandler(handle_dashboard_callback,
                             pattern=r"^dash_"),
    ]
