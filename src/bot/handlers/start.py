"""/start command and onboarding conversation flow.

Unified flow:
  1. Welcome → Ask monthly income → Budget 50/30/20
  2. Ask fitness info: age → weight → height → target → activity → food budget
  3. Dashboard showing both finance + fitness overview
"""
import logging
from datetime import date

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)

from src.database import get_settings, update_settings, get_spending_summary, get_type_spending
from src.utils.formatter import format_currency, progress_bar, percentage
from src.utils.calories import full_calculation
from src.utils.fitness_fmt import format_profile as format_fitness_profile, bold as fit_bold, escape_md as fit_escape
from src.parsers.amount_parser import parse_amount
from src.bot.keyboards.inline import income_options, budget_style_picker, dashboard_actions

logger = logging.getLogger(__name__)

# Conversation states
ASK_INCOME, CONFIRM_BUDGET = range(2)
FIT_AGE, FIT_WEIGHT, FIT_HEIGHT, FIT_TARGET, FIT_ACTIVITY, FIT_FOOD_BUDGET = range(10, 16)

ACTIVITY_KEYBOARD = ReplyKeyboardMarkup(
    [["Ít vận động", "Nhẹ (1-3 ngày)"],
     ["Vừa (3-5 ngày)", "Nặng (6-7 ngày)"]],
    one_time_keyboard=True, resize_keyboard=True,
)

ACTIVITY_MAP = {
    "ít vận động": "sedentary",
    "nhẹ (1-3 ngày)": "light",
    "vừa (3-5 ngày)": "moderate",
    "nặng (6-7 ngày)": "active",
}

FOOD_BUDGET_KEYBOARD = ReplyKeyboardMarkup(
    [["Tiết kiệm (< 2 triệu)"],
     ["Trung bình (2-4 triệu)"],
     ["Thoải mái (> 4 triệu)"]],
    one_time_keyboard=True, resize_keyboard=True,
)

FOOD_BUDGET_MAP = {
    "tiết kiệm (< 2 triệu)": ("budget", 2000000),
    "trung bình (2-4 triệu)": ("standard", 3500000),
    "thoải mái (> 4 triệu)": ("premium", 5000000),
}


# ═══════════════════════════════════════════════════════════════════════
# /start entry point
# ═══════════════════════════════════════════════════════════════════════

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = await get_settings()

    if settings.get("onboarding_complete") and settings.get("fitness_onboarding_complete"):
        await _show_dashboard(update)
        return ConversationHandler.END

    user = update.effective_user
    await update_settings(
        telegram_id=user.id,
        username=user.username or "",
        full_name=user.full_name or ""
    )

    if settings.get("onboarding_complete") and not settings.get("fitness_onboarding_complete"):
        await update.message.reply_text(
            "🏋️ *Thiết lập hồ sơ thể hình*\n\n"
            "Hãy cho tôi biết thông tin cơ thể của bạn.\n\n"
            "📅 *Bạn bao nhiêu tuổi?*",
            parse_mode="Markdown"
        )
        return FIT_AGE

    await update.message.reply_text(
        "👋 Chào bạn! Tôi là *LifeBot* — trợ lý quản lý cuộc sống.\n\n"
        "Tôi sẽ giúp bạn:\n"
        "• 📝 Ghi chép chi tiêu nhanh chóng\n"
        "• 📊 Phân tích xu hướng tài chính\n"
        "• 🏋️ Theo dõi tập luyện & dinh dưỡng\n"
        "• 🎯 Mục tiêu tiết kiệm & thể hình\n"
        "• 🤖 Tư vấn AI thông minh\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Hãy bắt đầu nhé! 💰\n\n"
        "*Thu nhập hàng tháng* của bạn khoảng bao nhiêu?",
        parse_mode="Markdown",
        reply_markup=income_options()
    )
    return ASK_INCOME


# ═══════════════════════════════════════════════════════════════════════
# Finance onboarding: Income + Budget
# ═══════════════════════════════════════════════════════════════════════

async def _income_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "income_custom":
        await query.edit_message_text(
            "💰 Nhập thu nhập hàng tháng của bạn (VND):\n\n"
            "Ví dụ: `15000000` hoặc `15tr` hoặc `15m`",
            parse_mode="Markdown"
        )
        return ASK_INCOME

    income = int(data.split("_")[1])
    context.user_data["income"] = income
    await _show_budget_proposal(query.message, income, edit=True)
    return CONFIRM_BUDGET


async def _income_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount, _ = parse_amount(update.message.text)
    if not amount or amount <= 0:
        await update.message.reply_text(
            "❌ Không nhận diện được số tiền. Vui lòng nhập lại:\n"
            "Ví dụ: `15000000` hoặc `15tr`",
            parse_mode="Markdown"
        )
        return ASK_INCOME

    context.user_data["income"] = amount
    await _show_budget_proposal(update.message, amount)
    return CONFIRM_BUDGET


async def _show_budget_proposal(message, income: float, edit: bool = False):
    needs = income * 0.5
    wants = income * 0.3
    savings = income * 0.2

    text = (
        f"✅ Thu nhập: *{format_currency(income)}*/tháng\n\n"
        "📊 *Gợi ý phân bổ theo nguyên tắc 50/30/20:*\n\n"
        f"💡 Nhu cầu thiết yếu (50%): *{format_currency(needs)}*\n"
        f"   _Ăn uống, nhà ở, di chuyển, hóa đơn_\n\n"
        f"🎮 Mong muốn cá nhân (30%): *{format_currency(wants)}*\n"
        f"   _Cafe, giải trí, shopping, du lịch_\n\n"
        f"💰 Tiết kiệm & đầu tư (20%): *{format_currency(savings)}*\n"
        f"   _Tiết kiệm, đầu tư, giáo dục, bảo hiểm_\n"
    )

    if edit:
        await message.edit_text(text, parse_mode="Markdown",
                                reply_markup=budget_style_picker())
    else:
        await message.reply_text(text, parse_mode="Markdown",
                                 reply_markup=budget_style_picker())


async def _budget_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    income = context.user_data.get("income", 0)

    if query.data == "budget_default":
        await update_settings(
            monthly_income=income,
            budget_needs_pct=50,
            budget_wants_pct=30,
            budget_savings_pct=20,
            onboarding_complete=1
        )

        await query.edit_message_text(
            "🎉 *Tài chính đã thiết lập!*\n\n"
            "Tiếp theo, hãy thiết lập hồ sơ thể hình 🏋️\n\n"
            "📅 *Bạn bao nhiêu tuổi?*",
            parse_mode="Markdown"
        )
        return FIT_AGE

    await query.edit_message_text(
        "✏️ Nhập tỷ lệ % theo thứ tự: *Nhu cầu / Mong muốn / Tiết kiệm*\n\n"
        "Ví dụ: `60 20 20` hoặc `40 30 30`\n\n"
        "⚠️ Tổng phải bằng 100%",
        parse_mode="Markdown"
    )
    return CONFIRM_BUDGET


async def _custom_budget_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.replace("/", " ").replace(",", " ").split()

    try:
        needs = float(parts[0])
        wants = float(parts[1])
        savings = float(parts[2])
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Định dạng không đúng. Nhập 3 số, ví dụ: `60 20 20`",
            parse_mode="Markdown"
        )
        return CONFIRM_BUDGET

    if abs(needs + wants + savings - 100) > 0.01:
        await update.message.reply_text(
            f"❌ Tổng = {needs + wants + savings:.0f}%, cần bằng 100%\n"
            "Vui lòng nhập lại:",
        )
        return CONFIRM_BUDGET

    income = context.user_data.get("income", 0)
    await update_settings(
        monthly_income=income,
        budget_needs_pct=needs,
        budget_wants_pct=wants,
        budget_savings_pct=savings,
        onboarding_complete=1
    )

    await update.message.reply_text(
        f"🎉 *Tài chính đã thiết lập!*\n\n"
        f"📊 Tỷ lệ: {needs:.0f}/{wants:.0f}/{savings:.0f}\n\n"
        "Tiếp theo, hãy thiết lập hồ sơ thể hình 🏋️\n\n"
        "📅 *Bạn bao nhiêu tuổi?*",
        parse_mode="Markdown"
    )
    return FIT_AGE


# ═══════════════════════════════════════════════════════════════════════
# Fitness onboarding
# ═══════════════════════════════════════════════════════════════════════

async def _fit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text.strip())
        if not 14 <= age <= 65:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập tuổi hợp lệ (14-65):")
        return FIT_AGE

    context.user_data["fit_age"] = age
    await update.message.reply_text("⚖️ Cân nặng hiện tại của bạn (kg)?")
    return FIT_WEIGHT


async def _fit_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        weight = float(update.message.text.strip().replace(",", "."))
        if not 30 <= weight <= 200:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập cân nặng hợp lệ (30-200 kg):")
        return FIT_WEIGHT

    context.user_data["fit_weight"] = weight
    await update.message.reply_text("📏 Chiều cao của bạn (cm)?")
    return FIT_HEIGHT


async def _fit_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height = float(update.message.text.strip().replace(",", "."))
        if not 140 <= height <= 220:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập chiều cao hợp lệ (140-220 cm):")
        return FIT_HEIGHT

    context.user_data["fit_height"] = height
    await update.message.reply_text("🎯 Cân nặng mục tiêu bạn muốn đạt (kg)?")
    return FIT_TARGET


async def _fit_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        target = float(update.message.text.strip().replace(",", "."))
        if not 40 <= target <= 150:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Vui lòng nhập mục tiêu hợp lệ (40-150 kg):")
        return FIT_TARGET

    context.user_data["fit_target"] = target
    await update.message.reply_text(
        "🏃 Mức độ hoạt động của bạn?",
        reply_markup=ACTIVITY_KEYBOARD,
    )
    return FIT_ACTIVITY


async def _fit_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    activity = ACTIVITY_MAP.get(text, "moderate")
    context.user_data["fit_activity"] = activity

    await update.message.reply_text(
        "💰 Ngân sách ăn uống hàng tháng dành cho tập gym?\n\n"
        "Tôi sẽ chọn thực phẩm phù hợp túi tiền của bạn.",
        reply_markup=FOOD_BUDGET_KEYBOARD,
    )
    return FIT_FOOD_BUDGET


async def _fit_food_budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    budget_tier, budget_amount = FOOD_BUDGET_MAP.get(text, ("standard", 3500000))

    ud = context.user_data
    calc = full_calculation(
        weight_kg=ud["fit_weight"],
        height_cm=ud["fit_height"],
        age=ud["fit_age"],
        activity_level=ud["fit_activity"],
    )

    await update_settings(
        age=ud["fit_age"],
        weight=ud["fit_weight"],
        height=ud["fit_height"],
        target_weight=ud["fit_target"],
        activity_level=ud["fit_activity"],
        goal="bulk",
        monthly_food_budget=budget_amount,
        food_budget_tier=budget_tier,
        tdee=calc["tdee"],
        daily_calories=calc["daily_calories"],
        daily_protein=calc["protein"],
        daily_carbs=calc["carbs"],
        daily_fat=calc["fat"],
        fitness_onboarding_complete=1,
    )

    tier_labels = {"budget": "Tiết kiệm", "standard": "Trung bình", "premium": "Thoải mái"}
    daily_budget = round(budget_amount / 30)
    daily_display = f"{daily_budget:,}".replace(",", ".")

    msg = (
        "🎉 *Thiết lập hoàn tất!*\n\n"
        f"📊 TDEE: *{calc['tdee']}* kcal\n"
        f"🔥 Mục tiêu: *{calc['daily_calories']}* kcal/ngày\n"
        f"🥩 Protein: *{calc['protein']}g* | 🍚 Carbs: *{calc['carbs']}g* | 🥑 Fat: *{calc['fat']}g*\n"
        f"💰 Gói ăn: *{tier_labels.get(budget_tier, budget_tier)}* (~{daily_display}đ/ngày)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "*📋 LỆNH TÀI CHÍNH:*\n"
        "• Gửi `ăn phở 50k` để ghi chi tiêu\n"
        "• /today — Chi tiêu hôm nay\n"
        "• /budget — Ngân sách\n"
        "• /report — Báo cáo tháng\n\n"
        "*🏋️ LỆNH THỂ HÌNH:*\n"
        "• /workout — Bài tập hôm nay\n"
        "• /meal — Menu ăn hôm nay\n"
        "• /log — Ghi nhận bài tập\n"
        "• /weight <kg> — Ghi cân nặng\n"
        "• /water <ml> — Ghi nước uống\n"
        "• /ask — Hỏi AI Coach\n\n"
        "💡 Gõ /help để xem tất cả lệnh!"
    )

    await update.message.reply_text(msg, parse_mode="Markdown",
                                    reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════

async def _show_dashboard(update: Update):
    today = date.today()
    month_start = today.replace(day=1)

    settings = await get_settings()
    summary = await get_spending_summary(month_start, today)
    type_spending = await get_type_spending(month_start, today)

    income = settings.get("monthly_income", 0)
    needs_pct = settings.get("budget_needs_pct", 50)
    wants_pct = settings.get("budget_wants_pct", 30)
    savings_pct = settings.get("budget_savings_pct", 20)

    needs_budget = income * needs_pct / 100
    wants_budget = income * wants_pct / 100
    savings_budget = income * savings_pct / 100

    name = update.effective_user.first_name
    text = (
        f"👋 Chào, *{name}*!\n\n"
        f"📊 *TỔNG QUAN THÁNG {today.month}/{today.year}*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Thu nhập: {format_currency(summary['total_income'])}\n"
        f"💸 Chi tiêu: {format_currency(summary['total_expense'])}\n"
        f"📊 Số GD: {summary['tx_count']}\n\n"
    )

    if income > 0:
        text += (
            f"💡 Nhu cầu: {format_currency(type_spending['need'], True)}"
            f" / {format_currency(needs_budget, True)}\n"
            f"   {progress_bar(type_spending['need'], needs_budget)}"
            f" {percentage(type_spending['need'], needs_budget)}\n"
            f"🎮 Mong muốn: {format_currency(type_spending['want'], True)}"
            f" / {format_currency(wants_budget, True)}\n"
            f"   {progress_bar(type_spending['want'], wants_budget)}"
            f" {percentage(type_spending['want'], wants_budget)}\n"
            f"💰 Tiết kiệm: {format_currency(type_spending['saving'], True)}"
            f" / {format_currency(savings_budget, True)}\n"
            f"   {progress_bar(type_spending['saving'], savings_budget)}"
            f" {percentage(type_spending['saving'], savings_budget)}\n\n"
        )

    if settings.get("fitness_onboarding_complete"):
        w = settings.get("weight") or "?"
        tw = settings.get("target_weight") or "?"
        dc = int(settings.get("daily_calories") or 0)
        text += (
            "🏋️ *Thể hình:*\n"
            f"   Cân nặng: {w}kg → mục tiêu {tw}kg\n"
            f"   Calories: {dc} kcal/ngày\n\n"
        )

    text += "📝 Gửi tin nhắn để ghi chi tiêu nhanh!"
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=dashboard_actions()
    )


# ═══════════════════════════════════════════════════════════════════════
# ConversationHandler builder
# ═══════════════════════════════════════════════════════════════════════

def get_start_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASK_INCOME: [
                CallbackQueryHandler(_income_callback, pattern=r"^income_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _income_text),
            ],
            CONFIRM_BUDGET: [
                CallbackQueryHandler(_budget_callback, pattern=r"^budget_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _custom_budget_text),
            ],
            FIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _fit_age)],
            FIT_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _fit_weight)],
            FIT_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _fit_height)],
            FIT_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, _fit_target)],
            FIT_ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, _fit_activity)],
            FIT_FOOD_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, _fit_food_budget)],
        },
        fallbacks=[CommandHandler("start", start_command)],
        allow_reentry=True,
        per_message=False,
    )


async def handle_dashboard_callback(update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data.split("_")[1]

    if action == "report":
        from src.bot.handlers.report import report_command
        update._effective_message = query.message
        await report_command(update, context)
    elif action == "budget":
        from src.bot.handlers.budget import budget_command
        update._effective_message = query.message
        await budget_command(update, context)
    elif action == "history":
        from src.bot.handlers.transaction import history_command
        update._effective_message = query.message
        await history_command(update, context)
    elif action == "export":
        from src.bot.handlers.utility import export_command
        update._effective_message = query.message
        await export_command(update, context)


def get_dashboard_handlers() -> list:
    return [
        CallbackQueryHandler(handle_dashboard_callback, pattern=r"^dash_"),
    ]
