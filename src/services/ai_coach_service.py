"""AI Fitness Coach — uses the unified AI service for fitness-specific queries."""
import logging
from src.services.ai_service import is_available, _generate
from src.config import GROQ_API_KEY, GEMINI_API_KEY, AI_API_KEY, AI_PROVIDER

logger = logging.getLogger(__name__)

FITNESS_SYSTEM_PROMPT = """Bạn là một huấn luyện viên thể hình và chuyên gia dinh dưỡng chuyên nghiệp.
Bạn đang hỗ trợ một nam giới Việt Nam trong hành trình tăng cân và xây dựng cơ bắp.

Nguyên tắc:
- Trả lời bằng tiếng Việt, thân thiện nhưng chuyên nghiệp
- Dựa trên khoa học và bằng chứng (evidence-based)
- Luôn khuyến khích và tạo động lực
- Đưa ra lời khuyên cụ thể, thực tế
- Nếu câu hỏi liên quan y tế, khuyên người dùng tham khảo bác sĩ
- Tập trung vào: dinh dưỡng, bài tập, hồi phục, tâm lý
- Không khuyến khích sử dụng PED (performance enhancing drugs)
- Trả lời ngắn gọn, dưới 500 từ
- KHÔNG dùng markdown heading (#). KHÔNG dùng ký tự _ hoặc *.
"""


async def ask_fitness_ai(user_message: str,
                         user_context: dict | None = None) -> str:
    if not is_available():
        return _offline_response(user_message)

    context_str = ""
    if user_context:
        context_str = (
            f"\n\nThông tin người dùng: "
            f"Cân nặng: {user_context.get('weight', '?')}kg, "
            f"Chiều cao: {user_context.get('height', '?')}cm, "
            f"Tuổi: {user_context.get('age', '?')}, "
            f"Mục tiêu: tăng cân lên {user_context.get('target_weight', '?')}kg, "
            f"TDEE: {user_context.get('tdee', '?')}kcal, "
            f"Calories/ngày: {user_context.get('daily_calories', '?')}kcal"
        )

    full_prompt = FITNESS_SYSTEM_PROMPT + "\n\nNgười dùng hỏi:\n" + user_message + context_str

    result = await _generate(full_prompt, temperature=0.7, max_tokens=1024)
    return result or _offline_response(user_message)


def get_provider_info() -> str:
    if not is_available():
        return (
            "⚠️ AI Coach chưa được cấu hình.\n\n"
            "🆓 Lấy API key MIỄN PHÍ:\n\n"
            "1️⃣ Groq (khuyến nghị):\n"
            "   → https://console.groq.com/keys\n"
            "   Không cần thẻ tín dụng!\n\n"
            "2️⃣ Gemini:\n"
            "   → https://aistudio.google.com/apikey\n"
            "   Không cần thẻ tín dụng!\n\n"
            "Sau đó điền vào .env:\n"
            "   GROQ_API_KEY=<key của bạn>"
        )
    return "✅ AI Coach sẵn sàng"


def _offline_response(message: str) -> str:
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["protein", "đạm"]):
        return (
            "🥩 Protein rất quan trọng cho tăng cơ! Với cân nặng của bạn, "
            "hãy nạp 1.6-2.2g protein/kg cân nặng mỗi ngày.\n\n"
            "Nguồn protein tốt: ức gà, cá hồi, trứng, whey protein, "
            "đậu nành, sữa Greek yogurt.\n\n"
            "Chia đều protein qua các bữa ăn trong ngày để tối ưu hấp thu!"
        )
    if any(kw in msg_lower for kw in ["creatine", "bổ sung", "supplement"]):
        return (
            "💊 Creatine Monohydrate là supplement được nghiên cứu nhiều nhất "
            "và hiệu quả nhất cho tăng sức mạnh và cơ bắp.\n\n"
            "Liều: 5g/ngày, uống hàng ngày (kể cả ngày nghỉ).\n"
            "Có thể pha với nước hoặc shake protein.\n\n"
            "Ngoài ra, whey protein giúp bạn đạt mục tiêu protein dễ dàng hơn."
        )
    if any(kw in msg_lower for kw in ["chấn thương", "đau", "injury"]):
        return (
            "⚠️ Nếu bạn bị đau hoặc chấn thương, hãy:\n\n"
            "1. Ngừng bài tập gây đau ngay lập tức\n"
            "2. Chườm đá 15-20 phút\n"
            "3. Nghỉ ngơi 2-3 ngày\n"
            "4. Nếu đau kéo dài, HÃY ĐI KHÁM BÁC SĨ\n\n"
            "Sức khỏe quan trọng hơn gainz! 💪"
        )
    if any(kw in msg_lower for kw in ["ngủ", "sleep", "nghỉ", "recover"]):
        return (
            "😴 Giấc ngủ cực kỳ quan trọng cho tăng cơ!\n\n"
            "• Ngủ 7-9 tiếng mỗi đêm\n"
            "• Hormone tăng trưởng tiết ra nhiều nhất khi ngủ sâu\n"
            "• Thiếu ngủ = giảm testosterone = giảm tăng cơ\n\n"
            "Tips: Tắt điện thoại 30 phút trước khi ngủ, "
            "phòng tối và mát (18-22°C)."
        )
    if any(kw in msg_lower for kw in ["động lực", "motivation", "chán", "bỏ"]):
        return (
            "🔥 Đừng bỏ cuộc! Nhớ rằng:\n\n"
            "• Mọi người bắt đầu từ con số 0\n"
            "• Kết quả đến sau 4-8 tuần tập đều\n"
            "• 1 buổi tập tệ vẫn tốt hơn 0 buổi\n"
            "• Bạn đang làm điều tuyệt vời cho bản thân!\n\n"
            "\"The only bad workout is the one that didn't happen.\" 💪"
        )
    return (
        "💪 Hãy nhớ: Consistency is key!\n\n"
        "Tập đều đặn, ăn đủ, ngủ đủ — đó là 3 trụ cột của tăng cơ.\n\n"
        "Bạn có thể hỏi tôi về:\n"
        "• Dinh dưỡng & macros\n"
        "• Bài tập & kỹ thuật\n"
        "• Supplements\n"
        "• Hồi phục & giấc ngủ\n"
        "• Động lực & mindset\n\n"
        "💡 Để có AI coach thông minh hơn, thêm GROQ_API_KEY vào .env!"
    )
