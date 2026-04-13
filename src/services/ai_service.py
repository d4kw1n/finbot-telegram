"""AI Service — Multi-provider integration for finance + fitness.

Supported providers:
  1. Groq (FREE, fast) — Llama 3.3 70B
  2. Google Gemini 2.0 Flash (via REST API, no SDK needed)

Set ONE of these in .env:
  GROQ_API_KEY=gsk_xxx
  GEMINI_API_KEY=xxx
"""
import asyncio
import json
import logging

import httpx

from src.config import GEMINI_API_KEY, GROQ_API_KEY, AI_API_KEY, AI_PROVIDER

logger = logging.getLogger(__name__)

_provider = None
_api_key = None
_available = False

_MAX_RETRIES = 3
_BASE_DELAY = 10


def init_ai():
    """Initialize AI provider. Tries Groq first, then Gemini."""
    global _provider, _api_key, _available

    if GROQ_API_KEY:
        _provider = "groq"
        _api_key = GROQ_API_KEY
        _available = True
        logger.info("✅ AI initialized with Groq (Llama 3.3 70B)")
        return

    if GEMINI_API_KEY:
        _provider = "gemini"
        _api_key = GEMINI_API_KEY
        _available = True
        logger.info("✅ AI initialized with Google Gemini 2.0 Flash")
        return

    if AI_API_KEY and AI_PROVIDER:
        _provider = AI_PROVIDER
        _api_key = AI_API_KEY
        _available = True
        logger.info(f"✅ AI initialized with {AI_PROVIDER}")
        return

    logger.info("⚠️ No AI API key set — AI features disabled.")
    _available = False


def is_available() -> bool:
    return _available


async def _generate(prompt: str, temperature: float = 0.5,
                    max_tokens: int = 500) -> str | None:
    if _provider == "groq":
        return await _groq_generate(prompt, temperature, max_tokens)
    elif _provider == "gemini":
        return await _gemini_generate(prompt, temperature, max_tokens)
    return None


async def _groq_generate(prompt: str, temperature: float,
                         max_tokens: int) -> str | None:
    headers = {
        "Authorization": f"Bearer {_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system",
             "content": "Bạn là chuyên gia tài chính và thể hình cá nhân Việt Nam."},
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
                    headers=headers, json=payload,
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
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.0-flash:generateContent?key={_api_key}"
    )

    for attempt in range(_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": temperature,
                    },
                })
                if resp.status_code == 429:
                    delay = _BASE_DELAY * (2 ** attempt)
                    logger.warning(f"⏳ Gemini rate limited, retry in {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                delay = _BASE_DELAY * (2 ** attempt)
                await asyncio.sleep(delay)
                continue
            logger.error(f"Gemini API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return None

    logger.error("Gemini: all retries exhausted.")
    return None


# ═════════════════════════════════════════════════════════════════════
# Finance-specific public API
# ═════════════════════════════════════════════════════════════════════

async def categorize_transaction(description: str,
                                  categories: list[dict]) -> dict | None:
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
