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
Bạn là một trợ lý AI xử lý ngôn ngữ. Dựa vào lịch sử trò chuyện dưới đây, hãy viết lại câu hỏi hiện tại của người dùng thành một câu truy vấn độc lập, đầy đủ chủ ngữ, danh từ chuyên môn và ngữ nghĩa để phục vụ cho hệ thống tìm kiếm tài liệu y khoa.
Nếu câu hỏi đã đầy đủ ý nghĩa hoặc không liên quan đến lịch sử, hãy giữ nguyên.
KHÔNG trả lời câu hỏi, KHÔNG giải thích, CHỈ in ra câu hỏi đã được viết lại.

Lịch sử trò chuyện gần nhất:
{history}

Câu hỏi hiện tại: {query}

Câu truy vấn độc lập:
"""

rewrite_prompt = PromptTemplate(
    template=REWRITE_PROMPT_TEMPLATE,
    input_variables=["history", "query"]
)


