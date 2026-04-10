"""Default categories, payment methods, and constants."""

# ─── Default Categories ──────────────────────────────────────────────
# Categories follow the 50/30/20 financial rule:
#   need (50%)  - Essential expenses
#   want (30%)  - Discretionary spending
#   saving (20%) - Savings & investments
#   income       - All income sources

DEFAULT_CATEGORIES = [
    # ━━━ Needs (50%) ━━━
    {"name": "Ăn uống", "emoji": "🍜", "type": "need",
     "keywords": ["ăn", "phở", "cơm", "bún", "bánh", "lunch", "dinner", "breakfast",
                  "ăn sáng", "ăn trưa", "ăn tối", "hủ tiếu", "mì", "chè", "xôi",
                  "đồ ăn", "food", "cháo", "gà", "bò", "heo", "thịt", "rau", "trứng",
                  "gạo", "chợ", "siêu thị", "vinmart", "bách hóa", "tạp hóa"]},
    {"name": "Nhà ở", "emoji": "🏠", "type": "need",
     "keywords": ["nhà", "thuê", "tiền phòng", "rent", "trọ", "chung cư", "phòng"]},
    {"name": "Di chuyển", "emoji": "🚗", "type": "need",
     "keywords": ["grab", "xe", "xăng", "bus", "taxi", "gojek", "be", "uber",
                  "gửi xe", "đổ xăng", "parking", "xe ôm", "vé xe", "xeom"]},
    {"name": "Hóa đơn", "emoji": "⚡", "type": "need",
     "keywords": ["điện", "nước", "internet", "wifi", "gas", "hóa đơn", "bill",
                  "truyền hình", "cáp"]},
    {"name": "Y tế", "emoji": "🏥", "type": "need",
     "keywords": ["thuốc", "bệnh viện", "khám", "doctor", "y tế", "pharmacy",
                  "nhà thuốc", "bác sĩ", "nha khoa", "răng"]},
    {"name": "Viễn thông", "emoji": "📱", "type": "need",
     "keywords": ["điện thoại", "sim", "data", "mobile", "nạp tiền", "4g", "5g",
                  "viettel", "mobifone", "vinaphone"]},

    # ━━━ Wants (30%) ━━━
    {"name": "Cafe/Trà sữa", "emoji": "☕", "type": "want",
     "keywords": ["cafe", "coffee", "cà phê", "trà sữa", "starbucks", "highlands",
                  "phúc long", "sinh tố", "trà", "nước ép", "smoothie", "boba",
                  "koi", "gongcha", "tocotoco"]},
    {"name": "Giải trí", "emoji": "🎬", "type": "want",
     "keywords": ["phim", "game", "netflix", "spotify", "youtube", "giải trí",
                  "karaoke", "bar", "club", "nhạc", "concert", "steam"]},
    {"name": "Shopping", "emoji": "🛍", "type": "want",
     "keywords": ["mua", "shopping", "lazada", "shopee", "tiki", "quần", "áo",
                  "giày", "dép", "đồ", "thời trang", "fashion", "order"]},
    {"name": "Du lịch", "emoji": "✈️", "type": "want",
     "keywords": ["vé máy bay", "khách sạn", "hotel", "du lịch", "travel",
                  "booking", "resort", "tour"]},
    {"name": "Quà tặng", "emoji": "🎁", "type": "want",
     "keywords": ["quà", "gift", "sinh nhật", "birthday", "tặng", "valentine"]},
    {"name": "Làm đẹp", "emoji": "💅", "type": "want",
     "keywords": ["tóc", "spa", "nail", "skincare", "mỹ phẩm", "cắt tóc",
                  "nhuộm", "makeup", "kem", "son"]},
    {"name": "Ăn ngoài", "emoji": "🍽", "type": "want",
     "keywords": ["nhà hàng", "restaurant", "buffet", "lẩu", "nướng", "tiệc",
                  "nhậu", "beer", "bia", "rượu", "wine", "bbq", "quán"]},

    # ━━━ Savings (20%) ━━━
    {"name": "Tiết kiệm", "emoji": "🏦", "type": "saving",
     "keywords": ["gửi", "tiết kiệm", "saving", "để dành"]},
    {"name": "Đầu tư", "emoji": "📈", "type": "saving",
     "keywords": ["chứng khoán", "crypto", "stock", "bitcoin", "đầu tư",
                  "invest", "coin", "etf", "quỹ"]},
    {"name": "Giáo dục", "emoji": "🎓", "type": "saving",
     "keywords": ["học", "course", "sách", "book", "udemy", "khóa học", "lớp",
                  "trường", "học phí", "ielts"]},
    {"name": "Bảo hiểm", "emoji": "🛡", "type": "saving",
     "keywords": ["bảo hiểm", "insurance", "bhxh", "bhyt"]},
    {"name": "Trả nợ", "emoji": "💳", "type": "saving",
     "keywords": ["trả nợ", "credit", "vay", "nợ", "khoản vay"]},

    # ━━━ Income ━━━
    {"name": "Lương", "emoji": "💼", "type": "income",
     "keywords": ["lương", "salary", "wage", "pay"]},
    {"name": "Thưởng", "emoji": "🎊", "type": "income",
     "keywords": ["thưởng", "bonus", "kpi"]},
    {"name": "Freelance", "emoji": "💻", "type": "income",
     "keywords": ["freelance", "dự án", "project", "job", "làm thêm"]},
    {"name": "Thu nhập khác", "emoji": "💵", "type": "income",
     "keywords": ["lãi", "interest", "hoàn tiền", "cashback", "thu nhập",
                  "bán", "cho thuê"]},
]

# ─── Payment Methods ─────────────────────────────────────────────────
PAYMENT_METHODS = {
    "cash": {
        "name": "Tiền mặt", "emoji": "💵",
        "keywords": ["cash", "tiền mặt", "tm"]
    },
    "bank": {
        "name": "Chuyển khoản", "emoji": "🏦",
        "keywords": ["ck", "chuyển khoản", "bank", "banking", "vcb", "tcb",
                     "mb", "vietcombank", "techcombank", "mbbank", "bidv",
                     "acb", "tpbank", "vpbank", "sacombank"]
    },
    "credit": {
        "name": "Thẻ tín dụng", "emoji": "💳",
        "keywords": ["visa", "credit", "mastercard", "thẻ", "card", "jcb"]
    },
    "ewallet": {
        "name": "Ví điện tử", "emoji": "📲",
        "keywords": ["momo", "zalopay", "vnpay", "viettelpay", "shopeepay", "ví"]
    },
}

# ─── Category Type Labels ────────────────────────────────────────────
CATEGORY_TYPE_LABELS = {
    "need": {"name": "Nhu cầu", "emoji": "💡", "color": "#4CAF50"},
    "want": {"name": "Mong muốn", "emoji": "🎮", "color": "#FF9800"},
    "saving": {"name": "Tiết kiệm", "emoji": "💰", "color": "#2196F3"},
    "income": {"name": "Thu nhập", "emoji": "📥", "color": "#9C27B0"},
}
