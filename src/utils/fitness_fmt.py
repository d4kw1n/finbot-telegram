"""Telegram MarkdownV2 formatting helpers for fitness messages."""
import re


def escape_md(text: str) -> str:
    special = r"_*[]()~`>#+-=|{}.!\\"
    return re.sub(f"([{re.escape(special)}])", r"\\\1", str(text))


def bold(text: str) -> str:
    return f"*{escape_md(text)}*"


def italic(text: str) -> str:
    return f"_{escape_md(text)}_"


def format_profile(data: dict) -> str:
    lines = [
        f"👤 {bold('HỒ SƠ THỂ HÌNH')}",
        "",
        f"📏 Chiều cao: {bold(str(data['height']))} cm",
        f"⚖️ Cân nặng: {bold(str(data['weight']))} kg",
        f"🎂 Tuổi: {bold(str(data['age']))}",
        f"📊 BMI: {bold(str(data['bmi']))} \\({escape_md(data['bmi_category'])}\\)",
        "",
        f"🔥 {bold('CHỈ SỐ DINH DƯỠNG')}",
        f"  TDEE: {bold(str(data['tdee']))} kcal",
        f"  Mục tiêu: {bold(str(data['daily_calories']))} kcal/ngày",
        f"  🥩 Protein: {bold(str(data['protein']))}g",
        f"  🍚 Carbs: {bold(str(data['carbs']))}g",
        f"  🥑 Fat: {bold(str(data['fat']))}g",
        "",
        f"🎯 Cân nặng mục tiêu: {bold(str(data.get('target_weight', 'N/A')))} kg",
    ]
    return "\n".join(lines)


def format_workout(day_type: str, exercises: list[dict],
                   day_info: dict | None = None) -> str:
    day_labels = {
        "push": "💪 PUSH — Ngực, Vai, Tay sau",
        "pull": "🏋️ PULL — Lưng, Tay trước",
        "legs": "🦵 LEGS — Chân, Mông",
        "rest": "😴 NGÀY NGHỈ — Hồi phục",
    }
    header = day_labels.get(day_type, day_type.upper())
    lines = [bold(header), ""]

    if day_type == "rest":
        lines.append("Hôm nay là ngày nghỉ\\. Hãy nghỉ ngơi, stretching nhẹ,")
        lines.append("uống đủ nước và ngủ đủ giấc nhé\\! 💤")
        return "\n".join(lines)

    if day_info:
        duration = day_info.get("estimated_duration_min", 0)
        muscles = day_info.get("target_muscles", [])
        if duration:
            lines.append(
                f"⏱ Thời lượng: ~{bold(f'{duration + 15}')} phút "
                f"\\(cả khởi động\\)")
        if muscles:
            lines.append(
                f"🎯 Cơ mục tiêu: {escape_md(', '.join(muscles))}")
        lines.append("")

    total_sets = 0
    for i, ex in enumerate(exercises, 1):
        name = escape_md(ex["name"])
        cat = "🔴" if ex.get("category") == "compound" else "🔵"
        sets = str(ex["sets"])
        reps = escape_md(str(ex["reps"]))
        rest = escape_md(ex.get("rest", "90s"))
        total_sets += ex["sets"]

        weight_hint = ""
        if ex.get("suggested_start_weight"):
            weight_hint = (
                f"  🏋️ Gợi ý: {escape_md(ex['suggested_start_weight'])}")

        lines.append(f"{cat} {i}\\. {bold(name)}")
        lines.append(
            f"   {escape_md(sets)} sets × {reps} reps \\| Nghỉ: {rest}")
        if weight_hint:
            lines.append(weight_hint)
        if ex.get("note"):
            lines.append(f"   💡 {italic(ex['note'])}")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append(
        f"📊 Tổng: {bold(str(total_sets))} sets \\| "
        f"🔴 Compound \\+ 🔵 Isolation")
    lines.append("📖 /exercise \\<số\\> — xem kỹ thuật chi tiết")
    lines.append("📚 /guide — hướng dẫn khởi động \\& tempo")

    return "\n".join(lines)


def format_meal(meal_type: str, meal: dict) -> str:
    cost = meal.get("cost_vnd", 0)
    cost_str = ""
    if cost:
        cost_fmt = f"{cost:,}".replace(",", ".")
        cost_str = f" \\~{escape_md(cost_fmt)}đ"

    lines = [
        bold(f"{meal.get('emoji', '🍽')} {meal['label']}") + cost_str,
        "",
    ]
    for item in meal.get("items", []):
        lines.append(f"  • {escape_md(item)}")
    lines.append("")
    lines.append(
        f"📊 \\~{escape_md(str(meal.get('calories', '?')))} kcal "
        f"\\| P: {escape_md(str(meal.get('protein', '?')))}g "
        f"\\| C: {escape_md(str(meal.get('carbs', '?')))}g "
        f"\\| F: {escape_md(str(meal.get('fat', '?')))}g")
    return "\n".join(lines)


def format_daily_summary(meals_done: int, meals_total: int,
                         water_ml: int, workout_done: bool) -> str:
    workout_status = "✅ Đã tập" if workout_done else "❌ Chưa tập"
    lines = [
        bold("📋 TỔNG KẾT THỂ HÌNH HÔM NAY"),
        "",
        f"🍽 Bữa ăn: {bold(f'{meals_done}/{meals_total}')}",
        f"💧 Nước: {bold(f'{water_ml}ml')} / 3000ml",
        f"🏋️ Tập luyện: {bold(workout_status)}",
    ]
    return "\n".join(lines)


def format_progress_chart_caption(current: float, start: float,
                                  target: float) -> str:
    gained = round(current - start, 1)
    remaining = round(target - current, 1)
    pct = round((gained / max(target - start, 0.1)) * 100, 1)
    lines = [
        bold("📈 TIẾN TRÌNH CỦA BẠN"),
        "",
        f"Bắt đầu: {bold(str(start))} kg",
        f"Hiện tại: {bold(str(current))} kg "
        f"\\(\\+{escape_md(str(gained))}\\)",
        f"Mục tiêu: {bold(str(target))} kg",
        f"Hoàn thành: {bold(f'{pct}%')}",
        f"Còn lại: {bold(str(remaining))} kg",
    ]
    return "\n".join(lines)
