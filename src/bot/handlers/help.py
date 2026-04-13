"""/help command — show all available commands and usage guide."""
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *HƯỚNG DẪN SỬ DỤNG LIFEBOT*\n"
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
        "• `$25` = ~637,500đ\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "💰 *TÀI CHÍNH*\n\n"

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

        "*Tìm kiếm & Xuất:*\n"
        "• /search `<từ khóa>` — Tìm GD\n"
        "• /export — Xuất CSV\n"
        "• /backup — Sao lưu DB\n\n"

        "*Mục tiêu:*\n"
        "• /goal — Xem mục tiêu\n"
        "• /goal add `<tên> <tiền> [tháng]`\n"
        "• /goal deposit `<ID> <tiền>`\n\n"

        "*Cài đặt:*\n"
        "• /settings — Xem cài đặt\n"
        "• /setincome `<số>` — Đổi thu nhập\n"
        "• /setratio `<N W S>` — Đổi tỷ lệ\n\n"

        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        "🏋️ *THỂ HÌNH*\n\n"

        "*Tập luyện:*\n"
        "• /workout — Bài tập hôm nay (PPL)\n"
        "• /log — Ghi nhận bài tập\n"
        "• /log `<tên> <kg> <sets>x<reps>` — Log nhanh\n"
        "• /done\\_workout — Hoàn thành buổi tập\n"
        "• /exercise — Danh sách bài tập\n"
        "• /exercise `<số>` — Chi tiết bài tập\n"
        "• /guide — Hướng dẫn khởi động & tempo\n\n"

        "*Dinh dưỡng:*\n"
        "• /meal — Menu ăn hôm nay\n"
        "• /done\\_`<bữa>` — Đánh dấu đã ăn\n"
        "   _VD: /done\\_breakfast, /done\\_lunch_\n\n"

        "*Theo dõi:*\n"
        "• /weight `<kg>` — Ghi cân nặng\n"
        "• /water `<ml>` — Ghi nước uống\n"
        "• /fittoday — Tổng kết thể hình hôm nay\n"
        "• /progress — Biểu đồ cân nặng\n"
        "• /fitreport — Báo cáo thể hình tuần\n\n"

        "*AI Coach:*\n"
        "• /ask `<câu hỏi>` — Hỏi AI về tập luyện & dinh dưỡng\n\n"

        "*Khác:*\n"
        "• /undo — Hoàn tác GD cuối\n"
        "• /start — Reset/Dashboard\n"
        "• /help — Bảng này\n"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


def get_help_handler() -> CommandHandler:
    return CommandHandler("help", help_command)
