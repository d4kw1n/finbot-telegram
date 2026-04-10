"""/export, /backup, /search — utility commands.

Provides:
  /export [month] — Export transactions to CSV
  /backup        — Send database file via Telegram
  /search <keyword> — Search transactions by description
"""
import csv
import io
import logging
import os
from datetime import date

from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler

from src.config import DB_PATH
from src.database import get_transactions, get_all_transactions_for_export
from src.utils.formatter import format_currency, format_date, format_payment_method

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# /export — CSV export
# ═══════════════════════════════════════════════════════════════════════

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export transactions to CSV.

    Usage:
        /export        → this month
        /export all    → everything
        /export 3      → month 3 of current year
    """
    today = date.today()
    start_date = None
    end_date = None
    label = ""

    args = context.args or []

    if args and args[0].lower() == "all":
        label = "tat-ca"
    elif args:
        try:
            month = int(args[0])
            year = int(args[1]) if len(args) > 1 else today.year
            start_date = date(year, month, 1)
            # End of month
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            from datetime import timedelta
            end_date -= timedelta(days=1)
            label = f"thang-{month:02d}-{year}"
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Sai cú pháp.\n\n"
                "Ví dụ:\n"
                "• `/export` — Tháng này\n"
                "• `/export all` — Tất cả\n"
                "• `/export 3` — Tháng 3",
                parse_mode="Markdown"
            )
            return
    else:
        # Default: this month
        start_date = today.replace(day=1)
        end_date = today
        label = f"thang-{today.month:02d}-{today.year}"

    await update.message.reply_text("📤 Đang xuất dữ liệu...")

    txns = await get_all_transactions_for_export(start_date, end_date)

    if not txns:
        await update.message.reply_text("📭 Không có giao dịch nào trong khoảng này.")
        return

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Ngày", "Loại", "Số tiền", "Danh mục", "Mô tả",
        "Phương thức", "Loại danh mục"
    ])

    total_income = 0
    total_expense = 0

    for tx in txns:
        tx_type_vn = "Thu nhập" if tx["type"] == "income" else "Chi tiêu"
        writer.writerow([
            tx["transaction_date"],
            tx_type_vn,
            tx["amount"],
            tx.get("category_name", ""),
            tx.get("description", ""),
            tx.get("payment_method", "cash"),
            tx.get("category_type", ""),
        ])

        if tx["type"] == "income":
            total_income += tx["amount"]
        else:
            total_expense += tx["amount"]

    # Summary row
    writer.writerow([])
    writer.writerow(["TỔNG THU NHẬP", "", total_income, "", "", "", ""])
    writer.writerow(["TỔNG CHI TIÊU", "", total_expense, "", "", "", ""])
    writer.writerow(["SỐ DƯ", "", total_income - total_expense, "", "", "", ""])

    # Send file
    output.seek(0)
    csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM for Excel
    filename = f"finbot-{label}.csv"

    await update.message.reply_document(
        document=io.BytesIO(csv_bytes),
        filename=filename,
        caption=(
            f"📊 *Xuất dữ liệu: {label}*\n\n"
            f"📝 {len(txns)} giao dịch\n"
            f"💰 Thu: {format_currency(total_income, True)}\n"
            f"💸 Chi: {format_currency(total_expense, True)}\n"
            f"💚 Số dư: {format_currency(total_income - total_expense, True)}"
        ),
        parse_mode="Markdown"
    )


# ═══════════════════════════════════════════════════════════════════════
# /backup — Send DB file
# ═══════════════════════════════════════════════════════════════════════

async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the database file to the user for backup."""
    db_path = DB_PATH

    if not os.path.exists(db_path):
        await update.message.reply_text("❌ Không tìm thấy file database.")
        return

    file_size = os.path.getsize(db_path)
    size_kb = file_size / 1024

    today = date.today()
    filename = f"finbot-backup-{today.isoformat()}.db"

    with open(db_path, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=filename,
            caption=(
                f"💾 *Backup Database*\n\n"
                f"📅 Ngày: {format_date(today)}\n"
                f"📦 Kích thước: {size_kb:.1f} KB\n\n"
                f"💡 Để khôi phục, thay file `data/finance.db` "
                f"bằng file này."
            ),
            parse_mode="Markdown"
        )


# ═══════════════════════════════════════════════════════════════════════
# /search — Search transactions
# ═══════════════════════════════════════════════════════════════════════

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search transactions by keyword.

    Usage: /search phở
    """
    if not context.args:
        await update.message.reply_text(
            "🔍 *Tìm kiếm giao dịch*\n\n"
            "Cú pháp: `/search <từ khóa>`\n\n"
            "Ví dụ:\n"
            "• `/search phở`\n"
            "• `/search grab`\n"
            "• `/search shopee`",
            parse_mode="Markdown"
        )
        return

    keyword = " ".join(context.args)
    txns = await get_transactions(search=keyword, limit=20)

    if not txns:
        await update.message.reply_text(
            f"📭 Không tìm thấy giao dịch nào với từ khóa \"{keyword}\"."
        )
        return

    total = sum(tx["amount"] for tx in txns if tx["type"] == "expense")

    text = f"🔍 *Kết quả cho \"{keyword}\"* ({len(txns)} GD)\n"
    text += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for tx in txns:
        sign = "+" if tx["type"] == "income" else "-"
        emoji = tx.get("category_emoji", "📦")
        desc = tx.get("description", "") or tx.get("category_name", "")
        text += (
            f"📅 {tx['transaction_date']} | "
            f"{emoji} {sign}{format_currency(tx['amount'], True)} "
            f"— {desc}\n"
        )

    if total > 0:
        text += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += f"💸 Tổng chi: {format_currency(total, True)}"

    await update.message.reply_text(text, parse_mode="Markdown")


def get_utility_handlers() -> list:
    """Get utility handlers."""
    return [
        CommandHandler("export", export_command),
        CommandHandler("backup", backup_command),
        CommandHandler("search", search_command),
    ]
