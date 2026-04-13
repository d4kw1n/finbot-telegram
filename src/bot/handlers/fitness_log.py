"""Fitness: /log — log workout exercises, /done_workout — finish session."""
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
)

from src.database import (
    get_settings, log_workout, get_exercise_pr, advance_workout_day
)
from src.services.workout_service import load_program, get_today_workout

EXERCISE, WEIGHT_REPS = range(2)


async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    args = context.args
    if args and len(args) >= 3:
        return await _quick_log(update, context, args)

    settings = await get_settings()
    if not settings.get("fitness_onboarding_complete"):
        await update.message.reply_text("❌ Gõ /start trước!")
        return ConversationHandler.END

    program = load_program(settings.get("current_program") or "ppl")
    day_type, exercises = get_today_workout(
        program, settings.get("workout_day_index") or 0)

    if day_type == "rest":
        await update.message.reply_text(
            "😴 Hôm nay là ngày nghỉ! Không cần log bài tập.")
        return ConversationHandler.END

    exercise_list = "\n".join(
        f"  {i}. {ex['name']}" for i, ex in enumerate(exercises, 1))
    await update.message.reply_text(
        f"📝 Bài tập hôm nay ({day_type.upper()}):\n\n"
        f"{exercise_list}\n\n"
        f"Nhập số thứ tự hoặc tên bài tập:")

    context.user_data["log_day_type"] = day_type
    context.user_data["log_exercises"] = exercises
    return EXERCISE


async def receive_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    exercises = context.user_data.get("log_exercises", [])

    exercise_name = None
    try:
        idx = int(text) - 1
        if 0 <= idx < len(exercises):
            exercise_name = exercises[idx]["name"]
    except ValueError:
        for ex in exercises:
            if text.lower() in ex["name"].lower():
                exercise_name = ex["name"]
                break

    if not exercise_name:
        await update.message.reply_text("❌ Không tìm thấy bài tập. Thử lại:")
        return EXERCISE

    context.user_data["log_exercise_name"] = exercise_name
    await update.message.reply_text(
        f"💪 {exercise_name}\n\n"
        f"Nhập: <cân nặng kg> <sets>x<reps>\n"
        f"Ví dụ: 60 4x8")
    return WEIGHT_REPS


async def receive_weight_reps(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    parts = text.split()

    try:
        weight_kg = float(parts[0])
        sets_reps = parts[1] if len(parts) > 1 else "1x1"
        sr = sets_reps.lower().split("x")
        sets = int(sr[0])
        reps = sr[1] if len(sr) > 1 else "1"
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Sai format. Nhập lại: <kg> <sets>x<reps>\nVí dụ: 60 4x8")
        return WEIGHT_REPS

    exercise_name = context.user_data["log_exercise_name"]
    day_type = context.user_data["log_day_type"]

    prev_pr = await get_exercise_pr(exercise_name)

    await log_workout(
        day_type=day_type,
        exercise_name=exercise_name,
        sets=sets, reps=reps, weight_kg=weight_kg,
    )

    reply = f"✅ Đã ghi: {exercise_name} — {weight_kg}kg {sets}x{reps}"
    if prev_pr and weight_kg > prev_pr:
        reply += f"\n\n🎉 KỶ LỤC MỚI! ({prev_pr}kg → {weight_kg}kg)"
    reply += "\n\nTiếp tục /log hoặc /done_workout khi tập xong."
    await update.message.reply_text(reply)
    return ConversationHandler.END


async def done_workout_command(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    await advance_workout_day()
    await update.message.reply_text(
        "🎉 Tuyệt vời! Đã hoàn thành buổi tập hôm nay!\n\n"
        "Đừng quên:\n"
        "🥤 Uống shake post-workout\n"
        "🍽 Ăn bữa tối đầy đủ\n"
        "😴 Ngủ sớm để cơ bắp hồi phục\n\n"
        "💪 Ngày mai tiếp tục chiến!")


async def _quick_log(update: Update, context: ContextTypes.DEFAULT_TYPE,
                     args: list):
    """Quick log: /log bench_press 80 4x8"""
    exercise_name = args[0].replace("_", " ")
    try:
        weight_kg = float(args[1])
        sr = args[2].lower().split("x")
        sets = int(sr[0])
        reps = sr[1]
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Format: /log <tên> <kg> <sets>x<reps>")
        return ConversationHandler.END

    await log_workout(
        day_type="manual", exercise_name=exercise_name,
        sets=sets, reps=reps, weight_kg=weight_kg,
    )
    await update.message.reply_text(
        f"✅ Đã ghi: {exercise_name} — {weight_kg}kg {sets}x{reps} 💪")
    return ConversationHandler.END


async def log_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Đã hủy ghi nhận.")
    return ConversationHandler.END


def get_fitness_log_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("log", log_command)],
        states={
            EXERCISE: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, receive_exercise)],
            WEIGHT_REPS: [MessageHandler(
                filters.TEXT & ~filters.COMMAND, receive_weight_reps)],
        },
        fallbacks=[CommandHandler("cancel", log_cancel)],
    )
