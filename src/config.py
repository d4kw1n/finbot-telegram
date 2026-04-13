"""Configuration settings for the LifeBot (Finance + Fitness)."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ─── Bot ─────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ─── Proxy (for VMs that can't reach api.telegram.org directly) ──────
PROXY_URL = os.getenv("PROXY_URL", "")

# ─── Network timeouts (seconds) ─────────────────────────────────────
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "30"))
READ_TIMEOUT = float(os.getenv("READ_TIMEOUT", "30"))
WRITE_TIMEOUT = float(os.getenv("WRITE_TIMEOUT", "30"))
POOL_TIMEOUT = float(os.getenv("POOL_TIMEOUT", "10"))

# ─── AI (unified — picks best available provider) ────────────────────
AI_PROVIDER = os.getenv("AI_PROVIDER", "")
AI_API_KEY = os.getenv("AI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ─── Database ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "finance.db"))

# ─── Defaults ────────────────────────────────────────────────────────
TIMEZONE = "Asia/Ho_Chi_Minh"
DEFAULT_CURRENCY = "VND"

# ─── Budget defaults (50/30/20 rule) ────────────────────────────────
DEFAULT_NEEDS_PCT = 50
DEFAULT_WANTS_PCT = 30
DEFAULT_SAVINGS_PCT = 20

# ─── Fitness defaults ───────────────────────────────────────────────
DEFAULT_PROFILE = {
    "age": 24,
    "weight": 65.0,
    "height": 178.0,
    "goal": "bulk",
    "activity_level": "moderate",
    "target_weight": 78.0,
}

FITNESS_REMINDER_SCHEDULE = {
    "breakfast":    {"hour": 7,  "minute": 0,  "label": "🍳 Bữa sáng"},
    "snack_am":     {"hour": 10, "minute": 0,  "label": "🥜 Snack sáng"},
    "lunch":        {"hour": 12, "minute": 30, "label": "🍚 Bữa trưa"},
    "pre_workout":  {"hour": 15, "minute": 30, "label": "🍠 Pre-workout"},
    "workout":      {"hour": 17, "minute": 0,  "label": "🏋️ Tập luyện"},
    "dinner":       {"hour": 19, "minute": 30, "label": "🥩 Bữa tối"},
    "log_progress": {"hour": 21, "minute": 0,  "label": "📊 Ghi nhận tiến trình"},
    "sleep":        {"hour": 22, "minute": 30, "label": "😴 Đi ngủ sớm"},
}
