"""Fitness: /ask — AI fitness coach with user context."""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.database import get_settings
from src.services.ai_service import is_available
from src.services.ai_coach_service import ask_fitness_ai, get_provider_info


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args) if context.args else ""
    if not question:
        info = get_provider_info()
        await update.message.reply_text(
            f"🤖 *AI Fitness Coach*\n\n"
            f"{info}\n\n"
            f"Ví dụ:\n"
            f"  /ask Tôi nên ăn gì trước khi tập?\n"
            f"  /ask Cách tăng bench press?\n"
            f"  /ask Tôi bị đau vai khi OHP\n"
            f"  /ask Creatine uống như nào?\n"
            f"  /ask Tôi chán tập rồi, làm sao?",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text("🤔 Đang suy nghĩ...")

    settings = await get_settings()
    user_context = None
    if settings.get("fitness_onboarding_complete"):
        user_context = {
            "weight": settings.get("weight"),
            "height": settings.get("height"),
            "age": settings.get("age"),
            "target_weight": settings.get("target_weight"),
            "tdee": settings.get("tdee"),
            "daily_calories": settings.get("daily_calories"),
        }

    answer = await ask_fitness_ai(question, user_context)
    await update.message.reply_text(
        f"🤖 *AI Coach:*\n\n{answer}", parse_mode="Markdown")


def get_ai_coach_handlers() -> list:
    return [CommandHandler("ask", ask_command)]
