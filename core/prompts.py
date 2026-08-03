"""
core/prompts.py — Tất cả Prompt Templates cho hệ thống PharmaRAG.

Tách riêng prompt để dễ chỉnh sửa nội dung prompt
mà không cần đụng vào logic xử lý.
"""

from langchain_core.prompts import PromptTemplate

# ──────────────────────────────────────────────
# 1. Prompt chính — Trả lời câu hỏi dược (có summary + 3 lịch sử gần nhất)
# ──────────────────────────────────────────────
MAIN_PROMPT_TEMPLATE = """
Bạn là một dược sĩ lâm sàng giàu kinh nghiệm. Hãy sử dụng CÁC THÔNG TIN TRONG PHẦN NGỮ CẢNH dưới đây để trả lời câu hỏi của người dùng một cách chính xác và dễ hiểu.
Nếu thông tin trong Ngữ cảnh không đủ để trả lời, hãy nói rõ là "Tài liệu hiện tại không chứa đủ thông tin để trả lời câu hỏi này", tuyệt đối không tự bịa ra kiến thức ngoài.
 
Ngữ cảnh tài liệu (Context):
{context}
 
Tóm tắt các cuộc hội thoại cũ (Summary of older history):
{summary}
 
Lịch sử hội thoại gần nhất (3 lượt gần nhất):
{recent_history}
 
Câu hỏi của người dùng (Query):
{query}
 
Câu trả lời:
"""

main_prompt = PromptTemplate(
    template=MAIN_PROMPT_TEMPLATE,
    input_variables=["context", "summary", "recent_history", "query"]
)

# ──────────────────────────────────────────────
# 2. Prompt tóm tắt lịch sử cũ
# ──────────────────────────────────────────────
SUMMARY_PROMPT_TEMPLATE = """
Hãy tóm tắt ngắn gọn nội dung các cuộc hội thoại dưới đây giữa người dùng và trợ lý dược sĩ lâm sàng AI.
Tóm tắt cần nắm bắt các chủ đề chính, câu hỏi quan trọng và thông tin y dược đã được đề cập.
Viết bằng tiếng Việt, súc tích trong khoảng 4-5 câu.
 
Lịch sử hội thoại cần tóm tắt:
{old_history}
 
Tóm tắt:
"""

summary_prompt = PromptTemplate(
    template=SUMMARY_PROMPT_TEMPLATE,
    input_variables=["old_history"]
)

# ──────────────────────────────────────────────
# 3. Prompt chuẩn hóa câu hỏi (Query Rewriting)
# ──────────────────────────────────────────────
REWRITE_PROMPT_TEMPLATE = """
Bạn là một chuyên gia xử lý ngôn ngữ tự nhiên trong hệ thống Tra cứu thuốc. 

Nhiệm vụ của bạn là phân tích "Lịch sử trò chuyện" và "Câu hỏi hiện tại" để viết lại câu hỏi thành CÂU TRUY VẤN ĐỘC LẬP (Standalone Query). Câu truy vấn mới phải tối ưu cho hệ thống tìm kiếm ngữ nghĩa (Vector Search / Semantic Search) trong cơ sở dữ liệu y khoa.

### QUY TẮC BẮT BUỘC:
1. KHÔI PHỤC NGỮ CẢNH: Thay thế tất cả các đại từ (nó, thuốc này, vị thuốc đó, bệnh nhân, người này...) hoặc ý bị ẩn bằng tên thuốc, tên dược chất (INN), nhóm thuốc, hoặc bệnh lý cụ thể được nhắc đến trong lịch sử trò chuyện.
2. CHUYÊN MÔN HÓA: Bổ sung từ khóa ngữ nghĩa y khoa/dược học rõ ràng (ví dụ: chỉ định, chống chỉ định, liều dùng, tác dụng phụ/ADR, tương tác thuốc, cơ chế tác dụng, cách dùng cho bà bầu/trẻ em...).
3. LOẠI BỎ TỪ THỪA: Loại bỏ hoàn toàn các từ giao tiếp, xã giao (chào bạn, cảm ơn, cho mình hỏi, tư vấn giúp, nhé, ạ,...) và các cấu trúc câu nghi vấn không cần thiết.
4. ĐỘC LẬP & NGUYÊN BẢN: 
   - Nếu câu hỏi hiện tại ĐÃ ĐẦY ĐỦ chủ ngữ, tên thuốc/bệnh và ngữ nghĩa chuyên môn, hoặc LÀ MỘT CHỦ ĐỀ MỚI không liên quan đến lịch sử: Giữ nguyên nội dung cốt lõi của câu hỏi, chỉ cần loại bỏ từ giao tiếp.
   - KHÔNG tự bịa ra thông tin y khoa hoặc tên thuốc không xuất hiện trong lịch sử.
5. ĐỊNH DẠNG ĐẦU RA (RẮC RỐI TỐI THIỂU):
   - CHỈ xuất ra duy nhất 1 câu truy vấn đã viết lại.
   - KHÔNG trả lời câu hỏi, KHÔNG giải thích, KHÔNG thêm tiền tố (như "Câu truy vấn:", "Dưới đây là..."), KHÔNG dùng dấu ngoặc kép.

---

Lịch sử trò chuyện gần nhất:
{history}

Câu hỏi hiện tại:
{query}

Câu truy vấn độc lập:
"""

rewrite_prompt = PromptTemplate(
    template=REWRITE_PROMPT_TEMPLATE,
    input_variables=["history", "query"]
)


