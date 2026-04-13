"""Reminder service — daily finance summary + fitness reminders.

Uses APScheduler (bundled with python-telegram-bot) to schedule jobs.
"""
import logging
from datetime import date, time as dt_time

from telegram.ext import Application

from src.database import get_settings, get_spending_summary, get_today_water, get_today_nutrition, did_workout_today
from src.config import FITNESS_REMINDER_SCHEDULE

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

    if summary["tx_count"] == 0:
        text = (
            "🌙 *Nhắc nhở cuối ngày*\n\n"
            "📭 Hôm nay chưa ghi giao dịch nào.\n"
            "Bạn có quên ghi chi tiêu không?\n\n"
            "💡 Gửi tin nhắn như `ăn phở 50k` để ghi nhanh!"
        )
    else:
        from src.utils.formatter import format_currency

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

    if settings.get("fitness_onboarding_complete"):
        nutrition = await get_today_nutrition()
        water = await get_today_water()
        workout_done = await did_workout_today()
        target_cal = int(settings.get("daily_calories") or 0)

        text += "\n\n🏋️ *Thể hình hôm nay:*\n"
        text += f"  🍽 Bữa ăn: {nutrition['meals_done']}\n"
        text += f"  💧 Nước: {water}ml / 3000ml\n"
        cal = int(nutrition['calories'])
        text += f"  🔥 Calories: {cal} / {target_cal}\n"
        text += f"  🏋️ Tập luyện: {'✅' if workout_done else '❌'}"

    try:
        await context.bot.send_message(
            chat_id=telegram_id, text=text, parse_mode="Markdown")
        logger.info("📨 Daily reminder sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")


async def _send_fitness_reminder(context):
    """Send a fitness reminder (meal, workout, etc.)."""
    settings = await get_settings()
    if not settings.get("fitness_reminders_enabled"):
        return

    telegram_id = settings.get("telegram_id")
    if not telegram_id:
        return

    label = context.job.data.get("label", "Nhắc nhở")
    key = context.job.data.get("key", "")

    if "workout" in key:
        msg = (
            f"⏰ {label}\n\n"
            "Đã đến giờ tập rồi! 🏋️\n"
            "Gõ /workout để xem bài tập hôm nay\n"
            "Gõ /guide để xem hướng dẫn khởi động"
        )
    elif "sleep" in key:
        msg = f"⏰ {label}\n\n Hãy đi ngủ sớm để cơ bắp hồi phục! 😴"
    elif "log_progress" in key:
        msg = (
            f"⏰ {label}\n\n"
            "Ghi nhận tiến trình cuối ngày:\n"
            "• /weight <kg> — Ghi cân nặng\n"
            "• /water <ml> — Ghi nước uống\n"
            "• /fittoday — Xem tổng kết"
        )
    else:
        msg = (
            f"⏰ {label}\n\n"
            "Đã đến giờ ăn! 🍽\n"
            "Gõ /meal để xem menu hôm nay"
        )

    try:
        await context.bot.send_message(chat_id=telegram_id, text=msg)
    except Exception as e:
        logger.error(f"Fitness reminder error: {e}")


def setup_daily_reminder(app: Application):
    """Schedule all reminders."""
    import asyncio

    async def _schedule():
        settings = await get_settings()

        # Finance daily reminder
        reminder_time_str = settings.get("reminder_time", "21:00")
        try:
            parts = reminder_time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            hour, minute = 21, 0

        existing = app.job_queue.get_jobs_by_name("daily_reminder")
        for job in existing:
            job.schedule_removal()

        import pytz
        tz = pytz.timezone("Asia/Ho_Chi_Minh")

        app.job_queue.run_daily(
            _send_daily_reminder,
            time=dt_time(hour=hour, minute=minute, tzinfo=tz),
            name="daily_reminder",
        )
        logger.info(f"⏰ Daily reminder scheduled at {hour:02d}:{minute:02d}")

        # Fitness reminders
        if settings.get("fitness_reminders_enabled") and settings.get("fitness_onboarding_complete"):
            for key, cfg in FITNESS_REMINDER_SCHEDULE.items():
                job_name = f"fit_{key}"
                existing = app.job_queue.get_jobs_by_name(job_name)
                for job in existing:
                    job.schedule_removal()

                app.job_queue.run_daily(
                    _send_fitness_reminder,
                    time=dt_time(hour=cfg["hour"], minute=cfg["minute"], tzinfo=tz),
                    name=job_name,
                    data={"key": key, "label": cfg["label"]},
                )
            logger.info(f"⏰ {len(FITNESS_REMINDER_SCHEDULE)} fitness reminders scheduled")

    loop = asyncio.get_event_loop()
    loop.create_task(_schedule())
