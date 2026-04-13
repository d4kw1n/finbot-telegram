"""/help command — show all available commands and usage guide."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler


HELP_MAIN = (
    "📖 *LIFEBOT — HƯỚNG DẪN*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    "💰 *TÀI CHÍNH*\n"
    "  /today  /week  /month — Xem chi tiêu\n"
    "  /budget — Ngân sách\n"
    "  /report — Báo cáo + biểu đồ\n"
    "  /advice — Tư vấn tài chính AI\n"
    "  /goal — Mục tiêu tiết kiệm\n"
    "  /history — Lịch sử GD\n"
    "  /search — Tìm giao dịch\n"
    "  /export — Xuất CSV\n\n"

    "🏋️ *THỂ HÌNH*\n"
    "  /workout — Bài tập hôm nay\n"
    "  /meal — Menu dinh dưỡng\n"
    "  /log — Ghi nhận bài tập\n"
    "  /exercise — Hướng dẫn kỹ thuật\n"
    "  /guide — Hướng dẫn chung\n\n"

    "📊 *THEO DÕI*\n"
    "  /weight `<kg>` — Ghi cân nặng\n"
    "  /water `<ml>` — Ghi nước uống\n"
    "  /fittoday — Tổng kết hôm nay\n"
    "  /progress — Biểu đồ cân nặng\n"
    "  /fitreport — Báo cáo tuần\n\n"

    "🤖 *AI*\n"
    "  /ask — AI Fitness Coach\n"
    "  /advice — AI Tài chính\n\n"

    "⚙️ *KHÁC*\n"
    "  /settings — Cài đặt\n"
    "  /backup — Sao lưu DB\n"
    "  /undo — Hoàn tác GD cuối\n"
    "  /start — Dashboard\n"
)


HELP_NLP = (
    "📝 *GHI CHI TIÊU NHANH*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    "Gửi tin nhắn tự nhiên, bot tự hiểu:\n\n"

    "  `ăn phở 50k`\n"
    "  `grab 35000`\n"
    "  `cafe 29k visa`\n"
    "  `+15tr lương`\n"
    "  `mua sách 120k hôm qua`\n\n"

    "💡 *Cách viết số tiền:*\n"
    "  `50k` = 50.000đ\n"
    "  `2tr` = 2.000.000đ\n"
    "  `1 củ` = 1.000.000đ\n"
    "  `500 ngàn` = 500.000đ\n"
    "  `$25` tự đổi sang VND\n"
)


HELP_FITNESS = (
    "🏋️ *CHI TIẾT LỆNH THỂ HÌNH*\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n\n"

    "*Tập luyện:*\n"
    "  /workout — Bài tập PPL hôm nay\n"
    "  /log — Ghi bài tập (hội thoại)\n"
    "  /log `bench_press 80 4x8` — Log nhanh\n"
    "  `/done_workout` — Xong buổi tập\n"
    "  /exercise `<số>` — Kỹ thuật chi tiết\n"
    "  /guide — Khởi động & tempo\n\n"

    "*Dinh dưỡng:*\n"
    "  /meal — Menu hôm nay theo gói\n"
    "  `/done_breakfast` — Đánh dấu đã ăn\n"
    "  `/done_lunch`  `/done_dinner`\n"
    "  `/done_snack_am`  `/done_pre_workout`\n\n"

    "*Theo dõi:*\n"
    "  /weight `66.5` — Ghi cân nặng\n"
    "  /water `500` — Ghi nước (ml)\n"
    "  /fittoday — Tổng kết ngày\n"
    "  /progress — Chart cân nặng\n"
    "  /fitreport — Báo cáo tuần\n"
)


def _help_keyboard(current: str = "main") -> InlineKeyboardMarkup:
    buttons = []
    if current != "main":
        buttons.append(InlineKeyboardButton("📋 Tổng quan", callback_data="help_main"))
    if current != "nlp":
        buttons.append(InlineKeyboardButton("📝 Ghi nhanh", callback_data="help_nlp"))
    if current != "fitness":
        buttons.append(InlineKeyboardButton("🏋️ Thể hình", callback_data="help_fitness"))

    rows = [buttons] if len(buttons) <= 3 else [buttons[:2], buttons[2:]]
    return InlineKeyboardMarkup(rows)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        HELP_MAIN,
        parse_mode="Markdown",
        reply_markup=_help_keyboard("main"),
    )


async def _help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    page = query.data.split("_")[1]
    pages = {"main": HELP_MAIN, "nlp": HELP_NLP, "fitness": HELP_FITNESS}
    text = pages.get(page, HELP_MAIN)

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=_help_keyboard(page),
    )


def get_help_handler() -> CommandHandler:
    return CommandHandler("help", help_command)


def get_help_callback_handler() -> CallbackQueryHandler:
    return CallbackQueryHandler(_help_callback, pattern=r"^help_")
