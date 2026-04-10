"""/report command — financial reports with charts.

Provides:
  - Monthly summary report with AI insights
  - Pie chart (spending by category)
  - Bar chart (spending by category)
  - Trend chart (daily spending)
"""
import os
import logging
import re
from datetime import date, timedelta

from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from src.database import (
    get_settings, get_spending_summary, get_category_spending,
    get_type_spending, get_daily_spending
)
from src.services import ai_service
from src.services.chart_service import (
    create_pie_chart, create_bar_chart, create_trend_chart
)
from src.utils.formatter import format_currency, format_date, percentage
from src.bot.keyboards.inline import report_period_picker

logger = logging.getLogger(__name__)


def _escape_markdown(text: str) -> str:
    """Escape special Markdown characters in AI-generated text."""
    # Only escape unmatched special chars to preserve intentional formatting
    # Remove problematic chars that AI might generate
    special = ['_', '*', '`', '[']
    for ch in special:
        # Count occurrences — if odd (unmatched), escape all
        if text.count(ch) % 2 != 0:
            text = text.replace(ch, f'\\{ch}')
    return text


async def _safe_reply(message, text: str, **kwargs):
    """Send message with Markdown, fallback to plain text on parse error."""
    try:
        await message.reply_text(text, parse_mode="Markdown", **kwargs)
    except Exception:
        # Strip all Markdown formatting and send as plain text
        clean = text.replace('*', '').replace('_', '').replace('`', '')
        await message.reply_text(clean, **kwargs)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show monthly report with summary and chart options."""
    today = date.today()
    month_start = today.replace(day=1)

    summary = await get_spending_summary(month_start, today)
    type_spending = await get_type_spending(month_start, today)
    settings = await get_settings()
    income = settings.get("monthly_income", 0)

    # Calculate savings rate
    savings = summary["total_income"] - summary["total_expense"]
    savings_rate = (savings / summary["total_income"] * 100) if summary["total_income"] > 0 else 0

    text = (
        f"📊 *BÁO CÁO THÁNG {today.month}/{today.year}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Thu nhập:  {format_currency(summary['total_income'])}\n"
        f"💸 Chi tiêu:  {format_currency(summary['total_expense'])}\n"
    )

    if savings >= 0:
        text += f"💚 Tiết kiệm: {format_currency(savings)} ({savings_rate:.1f}%)"
        if savings_rate >= 20:
            text += " ✅"
    else:
        text += f"🔴 Thâm hụt: {format_currency(abs(savings))}"

    text += (
        f"\n📊 Số GD: {summary['tx_count']}\n\n"
        f"*Phân bổ chi tiêu:*\n"
        f"  💡 Nhu cầu:  {format_currency(type_spending['need'], True)}\n"
        f"  🎮 Mong muốn: {format_currency(type_spending['want'], True)}\n"
        f"  💰 Tiết kiệm: {format_currency(type_spending['saving'], True)}\n"
    )

    # AI Insights
    if ai_service.is_available():
        insight_data = {
            "month": f"{today.month}/{today.year}",
            "income": summary["total_income"],
            "expense": summary["total_expense"],
            "savings": savings,
            "savings_rate": f"{savings_rate:.1f}%",
            "needs": type_spending["need"],
            "wants": type_spending["want"],
            "saving_investment": type_spending["saving"],
            "monthly_income_setting": income,
            "transaction_count": summary["tx_count"],
        }

        cat_spending = await get_category_spending(month_start, today)
        insight_data["top_categories"] = [
            {"name": c["name"], "amount": c["total_spent"]}
            for c in cat_spending[:5]
        ]

        text += "\n🤖 *Phân tích AI:*\n"
        insight = await ai_service.get_financial_insight(insight_data)
        text += _escape_markdown(insight)

    await _safe_reply(
        update.message, text,
        reply_markup=report_period_picker()
    )


async def handle_chart_callback(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    """Handle chart generation callbacks."""
    query = update.callback_query
    await query.answer("📊 Đang tạo biểu đồ...")

    today = date.today()
    month_start = today.replace(day=1)
    chart_type = query.data

    chart_path = None
    try:
        if chart_type == "chart_pie":
            cat_spending = await get_category_spending(month_start, today)
            if not cat_spending:
                await query.message.reply_text("📭 Chưa có dữ liệu chi tiêu.")
                return

            data = {
                f"{c['emoji']} {c['name']}": c["total_spent"]
                for c in cat_spending[:10]
            }
            chart_path = create_pie_chart(
                data, f"Chi tiêu tháng {today.month}/{today.year}"
            )

        elif chart_type == "chart_bar":
            cat_spending = await get_category_spending(month_start, today)
            if not cat_spending:
                await query.message.reply_text("📭 Chưa có dữ liệu chi tiêu.")
                return

            data = {
                f"{c['emoji']} {c['name']}": c["total_spent"]
                for c in cat_spending[:8]
            }
            chart_path = create_bar_chart(
                data, f"Chi tiêu tháng {today.month}/{today.year}",
                horizontal=True
            )

        elif chart_type == "chart_trend":
            # Last 30 days
            start = today - timedelta(days=29)
            daily = await get_daily_spending(start, today)

            if not daily:
                await query.message.reply_text("📭 Chưa có dữ liệu chi tiêu.")
                return

            dates = [d["transaction_date"][-5:] for d in daily]  # MM-DD
            values = [d["total"] for d in daily]
            chart_path = create_trend_chart(
                dates, values, "Xu hướng chi tiêu 30 ngày gần nhất"
            )

        if chart_path:
            with open(chart_path, 'rb') as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=f"📊 Biểu đồ tháng {today.month}/{today.year}"
                )
            os.unlink(chart_path)

    except Exception as e:
        logger.error(f"Chart error: {e}")
        await query.message.reply_text(
            f"⚠️ Lỗi tạo biểu đồ: {str(e)}"
        )


# ═══════════════════════════════════════════════════════════════════════
# /advice — AI financial advice
# ═══════════════════════════════════════════════════════════════════════

async def advice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get AI financial advice."""
    question = " ".join(context.args) if context.args else ""

    if not question:
        await update.message.reply_text(
            "🤖 *Tư Vấn Tài Chính AI*\n\n"
            "Hãy đặt câu hỏi về tài chính cá nhân:\n\n"
            "Ví dụ:\n"
            "• `/advice Làm sao tiết kiệm được 20% thu nhập?`\n"
            "• `/advice Nên đầu tư gì với 5 triệu/tháng?`\n"
            "• `/advice Có nên mua nhà trả góp không?`",
            parse_mode="Markdown"
        )
        return

    await update.message.reply_text("🤖 Đang suy nghĩ...")

    # Build context
    today = date.today()
    month_start = today.replace(day=1)
    settings = await get_settings()
    summary = await get_spending_summary(month_start, today)

    ctx = {
        "monthly_income": settings.get("monthly_income", 0),
        "this_month_expense": summary["total_expense"],
        "this_month_income": summary["total_income"],
        "budget_ratio": f"{settings.get('budget_needs_pct', 50)}/"
                       f"{settings.get('budget_wants_pct', 30)}/"
                       f"{settings.get('budget_savings_pct', 20)}",
    }

    answer = await ai_service.get_advice(question, ctx)
    await _safe_reply(
        update.message,
        f"🤖 *Tư vấn:*\n\n{_escape_markdown(answer)}"
    )


def get_report_handlers() -> list:
    """Get report-related handlers."""
    return [
        CommandHandler("report", report_command),
        CommandHandler("advice", advice_command),
        CallbackQueryHandler(handle_chart_callback,
                             pattern=r"^chart_(pie|bar|trend)$"),
    ]
