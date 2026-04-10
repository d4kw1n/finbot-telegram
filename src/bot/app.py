"""Bot application — assembles all handlers and runs the bot."""
import logging

from telegram.ext import Application

from src.config import BOT_TOKEN
from src.database import init_db
from src.services.ai_service import init_ai

from src.bot.handlers.start import get_start_handler
from src.bot.handlers.transaction import get_transaction_handlers
from src.bot.handlers.budget import get_budget_handlers
from src.bot.handlers.report import get_report_handlers
from src.bot.handlers.goal import get_goal_handlers
from src.bot.handlers.settings import get_settings_handlers
from src.bot.handlers.help import get_help_handler

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database and AI after the application starts."""
    logger.info("🔧 Initializing database...")
    await init_db()
    logger.info("✅ Database ready.")

    logger.info("🤖 Initializing AI service...")
    init_ai()

    # Fetch live exchange rate
    logger.info("💱 Fetching live USD/VND exchange rate...")
    from src.services.currency_service import get_usd_to_vnd
    rate = await get_usd_to_vnd()
    logger.info(f"💱 USD/VND = {rate:,.0f}")

    # Set bot commands for the menu
    from telegram import BotCommand
    commands = [
        BotCommand("start", "Bắt đầu / Dashboard"),
        BotCommand("today", "Chi tiêu hôm nay"),
        BotCommand("week", "Chi tiêu tuần này"),
        BotCommand("month", "Chi tiêu tháng này"),
        BotCommand("budget", "Xem ngân sách"),
        BotCommand("report", "Báo cáo & biểu đồ"),
        BotCommand("goal", "Mục tiêu tiết kiệm"),
        BotCommand("history", "Giao dịch gần đây"),
        BotCommand("undo", "Hoàn tác GD cuối"),
        BotCommand("advice", "Tư vấn tài chính AI"),
        BotCommand("settings", "Cài đặt"),
        BotCommand("help", "Hướng dẫn sử dụng"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands registered.")


def create_app() -> Application:
    """Create and configure the bot application."""
    from src.config import (
        PROXY_URL, CONNECT_TIMEOUT, READ_TIMEOUT, WRITE_TIMEOUT, POOL_TIMEOUT
    )

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set in .env file!")

    # Build application with network settings
    builder = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .connect_timeout(CONNECT_TIMEOUT)
        .read_timeout(READ_TIMEOUT)
        .write_timeout(WRITE_TIMEOUT)
        .pool_timeout(POOL_TIMEOUT)
    )

    # Optional proxy for restricted networks
    if PROXY_URL:
        builder = builder.proxy(PROXY_URL)
        logger.info(f"🌐 Using proxy: {PROXY_URL}")

    app = builder.build()


    # ─── Register Handlers ───────────────────────────────────────────
    # Order matters! ConversationHandler first, then commands, then NLP.

    # 1. Start/Onboarding conversation
    app.add_handler(get_start_handler())

    # 2. Budget commands
    for handler in get_budget_handlers():
        app.add_handler(handler)

    # 3. Report commands
    for handler in get_report_handlers():
        app.add_handler(handler)

    # 4. Goal commands
    for handler in get_goal_handlers():
        app.add_handler(handler)

    # 5. Settings commands
    for handler in get_settings_handlers():
        app.add_handler(handler)

    # 6. Help command
    app.add_handler(get_help_handler())

    # 7. Transaction handlers (NLP handler MUST be last)
    for handler in get_transaction_handlers():
        app.add_handler(handler)

    logger.info("✅ All handlers registered.")

    # Global error handler
    app.add_error_handler(_error_handler)

    return app


async def _error_handler(update, context):
    """Handle errors gracefully."""
    error = context.error

    # Ignore harmless Telegram API errors
    from telegram.error import BadRequest
    if isinstance(error, BadRequest):
        msg = str(error).lower()
        if "message is not modified" in msg:
            return  # User clicked same button twice
        if "message to edit not found" in msg:
            return  # Message was deleted

    logger.error(f"Update {update} caused error: {context.error}")
