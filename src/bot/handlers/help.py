"""/help command — show all available commands and usage guide."""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive help guide."""
    text = (
        "📖 *HƯỚNG DẪN SỬ DỤNG FINBOT*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "📝 *GHI CHI TIÊU NHANH*\n"
        "Chỉ cần gửi tin nhắn tự nhiên:\n"
        "• `ăn phở 50k` → Chi 50,000đ, Ăn uống\n"
        "• `grab 35000` → Chi 35,000đ, Di chuyển\n"
        "• `cafe 29k visa` → Chi 29,000đ, Thẻ\n"
        "• `điện 500k ck` → Chi 500,000đ, CK\n"
        "• `+15tr lương` → Thu nhập 15,000,000đ\n"
        "• `mua sách 120k hôm qua` → Chi hôm qua\n\n"

        "💡 *Định dạng số tiền:*\n"
        "• `50k` = 50,000đ\n"
        "• `2tr` = 2,000,000đ\n"
        "• `2tr5` = 2,500,000đ\n"
        "• `1 củ` = 1,000,000đ\n"
        "• `500 ngàn` = 500,000đ\n"
        "• `5 trăm` = 500,000đ\n"
        "• `$25` = ~637,500đ\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "📋 *CÁC LỆNH*\n\n"

        "*Xem chi tiêu:*\n"
        "• /today — Hôm nay\n"
        "• /week — Tuần này\n"
        "• /month — Tháng này\n"
        "• /history — GD gần đây\n\n"

        "*Ngân sách:*\n"
        "• /budget — Xem ngân sách\n\n"

        "*Báo cáo:*\n"
        "• /report — Báo cáo + biểu đồ\n"
        "• /advice `<câu hỏi>` — Tư vấn AI\n\n"

        "*Tìm kiếm & Xuất dữ liệu:*\n"
        "• /search `<từ khóa>` — Tìm GD\n"
        "• /export — Xuất CSV tháng này\n"
        "• /export `all` — Xuất tất cả\n"
        "• /backup — Sao lưu database\n\n"

        "*Mục tiêu:*\n"
        "• /goal — Xem mục tiêu\n"
        "• /goal add `<tên> <tiền> [tháng]`\n"
        "• /goal deposit `<ID> <tiền>`\n\n"

        "*Cài đặt:*\n"
        "• /settings — Xem cài đặt\n"
        "• /setincome `<số>` — Đổi thu nhập\n"
        "• /setratio `<N W S>` — Đổi tỷ lệ\n\n"

        "*Khác:*\n"
        "• /undo — Hoàn tác GD cuối\n"
        "• /start — Reset/Dashboard\n"
        "• /help — Bảng này\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


def get_help_handler() -> CommandHandler:
    """Get the help command handler."""
    return CommandHandler("help", help_command)
