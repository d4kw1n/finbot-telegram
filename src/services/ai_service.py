"""AI Service — Multi-provider AI integration for smart finance features.

Supported providers (in priority order):
  1. Groq (FREE, fast, generous quota) — Llama 3.3 70B
  2. Google Gemini 2.0 Flash (FREE but limited quota)

Set ONE of these in .env:
  GROQ_API_KEY=gsk_xxx      (recommended — get free at https://console.groq.com)
  GEMINI_API_KEY=xxx         (fallback — get free at https://aistudio.google.com/apikey)

Features:
  - Auto-categorize transactions when keyword matching fails
  - Generate financial insights from spending data
  - Provide personalized financial advice
  - Auto-retry on rate limit with exponential backoff
"""
import asyncio
import json
import logging

import httpx

from src.config import GEMINI_API_KEY, GROQ_API_KEY

logger = logging.getLogger(__name__)

# ─── State ────────────────────────────────────────────────────────────
_provider = None   # "groq" | "gemini" | None
_client = None     # genai.Client for Gemini
_available = False

# Retry settings
_MAX_RETRIES = 3
_BASE_DELAY = 10  # seconds


def init_ai():
    """Initialize AI provider. Tries Groq first, then Gemini."""
    global _provider, _client, _available

    # 1. Try Groq (preferred — better free tier)
    if GROQ_API_KEY:
        _provider = "groq"
        _available = True
        logger.info("✅ AI initialized with Groq (Llama 3.3 70B)")
        return

    # 2. Try Gemini
    if GEMINI_API_KEY:
        try:
            from google import genai
            _client = genai.Client(api_key=GEMINI_API_KEY)
            _provider = "gemini"
            _available = True
            logger.info("✅ AI initialized with Google Gemini 2.0 Flash")
            return
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")

    logger.info("⚠️ No AI API key set — AI features disabled.")
    logger.info("  Get FREE Groq key: https://console.groq.com")
    logger.info("  Or Gemini key: https://aistudio.google.com/apikey")
    _available = False


def is_available() -> bool:
    """Check if AI service is ready."""
    return _available


# ═════════════════════════════════════════════════════════════════════
# Core generation with retry
# ═════════════════════════════════════════════════════════════════════

async def _generate(prompt: str, temperature: float = 0.5,
                    max_tokens: int = 500) -> str | None:
    """Generate content with auto-retry on rate limit."""
    if _provider == "groq":
        return await _groq_generate(prompt, temperature, max_tokens)
    elif _provider == "gemini":
        return await _gemini_generate(prompt, temperature, max_tokens)
    return None


async def _groq_generate(prompt: str, temperature: float,
                         max_tokens: int) -> str | None:
    """Call Groq API (OpenAI-compatible)."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "Bạn là chuyên gia tài chính cá nhân Việt Nam."},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if resp.status_code == 429:
                    delay = _BASE_DELAY * (2 ** attempt)
                    logger.warning(f"⏳ Groq rate limited, retry in {delay}s...")
                    await asyncio.sleep(delay)
                    continue

                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(f"⏳ Groq rate limited, retry in {delay}s...")
                await asyncio.sleep(delay)
                continue
            logger.error(f"Groq API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return None

    logger.error("Groq: all retries exhausted.")
    return None


async def _gemini_generate(prompt: str, temperature: float,
                           max_tokens: int) -> str | None:
    """Call Gemini API."""
    from google.genai import types

    for attempt in range(_MAX_RETRIES):
        try:
            response = await _client.aio.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
            return response.text.strip()

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                delay = _BASE_DELAY * (2 ** attempt)
                logger.warning(f"⏳ Gemini rate limited, retry in {delay}s...")
                await asyncio.sleep(delay)
                continue
            logger.error(f"Gemini error: {e}")
            return None

    logger.error("Gemini: all retries exhausted.")
    return None


# ═════════════════════════════════════════════════════════════════════
# Public API
# ═════════════════════════════════════════════════════════════════════

async def categorize_transaction(description: str,
                                  categories: list[dict]) -> dict | None:
    """Use AI to categorize a transaction."""
    if not _available:
        return None

    cats_text = "\n".join(
        f"  ID={c['id']}: {c['emoji']} {c['name']} (loại: {c['type']})"
        for c in categories
    )

    prompt = (
        "Phân loại khoản chi tiêu sau vào MỘT danh mục phù hợp nhất.\n\n"
        f"Danh mục:\n{cats_text}\n\n"
        f'Mô tả: "{description}"\n\n'
        "Trả về CHỈ JSON (không giải thích):\n"
        '{"category_id": <số>, "confidence": <0-100>}'
    )

    text = await _generate(prompt, temperature=0.3, max_tokens=100)
    if not text:
        return None

    try:
        # Extract JSON from possible markdown code block
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        result = json.loads(text)
        if "category_id" in result and "confidence" in result:
            return result
    except (json.JSONDecodeError, KeyError):
        logger.error(f"AI categorize: invalid response: {text}")

    return None


async def get_financial_insight(spending_data: dict) -> str:
    """Generate AI-powered financial insights."""
    if not _available:
        return ("💡 Thêm GROQ_API_KEY hoặc GEMINI_API_KEY vào .env "
                "để nhận phân tích AI.")

    prompt = (
        "Phân tích dữ liệu chi tiêu sau:\n\n"
        f"{json.dumps(spending_data, ensure_ascii=False, default=str)}\n\n"
        "Yêu cầu:\n"
        "1. Nhận xét tổng quan (1-2 câu)\n"
        "2. 1 điểm tích cực\n"
        "3. 1 điểm cần cải thiện\n"
        "4. 1 lời khuyên cụ thể\n\n"
        "Trả lời ngắn gọn (tối đa 200 từ), bằng tiếng Việt, dùng emoji. "
        "KHÔNG dùng markdown heading (#). KHÔNG dùng ký tự _ hoặc *."
    )

    result = await _generate(prompt, temperature=0.5, max_tokens=500)
    return result or "⚠️ Không thể tạo phân tích AI lúc này. Thử lại sau."


async def get_advice(question: str, context_data: dict) -> str:
    """Get personalized financial advice from AI."""
    if not _available:
        return ("💡 Thêm GROQ_API_KEY hoặc GEMINI_API_KEY vào .env "
                "để sử dụng tư vấn AI.")

    prompt = (
        f'Người dùng hỏi:\n"{question}"\n\n'
        "Bối cảnh tài chính:\n"
        f"{json.dumps(context_data, ensure_ascii=False, default=str)}\n\n"
        "Trả lời bằng tiếng Việt, thân thiện, thực tế. "
        "Tối đa 300 từ. Dùng emoji cho sinh động. "
        "KHÔNG dùng markdown heading (#). KHÔNG dùng ký tự _ hoặc *."
    )

    result = await _generate(prompt, temperature=0.7, max_tokens=600)
    return result or "⚠️ Không thể tư vấn lúc này. Vui lòng thử lại sau."
