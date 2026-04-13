"""Fitness: /workout — show today's workout from PPL program."""
import re
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.database import get_settings
from src.services.workout_service import load_program, get_today_workout
from src.utils.fitness_fmt import format_workout, bold, escape_md


async def workout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = await get_settings()
    if not settings.get("fitness_onboarding_complete"):
        await update.message.reply_text(
            "❌ Chưa có hồ sơ thể hình. Gõ /start → chọn thiết lập fitness!")
        return

    program = load_program(settings.get("current_program") or "ppl")
    day_index = settings.get("workout_day_index") or 0
    day_type, exercises = get_today_workout(program, day_index)

    schedule = program["schedule"]
    day_num = day_index % len(schedule) + 1
    day_info = program["days"].get(day_type) if day_type != "rest" else None

    day_labels = {"push": "PUSH", "pull": "PULL", "legs": "LEGS", "rest": "REST"}
    week_parts = []
    for i, d in enumerate(schedule):
        label = day_labels.get(d, d.upper())
        if i == (day_num - 1):
            week_parts.append(f"\\[{bold(label)}\\]")
        else:
            week_parts.append(escape_md(label))

    header = f"📅 {bold(f'Ngày {day_num}/7')}\n"
    header += " ➜ ".join(week_parts) + "\n\n"

    text = header + format_workout(day_type, exercises, day_info)
    await update.message.reply_text(text, parse_mode="MarkdownV2")


def get_workout_handlers() -> list:
    return [CommandHandler("workout", workout_command)]
