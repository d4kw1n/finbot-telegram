"""Bot application — assembles all handlers and runs the bot."""
import logging

from telegram.ext import Application

from src.config import BOT_TOKEN
from src.database import init_db
from src.services.ai_service import init_ai

from src.bot.handlers.start import get_start_handler, get_dashboard_handlers
from src.bot.handlers.transaction import get_transaction_handlers
from src.bot.handlers.budget import get_budget_handlers
from src.bot.handlers.report import get_report_handlers
from src.bot.handlers.goal import get_goal_handlers
from src.bot.handlers.settings import get_settings_handlers
from src.bot.handlers.help import get_help_handler, get_help_callback_handler
from src.bot.handlers.utility import get_utility_handlers

from src.bot.handlers.workout import get_workout_handlers
from src.bot.handlers.meal import get_meal_handlers
from src.bot.handlers.fitness_log import get_fitness_log_handler
from src.bot.handlers.progress import get_progress_handlers
from src.bot.handlers.exercise import get_exercise_handlers
from src.bot.handlers.ai_coach import get_ai_coach_handlers

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database and AI after the application starts."""
    logger.info("🔧 Initializing database...")
    await init_db()
    logger.info("✅ Database ready.")

    logger.info("🤖 Initializing AI service...")
    init_ai()

    logger.info("💱 Fetching live USD/VND exchange rate...")
    from src.services.currency_service import get_usd_to_vnd
    rate = await get_usd_to_vnd()
    logger.info(f"💱 USD/VND = {rate:,.0f}")

    from telegram import BotCommand
    commands = [
        BotCommand("start", "Bắt đầu / Dashboard"),
        BotCommand("today", "Chi tiêu hôm nay"),
        BotCommand("week", "Chi tiêu tuần này"),
        BotCommand("month", "Chi tiêu tháng này"),
        BotCommand("budget", "Xem ngân sách"),
        BotCommand("report", "Báo cáo & biểu đồ"),
        BotCommand("goal", "Mục tiêu tiết kiệm"),
        BotCommand("workout", "🏋️ Bài tập hôm nay"),
        BotCommand("meal", "🍽 Menu ăn hôm nay"),
        BotCommand("log", "📝 Ghi nhận bài tập"),
        BotCommand("weight", "⚖️ Ghi cân nặng"),
        BotCommand("water", "💧 Ghi nước uống"),
        BotCommand("fittoday", "📋 Tổng kết thể hình"),
        BotCommand("progress", "📈 Tiến trình cân nặng"),
        BotCommand("exercise", "📖 Hướng dẫn bài tập"),
        BotCommand("guide", "📚 Hướng dẫn chung"),
        BotCommand("ask", "🤖 Hỏi AI Coach"),
        BotCommand("fitreport", "📊 Báo cáo thể hình tuần"),
        BotCommand("advice", "Tư vấn tài chính AI"),
        BotCommand("search", "Tìm kiếm giao dịch"),
        BotCommand("history", "Giao dịch gần đây"),
        BotCommand("export", "Xuất CSV"),
        BotCommand("backup", "Sao lưu database"),
        BotCommand("undo", "Hoàn tác GD cuối"),
        BotCommand("settings", "Cài đặt"),
        BotCommand("help", "Hướng dẫn sử dụng"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands registered.")

    from src.services.reminder_service import setup_daily_reminder
    setup_daily_reminder(application)


def create_app() -> Application:
    """Create and configure the bot application."""
    from src.config import (
        PROXY_URL, CONNECT_TIMEOUT, READ_TIMEOUT, WRITE_TIMEOUT, POOL_TIMEOUT
    )

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env file!")

    builder = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .connect_timeout(CONNECT_TIMEOUT)
        .read_timeout(READ_TIMEOUT)
        .write_timeout(WRITE_TIMEOUT)
        .pool_timeout(POOL_TIMEOUT)
    )

    if PROXY_URL:
        builder = builder.proxy(PROXY_URL)
        logger.info(f"🌐 Using proxy: {PROXY_URL}")

    app = builder.build()

    # ─── Register Handlers ───────────────────────────────────────────
    # Order matters! ConversationHandlers first, then commands, then NLP.

    # 1. Start/Onboarding conversation
    app.add_handler(get_start_handler())

    # 1b. Dashboard callbacks
    for handler in get_dashboard_handlers():
        app.add_handler(handler)

    # 2. Fitness log conversation (has ConversationHandler)
    app.add_handler(get_fitness_log_handler())

    # 3. Fitness commands (before NLP to avoid conflict)
    for handler in get_workout_handlers():
        app.add_handler(handler)
    for handler in get_meal_handlers():
        app.add_handler(handler)
    for handler in get_progress_handlers():
        app.add_handler(handler)
    for handler in get_exercise_handlers():
        app.add_handler(handler)
    for handler in get_ai_coach_handlers():
        app.add_handler(handler)

    # 4. Budget commands
    for handler in get_budget_handlers():
        app.add_handler(handler)

    # 5. Report commands
    for handler in get_report_handlers():
        app.add_handler(handler)

    # 6. Goal commands
    for handler in get_goal_handlers():
        app.add_handler(handler)

    # 7. Settings commands
    for handler in get_settings_handlers():
        app.add_handler(handler)

    # 8. Help command + navigation callbacks
    app.add_handler(get_help_handler())
    app.add_handler(get_help_callback_handler())

    # 9. Utility commands (export, backup, search)
    for handler in get_utility_handlers():
        app.add_handler(handler)

    # 10. Transaction handlers (NLP handler MUST be last)
    for handler in get_transaction_handlers():
        app.add_handler(handler)

    logger.info("✅ All handlers registered.")

    app.add_error_handler(_error_handler)

    return app


async def _error_handler(update, context):
    """Handle errors gracefully."""
    error = context.error

    from telegram.error import BadRequest
    if isinstance(error, BadRequest):
        msg = str(error).lower()
        if "message is not modified" in msg:
            return
        if "message to edit not found" in msg:
            return

    logger.error(f"Update {update} caused error: {context.error}")
