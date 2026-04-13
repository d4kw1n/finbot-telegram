"""Fitness: /exercise — detailed exercise guide, /guide — warmup & tempo."""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.database import get_settings
from src.services.workout_service import load_program, get_today_workout
from src.utils.fitness_fmt import escape_md, bold, italic


async def exercise_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = await get_settings()
    if not settings.get("fitness_onboarding_complete"):
        await update.message.reply_text("❌ Gõ /start trước!")
        return

    program = load_program(settings.get("current_program") or "ppl")
    day_type, exercises = get_today_workout(
        program, settings.get("workout_day_index") or 0)

    if day_type == "rest":
        await update.message.reply_text(
            "😴 Hôm nay ngày nghỉ! Không có bài tập để xem.")
        return

    query = " ".join(context.args).strip() if context.args else ""

    if not query:
        lines = [f"📖 {bold('HƯỚNG DẪN BÀI TẬP')}", ""]
        lines.append(f"Hôm nay: {bold(day_type.upper())}")
        lines.append("")
        for i, ex in enumerate(exercises, 1):
            name_vi = ex.get("name_vi", "")
            display = f"{ex['name']}"
            if name_vi:
                display += f" \\({escape_md(name_vi)}\\)"
            cat = "🔴" if ex.get("category") == "compound" else "🔵"
            lines.append(f"{cat} {i}\\. {escape_md(display)}")
        lines.append("")
        lines.append("Gõ /exercise \\<số\\> để xem hướng dẫn chi tiết")
        lines.append("Ví dụ: /exercise 1")
        await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")
        return

    exercise = _find_exercise(exercises, query)
    if not exercise:
        await update.message.reply_text(
            f"❌ Không tìm thấy bài tập '{query}'.\n"
            f"Gõ /exercise để xem danh sách.")
        return

    text = _format_exercise_detail(exercise)
    await update.message.reply_text(text, parse_mode="MarkdownV2")


async def guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    program = load_program("ppl")

    warmup = program.get("warmup", {})
    cooldown = program.get("cooldown", {})
    tempo = program.get("tempo_guide", {})
    overload = program.get("progressive_overload_guide", {})

    lines = [f"📚 {bold('HƯỚNG DẪN TẬP GYM')}", ""]

    lines.append(
        f"🔥 {bold('KHỞI ĐỘNG')} "
        f"\\(~{warmup.get('duration_min', 10)} phút\\)")
    for step in warmup.get("steps", []):
        lines.append(f"  • {escape_md(step)}")
    lines.append("")

    lines.append(
        f"🧊 {bold('HẠ NHIỆT')} "
        f"\\(~{cooldown.get('duration_min', 5)} phút\\)")
    for step in cooldown.get("steps", []):
        lines.append(f"  • {escape_md(step)}")
    lines.append("")

    lines.append(f"⏱ {bold('TEMPO')}")
    lines.append(f"  Format: {escape_md(tempo.get('format', ''))}")
    lines.append(f"  VD: {escape_md(tempo.get('example', ''))}")
    lines.append(f"  💡 {italic(tempo.get('why', ''))}")
    lines.append("")

    lines.append(f"📈 {bold('PROGRESSIVE OVERLOAD')}")
    for rule in overload.get("rules", []):
        lines.append(f"  • {escape_md(rule)}")
    lines.append("")

    lines.append("🔴 Compound \\= bài đa khớp \\(nặng, ít rep\\)")
    lines.append("🔵 Isolation \\= bài đơn khớp \\(nhẹ, nhiều rep\\)")

    await update.message.reply_text("\n".join(lines), parse_mode="MarkdownV2")


def _find_exercise(exercises: list[dict], query: str) -> dict | None:
    try:
        idx = int(query) - 1
        if 0 <= idx < len(exercises):
            return exercises[idx]
    except ValueError:
        pass
    q = query.lower()
    for ex in exercises:
        if q in ex["name"].lower() or q in ex.get("name_vi", "").lower():
            return ex
    return None


def _format_exercise_detail(ex: dict) -> str:
    cat_emoji = "🔴 Compound" if ex.get("category") == "compound" else "🔵 Isolation"
    name_vi = ex.get("name_vi", "")

    lines = [f"💪 {bold(ex['name'])}"]
    if name_vi:
        lines.append(f"_{escape_md(name_vi)}_")
    lines.append(f"{escape_md(cat_emoji)}")
    lines.append("")

    primary = ", ".join(ex.get("primary_muscles", []))
    secondary = ", ".join(ex.get("secondary_muscles", []))
    lines.append(f"🎯 {bold('Cơ chính')}: {escape_md(primary)}")
    if secondary:
        lines.append(f"   Cơ phụ: {escape_md(secondary)}")
    lines.append("")

    lines.append(f"📊 {bold('SET/REP')}")
    lines.append(
        f"  Sets: {bold(str(ex['sets']))} \\| "
        f"Reps: {bold(str(ex['reps']))}")
    lines.append(f"  Nghỉ: {escape_md(ex.get('rest', '90s'))}")
    if ex.get("tempo"):
        lines.append(f"  Tempo: {escape_md(ex['tempo'])}")
    lines.append("")

    if ex.get("suggested_start_weight"):
        lines.append(
            f"🏋️ {bold('Cân nặng gợi ý')}: "
            f"{escape_md(ex['suggested_start_weight'])}")
        lines.append("")

    if ex.get("technique"):
        lines.append(f"📝 {bold('KỸ THUẬT')}")
        for i, step in enumerate(ex["technique"], 1):
            lines.append(f"  {i}\\. {escape_md(step)}")
        lines.append("")

    if ex.get("common_mistakes"):
        lines.append(f"❌ {bold('LỖI THƯỜNG GẶP')}")
        for mistake in ex["common_mistakes"]:
            lines.append(f"  • {escape_md(mistake)}")
        lines.append("")

    if ex.get("note"):
        lines.append(f"💡 {italic(ex['note'])}")

    return "\n".join(lines)


def get_exercise_handlers() -> list:
    return [
        CommandHandler("exercise", exercise_command),
        CommandHandler("guide", guide_command),
    ]
