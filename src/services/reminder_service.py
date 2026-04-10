"""Daily reminder service — sends end-of-day spending summary.

Uses APScheduler (already bundled with python-telegram-bot) to
schedule a daily message at the configured reminder_time.
"""
import logging
from datetime import date, time as dt_time

from telegram.ext import Application

from src.database import get_settings, get_spending_summary

logger = logging.getLogger(__name__)


async def _send_daily_reminder(context):
    """Send daily spending summary to the user."""
    settings = await get_settings()

    if not settings.get("reminder_enabled"):
        return

    telegram_id = settings.get("telegram_id")
    if not telegram_id:
        return

    today = date.today()
    summary = await get_spending_summary(today, today)

    # Only send if there were transactions today
    if summary["tx_count"] == 0:
        text = (
            "🌙 *Nhắc nhở cuối ngày*\n\n"
            "📭 Hôm nay chưa ghi giao dịch nào.\n"
            "Bạn có quên ghi chi tiêu không?\n\n"
            "💡 Gửi tin nhắn như `ăn phở 50k` để ghi nhanh!"
        )
    else:
        from src.utils.formatter import format_currency

        # Monthly progress
        month_start = today.replace(day=1)
        month_summary = await get_spending_summary(month_start, today)
        income = settings.get("monthly_income", 0)
        remaining = income - month_summary["total_expense"] if income > 0 else 0

        text = (
            "🌙 *Tổng kết hôm nay*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 {summary['tx_count']} giao dịch\n"
            f"💰 Thu: {format_currency(summary['total_income'], True)}\n"
            f"💸 Chi: {format_currency(summary['total_expense'], True)}\n"
        )

        if income > 0:
            import calendar
            days_in_month = calendar.monthrange(today.year, today.month)[1]
            days_left = days_in_month - today.day

            pct = (month_summary["total_expense"] / income * 100
                   if income > 0 else 0)
            text += (
                f"\n📅 Tháng này đã chi: {pct:.0f}% ngân sách\n"
                f"💚 Còn lại: {format_currency(remaining, True)}"
            )
            if days_left > 0 and remaining > 0:
                daily = remaining / days_left
                text += f" ({format_currency(daily, True)}/ngày)"

    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="Markdown"
        )
        logger.info("📨 Daily reminder sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")


def setup_daily_reminder(app: Application):
    """Schedule the daily reminder job.

    Call this in post_init after database is ready.
    """
    import asyncio

    async def _schedule():
        settings = await get_settings()
        reminder_time_str = settings.get("reminder_time", "21:00")
        try:
            parts = reminder_time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            hour, minute = 21, 0

        # Remove existing job if any
        existing = app.job_queue.get_jobs_by_name("daily_reminder")
        for job in existing:
            job.schedule_removal()

        # Schedule daily at configured time (Vietnam timezone)
        import pytz
        tz = pytz.timezone("Asia/Ho_Chi_Minh")

        app.job_queue.run_daily(
            _send_daily_reminder,
            time=dt_time(hour=hour, minute=minute, tzinfo=tz),
            name="daily_reminder",
        )
        logger.info(f"⏰ Daily reminder scheduled at {hour:02d}:{minute:02d}")

    # Run async setup
    loop = asyncio.get_event_loop()
    loop.create_task(_schedule())
