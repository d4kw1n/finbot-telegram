"""Fitness: /meal — show daily meal plan, /done_<meal> to log."""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from src.database import (
    get_settings, log_meal_entry, add_transaction, find_category_by_name
)
from src.services.meal_service import load_menu, get_full_day_menu
from src.utils.fitness_fmt import format_meal, bold, escape_md

TIER_LABELS = {"budget": "Tiết kiệm", "standard": "Trung bình", "premium": "Cao cấp"}


def _format_vnd(amount: int) -> str:
    return f"{amount:,}".replace(",", ".")


async def meal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = await get_settings()
    if not settings.get("fitness_onboarding_complete"):
        await update.message.reply_text(
            "❌ Chưa có hồ sơ thể hình. Gõ /start → chọn thiết lập fitness!")
        return

    tier = settings.get("food_budget_tier") or "standard"
    menu = load_menu(tier)
    day_meals = get_full_day_menu(menu)

    total_cal = sum(m.get("calories", 0) for m in day_meals)
    total_p = sum(m.get("protein", 0) for m in day_meals)
    total_c = sum(m.get("carbs", 0) for m in day_meals)
    total_f = sum(m.get("fat", 0) for m in day_meals)
    total_cost = sum(m.get("cost_vnd", 0) for m in day_meals)

    tier_label = TIER_LABELS.get(tier, tier)
    daily_cal = int(settings.get("daily_calories") or 0)

    text = f"🍽 {bold('MENU HÔM NAY')}"
    text += f" \\({escape_md(tier_label)}\\)\n"
    text += f"🎯 Mục tiêu: {escape_md(str(daily_cal))} kcal\n"
    text += f"💰 Chi phí: ~{bold(_format_vnd(total_cost))}đ/ngày\n"
    text += "━━━━━━━━━━━━━━━━━━\n\n"

    for meal in day_meals:
        text += format_meal(meal.get("type", ""), meal) + "\n\n"

    text += "━━━━━━━━━━━━━━━━━━\n"
    text += (
        f"📊 {bold('TỔNG')}: ~{escape_md(str(total_cal))} kcal "
        f"\\| P: {escape_md(str(total_p))}g "
        f"\\| C: {escape_md(str(total_c))}g "
        f"\\| F: {escape_md(str(total_f))}g\n"
    )
    text += f"💰 Tổng chi: ~{bold(_format_vnd(total_cost))}đ "
    text += f"\\(~{escape_md(_format_vnd(total_cost * 30))}/tháng\\)\n\n"
    text += "✅ Dùng /done\\_\\<tên bữa\\> để đánh dấu đã ăn"

    await update.message.reply_text(text, parse_mode="MarkdownV2")


async def done_meal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done_breakfast, /done_lunch, etc."""
    command = update.message.text.strip()
    parts = command.split("_", 1)
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Sử dụng: /done_breakfast, /done_lunch, /done_dinner, ...")
        return

    meal_type = parts[1].lower()
    settings = await get_settings()
    tier = settings.get("food_budget_tier") or "standard"
    menu = load_menu(tier)

    if meal_type not in menu["meals"]:
        valid = ", ".join(menu["meals"].keys())
        await update.message.reply_text(f"❌ Bữa ăn không hợp lệ. Chọn: {valid}")
        return

    meal_info = menu["meals"][meal_type]
    option = meal_info["options"][0] if meal_info.get("options") else {}
    cost = option.get("cost_vnd", 0)

    await log_meal_entry(
        meal_type=meal_type,
        description=meal_info.get("label", meal_type),
        calories=option.get("calories", 0),
        protein=option.get("protein", 0),
        carbs=option.get("carbs", 0),
        fat=option.get("fat", 0),
        cost_vnd=cost,
        completed=True,
    )

    if cost > 0:
        food_cat = await find_category_by_name("Ăn uống")
        if food_cat:
            await add_transaction(
                category_id=food_cat["id"],
                tx_type="expense",
                amount=cost,
                description=f"🍽 {meal_info.get('label', meal_type)} (fitness)",
            )

    emoji = meal_info.get("emoji", "✅")
    cost_str = f" (~{_format_vnd(cost)}đ)" if cost else ""
    await update.message.reply_text(
        f"{emoji} Đã ghi nhận {meal_info.get('label', meal_type)}{cost_str}! "
        f"Tốt lắm! 💪")


def get_meal_handlers() -> list:
    return [
        CommandHandler("meal", meal_command),
        MessageHandler(filters.Regex(r"^/done_\w+"), done_meal_command),
    ]
