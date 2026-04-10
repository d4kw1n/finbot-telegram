#!/usr/bin/env python3
"""FinBot — Personal Finance Management Telegram Bot.

Usage:
    python run.py

Ensure .env file has BOT_TOKEN set.
Optionally set GEMINI_API_KEY for AI features.
"""
import sys
from pathlib import Path

# Add project root to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from src.bot.app import create_app


def main():
    """Start the bot (synchronous entry point)."""
    import logging
    logging.basicConfig(
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting FinBot...")

    app = create_app()
    # run_polling manages its own event loop
    # bootstrap_retries: retry connecting to Telegram API on startup failures
    app.run_polling(
        drop_pending_updates=True,
        bootstrap_retries=5,  # Retry up to 5 times if Telegram API is unreachable
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 FinBot stopped.")
