"""Fitness: /weight, /water, /today (fitness summary), /progress, /fitreport."""
import io
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from src.database import (
    get_settings, update_settings, log_weight, log_water,
    get_today_water, get_today_nutrition, did_workout_today,
    get_weight_history, get_fitness_weekly_report,
)
from src.utils.fitness_fmt import (
    format_daily_summary, format_progress_chart_caption, bold, escape_md,
)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


async def weight_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚖️ Sử dụng: /weight <số kg>\nVí dụ: /weight 66.5")
        return

    try:
        weight = float(args[0].replace(",", "."))
        if not 30 <= weight <= 200:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Cân nặng không hợp lệ (30-200 kg)")
        return

    settings = await get_settings()
    old_weight = settings.get("weight") or weight

    await log_weight(weight)
    await update_settings(weight=weight)

    diff = round(weight - old_weight, 1)
    sign = "+" if diff >= 0 else ""
    await update.message.reply_text(
        f"✅ Đã ghi: {weight} kg ({sign}{diff} kg so với ban đầu)\n\n"
        f"📈 Xem biểu đồ: /progress")


async def water_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "💧 Sử dụng: /water <ml>\nVí dụ: /water 500")
        return

    try:
        amount = int(args[0])
        if not 50 <= amount <= 5000:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Số ml không hợp lệ (50-5000)")
        return

    await log_water(amount)
    total = await get_today_water()

    pct = min(round(total / 3000 * 100), 100)
    bar_filled = "🟦" * (pct // 10)
    bar_empty = "⬜" * (10 - pct // 10)

    await update.message.reply_text(
        f"💧 +{amount}ml — Tổng hôm nay: {total}ml / 3000ml\n"
        f"{bar_filled}{bar_empty} {pct}%")


async def fit_today_command(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    settings = await get_settings()
    if not settings.get("fitness_onboarding_complete"):
        await update.message.reply_text("❌ Gõ /start trước!")
        return

    nutrition = await get_today_nutrition()
    water = await get_today_water()
    workout_done = await did_workout_today()

    text = format_daily_summary(
        meals_done=nutrition["meals_done"],
        meals_total=7,
        water_ml=water,
        workout_done=workout_done,
    )

    target_cal = int(settings.get("daily_calories") or 0)
    consumed_cal = int(nutrition["calories"])
    remaining = max(target_cal - consumed_cal, 0)

    text += f"\n\n🔥 {bold('DINH DƯỠNG')}"
    text += f"\n  Đã nạp: {bold(f'{consumed_cal}')} / {escape_md(str(target_cal))} kcal"
    text += f"\n  Còn thiếu: {bold(str(remaining))} kcal"
    text += (f"\n  Protein: {bold(str(int(nutrition['protein'])))}g"
             f" / {escape_md(str(int(settings.get('daily_protein') or 0)))}g")

    await update.message.reply_text(text, parse_mode="MarkdownV2")


async def progress_command(update: Update,
                           context: ContextTypes.DEFAULT_TYPE):
    settings = await get_settings()
    if not settings.get("fitness_onboarding_complete"):
        await update.message.reply_text("❌ Gõ /start trước!")
        return

    current = settings.get("weight") or 65
    target = settings.get("target_weight") or 78

    caption = format_progress_chart_caption(
        current=current, start=65.0, target=target)

    chart_buf = await _generate_weight_chart(days=30)
    if chart_buf:
        await update.message.reply_photo(
            photo=chart_buf, caption=caption, parse_mode="MarkdownV2")
    else:
        caption += "\n\n📊 Ghi nhận cân nặng ít nhất 2 lần để xem biểu đồ\\!"
        await update.message.reply_text(caption, parse_mode="MarkdownV2")


async def fitreport_command(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    report = await get_fitness_weekly_report()
    wc = report["weight_change"]
    sign = "+" if wc >= 0 else ""

    text = f"📊 {bold('BÁO CÁO THỂ HÌNH TUẦN')}\n\n"
    text += f"🏋️ Số ngày tập: {bold(str(report['workout_days']))} / 6\n"
    text += f"🍽 Bữa ăn đã log: {bold(str(report['meals_logged']))}\n"
    text += f"⚖️ Thay đổi cân: {bold(f'{sign}{wc}')} kg\n"

    if report["latest_weight"]:
        text += f"  Cân hiện tại: {bold(str(report['latest_weight']))} kg\n"

    text += f"\n💡 {bold('ĐÁNH GIÁ')}: "
    if report["workout_days"] >= 5:
        text += "Xuất sắc\\! Giữ vững nhịp độ này\\! 🔥"
    elif report["workout_days"] >= 3:
        text += "Khá tốt\\. Cố thêm 1\\-2 buổi nữa nhé\\! 💪"
    else:
        text += "Cần cải thiện\\. Hãy ưu tiên thời gian tập luyện\\! 🎯"

    await update.message.reply_text(text, parse_mode="MarkdownV2")


async def _generate_weight_chart(days: int = 30) -> io.BytesIO | None:
    if not HAS_MATPLOTLIB:
        return None
    logs = await get_weight_history(days)
    if len(logs) < 2:
        return None

    dates = [datetime.fromisoformat(log["logged_at"]) for log in logs]
    weights = [log["weight"] for log in logs]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, weights, "o-", color="#4CAF50", linewidth=2, markersize=6)
    ax.fill_between(dates, weights, alpha=0.15, color="#4CAF50")
    ax.set_title("Biểu đồ Cân nặng", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Ngày")
    ax.set_ylabel("Cân nặng (kg)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    buf.seek(0)
    plt.close(fig)
    return buf


def get_progress_handlers() -> list:
    return [
        CommandHandler("weight", weight_command),
        CommandHandler("water", water_command),
        CommandHandler("fittoday", fit_today_command),
        CommandHandler("progress", progress_command),
        CommandHandler("fitreport", fitreport_command),
        CommandHandler("done_workout", done_workout_command),
    ]


async def done_workout_command(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    from src.bot.handlers.fitness_log import done_workout_command as _dwc
    await _dwc(update, context)
