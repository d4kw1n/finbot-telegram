"""Transaction handler — the core of the bot.

Handles:
  - Natural language input: "ăn phở 50k" → auto-record transaction
  - /add command with guided input
  - /income command for recording income
  - /today, /week, /month summary views
  - /undo to delete the last transaction
  - Inline callbacks for edit/delete/change category
"""
import logging
import os
from datetime import date, timedelta

from telegram import Update
from telegram.ext import (
    ContextTypes, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)

from src.database import (
    get_settings, get_categories, get_category, find_category_by_keywords,
    add_transaction, get_transactions, get_last_transaction,
    delete_transaction, update_transaction,
    get_spending_summary, get_category_spending
)
from src.parsers.nlp_parser import parse_message, has_amount
from src.services import ai_service
from src.utils.formatter import (
    format_currency, format_date, format_payment_method,
    progress_bar, percentage
)
from src.utils.constants import PAYMENT_METHODS, CATEGORY_TYPE_LABELS
from src.bot.keyboards.inline import (
    category_picker, transaction_actions, confirm_delete
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# NLP Message Handler — "ăn phở 50k"
# ═══════════════════════════════════════════════════════════════════════

async def handle_nlp_transaction(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
    """Parse natural language message and record transaction."""
    text = update.message.text.strip()

    # Skip if doesn't look like a transaction
    if not has_amount(text):
        return

    # Check onboarding
    settings = await get_settings()
    if not settings.get("onboarding_complete"):
        return

    # Parse the message
    parsed = parse_message(text)
    if parsed.get("error") or parsed.get("amount") is None:
        return  # Silently ignore non-transaction messages

    amount = parsed["amount"]
    description = parsed["description"]
    tx_type = parsed["type"]
    payment_method = parsed["payment_method"]
    tx_date = parsed["date"]

    # Find category
    category = None
    confidence = 0.0

    if description:
        category, confidence = await find_category_by_keywords(description)

    # If low confidence and AI available, try AI categorization
    if (confidence < 0.5 or category is None) and ai_service.is_available():
        all_cats = await get_categories(
            cat_type="income" if tx_type == "income" else None
        )
        if tx_type != "income":
            all_cats = [c for c in all_cats if c["type"] != "income"]
        else:
            all_cats = [c for c in all_cats if c["type"] == "income"]

        ai_result = await ai_service.categorize_transaction(
            description or text, all_cats
        )
        if ai_result and ai_result.get("confidence", 0) > 50:
            ai_cat = await get_category(ai_result["category_id"])
            if ai_cat:
                category = ai_cat
                confidence = ai_result["confidence"] / 100

    # If still no category, show picker
    if category is None or confidence < 0.4:
        if tx_type == "income":
            cats = await get_categories(cat_type="income")
        else:
            cats = await get_categories()
            cats = [c for c in cats if c["type"] != "income"]

        # Store parsed data for callback
        context.user_data["pending_tx"] = {
            "amount": amount,
            "description": description,
            "type": tx_type,
            "payment_method": payment_method,
            "date": tx_date.isoformat(),
        }

        sign = "+" if tx_type == "income" else "-"
        await update.message.reply_text(
            f"💰 {sign}{format_currency(amount)}\n"
            f"📝 {description or '(không có mô tả)'}\n\n"
            "📂 Chọn danh mục:",
            reply_markup=category_picker(cats, prefix="newcat")
        )
        return

    # Auto-record transaction
    tx_id = await add_transaction(
        category_id=category["id"],
        tx_type=tx_type,
        amount=amount,
        description=description,
        payment_method=payment_method,
        transaction_date=tx_date
    )

    # Build confirmation message
    await _send_tx_confirmation(
        update.message, tx_id, amount, description, category,
        payment_method, tx_date, tx_type
    )


async def _send_tx_confirmation(message, tx_id, amount, description,
                                 category, payment_method, tx_date, tx_type):
    """Send a formatted transaction confirmation."""
    sign = "+" if tx_type == "income" else "-"
    icon = "📥" if tx_type == "income" else "✅"

    # Get today's spending
    today_summary = ""
    if tx_type == "expense":
        today = date.today()
        summary = await get_spending_summary(today, today)
        month_start = today.replace(day=1)
        cat_spending = await get_category_spending(month_start, today)

        today_summary = f"\n💡 Hôm nay đã chi: {format_currency(summary['total_expense'])}"

        # Category monthly progress
        cat_total = 0
        for cs in cat_spending:
            if cs["id"] == category["id"]:
                cat_total = cs["total_spent"]
                break

        if category.get("budget_limit", 0) > 0:
            budget = category["budget_limit"]
            today_summary += (
                f"\n📊 {category['emoji']} {category['name']} tháng này: "
                f"{format_currency(cat_total, True)}/{format_currency(budget, True)} "
                f"({percentage(cat_total, budget)})"
            )

            # Budget warning
            pct = cat_total / budget if budget > 0 else 0
            if pct >= 1.0:
                today_summary += "\n🔴 *VƯỢT NGÂN SÁCH!*"
            elif pct >= 0.8:
                today_summary += "\n⚠️ Sắp hết ngân sách!"

    pay_display = format_payment_method(payment_method)

    text = (
        f"{icon} Đã ghi: {sign}{format_currency(amount)}\n"
        f"{category['emoji']} {category['name']} | {pay_display}\n"
        f"📅 {format_date(tx_date)}"
    )
    if description:
        text += f"\n📝 {description}"
    text += today_summary

    await message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=transaction_actions(tx_id)
    )


# ═══════════════════════════════════════════════════════════════════════
# Category selection callback (for pending transactions)
# ═══════════════════════════════════════════════════════════════════════

async def handle_new_category_callback(update: Update,
                                        context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection for a new transaction."""
    query = update.callback_query
    await query.answer()

    cat_id = int(query.data.split("_")[-1])
    pending = context.user_data.pop("pending_tx", None)
    if not pending:
        await query.edit_message_text("⚠️ Dữ liệu đã hết hạn. Vui lòng ghi lại.")
        return

    category = await get_category(cat_id)
    if not category:
        await query.edit_message_text("⚠️ Danh mục không tồn tại.")
        return

    tx_date = date.fromisoformat(pending["date"])
    tx_id = await add_transaction(
        category_id=cat_id,
        tx_type=pending["type"],
        amount=pending["amount"],
        description=pending["description"],
        payment_method=pending["payment_method"],
        transaction_date=tx_date
    )

    sign = "+" if pending["type"] == "income" else "-"
    pay_display = format_payment_method(pending["payment_method"])

    text = (
        f"✅ Đã ghi: {sign}{format_currency(pending['amount'])}\n"
        f"{category['emoji']} {category['name']} | {pay_display}\n"
        f"📅 {format_date(tx_date)}"
    )
    if pending["description"]:
        text += f"\n📝 {pending['description']}"

    await query.edit_message_text(
        text,
        reply_markup=transaction_actions(tx_id)
    )


# ═══════════════════════════════════════════════════════════════════════
# Change category / Delete callbacks
# ═══════════════════════════════════════════════════════════════════════

async def handle_change_category(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
    """Show category picker to change an existing transaction's category."""
    query = update.callback_query
    await query.answer()

    tx_id = int(query.data.split("_")[-1])
    cats = await get_categories()
    cats = [c for c in cats if c["type"] != "income"]

    await query.edit_message_text(
        "📂 Chọn danh mục mới:",
        reply_markup=category_picker(cats, tx_id=tx_id, prefix="chcat")
    )


async def handle_category_changed(update: Update,
                                    context: ContextTypes.DEFAULT_TYPE):
    """Apply category change to a transaction."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    tx_id = int(parts[1])
    cat_id = int(parts[2])

    await update_transaction(tx_id, category_id=cat_id)
    category = await get_category(cat_id)

    await query.edit_message_text(
        f"✅ Đã đổi danh mục → {category['emoji']} {category['name']}",
        reply_markup=transaction_actions(tx_id)
    )


async def handle_delete_request(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    """Show delete confirmation."""
    query = update.callback_query
    await query.answer()

    tx_id = int(query.data.split("_")[-1])
    await query.edit_message_text(
        "⚠️ Bạn có chắc muốn xóa giao dịch này?",
        reply_markup=confirm_delete(tx_id)
    )


async def handle_delete_confirm(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    """Confirm and delete transaction."""
    query = update.callback_query
    await query.answer()

    tx_id = int(query.data.split("_")[-1])
    deleted = await delete_transaction(tx_id)

    if deleted:
        await query.edit_message_text("🗑 Đã xóa giao dịch.")
    else:
        await query.edit_message_text("⚠️ Không tìm thấy giao dịch.")


async def handle_delete_cancel(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    """Cancel deletion."""
    query = update.callback_query
    await query.answer()

    tx_id = int(query.data.split("_")[-1])
    await query.edit_message_text(
        "✅ Đã hủy xóa.",
        reply_markup=transaction_actions(tx_id)
    )


# ═══════════════════════════════════════════════════════════════════════
# /today, /week, /month — Summary commands
# ═══════════════════════════════════════════════════════════════════════

async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's transactions."""
    today = date.today()
    txns = await get_transactions(start_date=today, end_date=today)
    summary = await get_spending_summary(today, today)

    if not txns:
        await update.message.reply_text(
            f"📅 *Hôm nay ({format_date(today)})*\n\n"
            "Chưa có giao dịch nào. Gửi tin nhắn như `ăn phở 50k` để bắt đầu!",
            parse_mode="Markdown"
        )
        return

    text = (
        f"📅 *HÔM NAY — {format_date(today)}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    for tx in txns:
        sign = "+" if tx["type"] == "income" else "-"
        emoji = tx.get("category_emoji", "📦")
        text += (
            f"{emoji} {sign}{format_currency(tx['amount'], True)} "
            f"— {tx.get('description', '') or tx.get('category_name', '')}\n"
        )

    text += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Thu: {format_currency(summary['total_income'], True)} | "
        f"💸 Chi: {format_currency(summary['total_expense'], True)}\n"
        f"📊 Tổng {summary['tx_count']} giao dịch"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show this week's summary."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday

    txns = await get_transactions(start_date=week_start, end_date=today)
    summary = await get_spending_summary(week_start, today)
    cat_spending = await get_category_spending(week_start, today)

    text = (
        f"📅 *TUẦN NÀY ({format_date(week_start)} — {format_date(today)})*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Thu nhập: {format_currency(summary['total_income'])}\n"
        f"💸 Chi tiêu: {format_currency(summary['total_expense'])}\n"
        f"📊 Số GD: {summary['tx_count']}\n\n"
    )

    if cat_spending:
        text += "*Chi tiêu theo danh mục:*\n"
        for cs in cat_spending[:8]:
            text += (
                f"  {cs['emoji']} {cs['name']}: "
                f"{format_currency(cs['total_spent'], True)} "
                f"({cs['tx_count']} GD)\n"
            )

    await update.message.reply_text(text, parse_mode="Markdown")


async def month_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show this month's summary with budget progress."""
    today = date.today()
    month_start = today.replace(day=1)

    summary = await get_spending_summary(month_start, today)
    cat_spending = await get_category_spending(month_start, today)
    settings = await get_settings()

    income = settings.get("monthly_income", 0)
    needs_pct = settings.get("budget_needs_pct", 50)
    wants_pct = settings.get("budget_wants_pct", 30)
    savings_pct = settings.get("budget_savings_pct", 20)

    text = (
        f"📅 *THÁNG {today.month}/{today.year}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Thu nhập: {format_currency(summary['total_income'])}\n"
        f"💸 Chi tiêu: {format_currency(summary['total_expense'])}\n"
        f"💚 Còn lại: {format_currency(summary['net'])}\n"
        f"📊 Số GD: {summary['tx_count']}\n\n"
    )

    if cat_spending:
        text += "*Top chi tiêu:*\n"
        for cs in cat_spending[:10]:
            budget = cs.get("budget_limit", 0)
            if budget > 0:
                bar = progress_bar(cs["total_spent"], budget, 8)
                pct = percentage(cs["total_spent"], budget)
                text += (
                    f"  {cs['emoji']} {cs['name']}: "
                    f"{format_currency(cs['total_spent'], True)}"
                    f"/{format_currency(budget, True)} {bar} {pct}\n"
                )
            else:
                text += (
                    f"  {cs['emoji']} {cs['name']}: "
                    f"{format_currency(cs['total_spent'], True)} "
                    f"({cs['tx_count']} GD)\n"
                )

    # Days remaining advice
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = days_in_month - today.day
    if days_left > 0 and income > 0:
        budget_left = income - summary['total_expense']
        daily_budget = budget_left / days_left if budget_left > 0 else 0
        text += (
            f"\n⏳ Còn {days_left} ngày | "
            f"Nên chi tối đa {format_currency(daily_budget, True)}/ngày"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════════
# /undo — Delete last transaction
# ═══════════════════════════════════════════════════════════════════════

async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete the most recent transaction."""
    last_tx = await get_last_transaction()
    if not last_tx:
        await update.message.reply_text("📭 Không có giao dịch nào để hoàn tác.")
        return

    sign = "+" if last_tx["type"] == "income" else "-"
    emoji = last_tx.get("category_emoji", "📦")
    name = last_tx.get("category_name", "Khác")

    await delete_transaction(last_tx["id"])

    await update.message.reply_text(
        f"↩️ *Đã hoàn tác:*\n"
        f"{emoji} {sign}{format_currency(last_tx['amount'])} — "
        f"{last_tx.get('description', '') or name}\n"
        f"📅 {last_tx['transaction_date']}",
        parse_mode="Markdown"
    )


# ═══════════════════════════════════════════════════════════════════════
# /history — Recent transaction list
# ═══════════════════════════════════════════════════════════════════════

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent transactions."""
    txns = await get_transactions(limit=15)
    if not txns:
        await update.message.reply_text("📭 Chưa có giao dịch nào.")
        return

    text = "📋 *GIAO DỊCH GẦN ĐÂY*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for tx in txns:
        sign = "+" if tx["type"] == "income" else "-"
        emoji = tx.get("category_emoji", "📦")
        desc = tx.get("description", "") or tx.get("category_name", "")
        text += (
            f"📅 {tx['transaction_date']} | "
            f"{emoji} {sign}{format_currency(tx['amount'], True)} "
            f"— {desc}\n"
        )

    await update.message.reply_text(text, parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════════
# Register handlers
# ═══════════════════════════════════════════════════════════════════════

def get_transaction_handlers() -> list:
    """Get all transaction-related handlers."""
    return [
        # Commands
        CommandHandler("today", today_command),
        CommandHandler("week", week_command),
        CommandHandler("month", month_command),
        CommandHandler("undo", undo_command),
        CommandHandler("history", history_command),

        # Callbacks
        CallbackQueryHandler(handle_new_category_callback,
                             pattern=r"^newcat_\d+$"),
        CallbackQueryHandler(handle_change_category,
                             pattern=r"^txchcat_\d+$"),
        CallbackQueryHandler(handle_category_changed,
                             pattern=r"^chcat_\d+_\d+$"),
        CallbackQueryHandler(handle_delete_request,
                             pattern=r"^txdel_\d+$"),
        CallbackQueryHandler(handle_delete_confirm,
                             pattern=r"^txdelconfirm_\d+$"),
        CallbackQueryHandler(handle_delete_cancel,
                             pattern=r"^txdelcancel_\d+$"),

        # NLP handler — MUST be last (catches all text with amounts)
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_nlp_transaction
        ),
    ]
