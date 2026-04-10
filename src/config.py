"""Configuration settings for the Finance Bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
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

# ─── AI (set ONE — Groq recommended for free tier) ──────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")      # https://console.groq.com
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")   # https://aistudio.google.com/apikey

# ─── Database ────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "finance.db"))

# ─── Defaults ────────────────────────────────────────────────────────
TIMEZONE = "Asia/Ho_Chi_Minh"
DEFAULT_CURRENCY = "VND"
# USD_TO_VND_RATE: fetched live from currency_service (no hardcoded value)

# ─── Budget defaults (50/30/20 rule) ────────────────────────────────
DEFAULT_NEEDS_PCT = 50
DEFAULT_WANTS_PCT = 30
DEFAULT_SAVINGS_PCT = 20
