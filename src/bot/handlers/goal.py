"""/goal command — manage savings goals.

Commands:
  /goal                 — List all active goals
  /goal add <name> <amount> [deadline]  — Create a new goal
  /goal deposit <id> <amount>           — Add money to a goal
"""
import logging
from datetime import date, datetime

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from src.database import get_goals, add_goal, update_goal, delete_goal
from src.parsers.amount_parser import parse_amount
from src.utils.formatter import format_currency, progress_bar, percentage, format_date
from src.bot.keyboards.inline import goal_actions

logger = logging.getLogger(__name__)


async def goal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /goal command with subcommands."""
    args = context.args or []

    if not args:
        await _list_goals(update)
        return

    subcmd = args[0].lower()

    if subcmd == "add" and len(args) >= 3:
        await _add_goal(update, args[1:])
    elif subcmd == "deposit" and len(args) >= 3:
        await _deposit_goal(update, args[1:])
    else:
        await update.message.reply_text(
            "🎯 *Quản Lý Mục Tiêu Tiết Kiệm*\n\n"
            "*Cách dùng:*\n"
            "• `/goal` — Xem tất cả mục tiêu\n"
            "• `/goal add <tên> <số tiền> [thời hạn]`\n"
            "  Ví dụ: `/goal add iPhone 30tr 6`  _(6 tháng)_\n"
            "• `/goal deposit <ID> <số tiền>`\n"
            "  Ví dụ: `/goal deposit 1 5tr`",
            parse_mode="Markdown"
        )


async def _list_goals(update: Update):
    """Show all active savings goals."""
    goals = await get_goals()

    if not goals:
        await update.message.reply_text(
            "🎯 Chưa có mục tiêu nào.\n\n"
            "Tạo mới: `/goal add <tên> <số tiền> [số tháng]`\n"
            "Ví dụ: `/goal add iPhone 30tr 6`",
            parse_mode="Markdown"
        )
        return

    text = "🎯 *MỤC TIÊU TIẾT KIỆM*\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for g in goals:
        pct = g["current_amount"] / g["target_amount"] if g["target_amount"] > 0 else 0
        bar = progress_bar(g["current_amount"], g["target_amount"], 12)

        text += (
            f"{g.get('emoji', '🎯')} *{g['name']}* (ID: {g['id']})\n"
            f"   {format_currency(g['current_amount'], True)} / "
            f"{format_currency(g['target_amount'], True)}\n"
            f"   {bar} {percentage(g['current_amount'], g['target_amount'])}\n"
        )

        if g.get("deadline"):
            try:
                deadline = date.fromisoformat(g["deadline"])
                days_left = (deadline - date.today()).days
                if days_left > 0:
                    remaining = g["target_amount"] - g["current_amount"]
                    monthly = remaining / max(days_left / 30, 1)
                    text += (
                        f"   📅 Hạn: {format_date(deadline)} "
                        f"({days_left} ngày)\n"
                        f"   💡 Cần: {format_currency(monthly, True)}/tháng\n"
                    )
                else:
                    text += "   ⏰ Đã hết hạn!\n"
            except (ValueError, TypeError):
                pass

        text += "\n"

    text += (
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 Nạp tiền: `/goal deposit <ID> <số tiền>`"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def _add_goal(update: Update, args: list):
    """Create a new savings goal."""
    name = args[0]

    amount_text = args[1] if len(args) > 1 else ""
    amount, _ = parse_amount(amount_text)
    if not amount or amount <= 0:
        await update.message.reply_text(
            "❌ Số tiền không hợp lệ.\n"
            "Ví dụ: `/goal add iPhone 30tr 6`",
            parse_mode="Markdown"
        )
        return

    # Optional deadline in months
    deadline = None
    if len(args) > 2:
        try:
            months = int(args[2])
            deadline_date = date.today()
            month = deadline_date.month + months
            year = deadline_date.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            deadline = date(year, month, min(deadline_date.day, 28))
        except (ValueError, TypeError):
            pass

    goal_id = await add_goal(name, amount, deadline)

    text = (
        f"🎯 *Mục tiêu mới!*\n\n"
        f"📌 {name}\n"
        f"💰 Mục tiêu: {format_currency(amount)}\n"
    )

    if deadline:
        days = (deadline - date.today()).days
        monthly = amount / max(days / 30, 1)
        text += (
            f"📅 Hạn: {format_date(deadline)}\n"
            f"💡 Cần tiết kiệm: {format_currency(monthly, True)}/tháng\n"
        )

    text += (
        f"\n{progress_bar(0, amount, 15)} 0%\n\n"
        f"Nạp tiền: `/goal deposit {goal_id} <số tiền>`"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def _deposit_goal(update: Update, args: list):
    """Add money to a savings goal."""
    try:
        goal_id = int(args[0])
    except (ValueError, IndexError):
        await update.message.reply_text("❌ ID mục tiêu không hợp lệ.")
        return

    amount_text = args[1] if len(args) > 1 else ""
    amount, _ = parse_amount(amount_text)
    if not amount or amount <= 0:
        await update.message.reply_text("❌ Số tiền không hợp lệ.")
        return

    goals = await get_goals(active_only=False)
    goal = next((g for g in goals if g["id"] == goal_id), None)

    if not goal:
        await update.message.reply_text(f"❌ Không tìm thấy mục tiêu ID {goal_id}.")
        return

    new_amount = goal["current_amount"] + amount
    is_completed = new_amount >= goal["target_amount"]

    await update_goal(goal_id,
                      current_amount=new_amount,
                      is_completed=1 if is_completed else 0)

    bar = progress_bar(new_amount, goal["target_amount"], 15)
    pct = percentage(new_amount, goal["target_amount"])

    text = (
        f"💰 *Đã nạp {format_currency(amount, True)}* "
        f"vào mục tiêu *{goal['name']}*\n\n"
        f"{format_currency(new_amount, True)} / "
        f"{format_currency(goal['target_amount'], True)}\n"
        f"{bar} {pct}\n"
    )

    if is_completed:
        text += "\n🎉🎉🎉 *HOÀN THÀNH MỤC TIÊU!* 🎉🎉🎉"

    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_goal_delete(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    """Delete a savings goal from callback."""
    query = update.callback_query
    await query.answer()

    goal_id = int(query.data.split("_")[-1])
    await delete_goal(goal_id)
    await query.edit_message_text("🗑 Đã xóa mục tiêu.")


def get_goal_handlers() -> list:
    """Get goal-related handlers."""
    return [
        CommandHandler("goal", goal_command),
        CallbackQueryHandler(handle_goal_delete, pattern=r"^goaldel_\d+$"),
    ]
