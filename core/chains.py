"""
core/chains.py — Tạo các LangChain chains từ prompts và LLM instances.

Mỗi chain kết hợp một PromptTemplate với một LLM và StrOutputParser.
"""

from langchain_core.output_parsers import StrOutputParser

from core.config import llm, fast_llm, mid_llm
from core.prompts import main_prompt, summary_prompt, rewrite_prompt

# ──────────────────────────────────────────────
# 1. Chain chính — Trả lời câu hỏi dược
# ──────────────────────────────────────────────
chain = main_prompt | llm | StrOutputParser()

# ──────────────────────────────────────────────
# 2. Chain tóm tắt lịch sử hội thoại cũ — dùng Qwen3-32b
# ──────────────────────────────────────────────
summary_chain = summary_prompt | mid_llm | StrOutputParser()

# ──────────────────────────────────────────────
# 3. Chain chuẩn hóa câu hỏi (Query Rewriting) — dùng model nhỏ, nhanh
# ──────────────────────────────────────────────
rewrite_chain = rewrite_prompt | fast_llm | StrOutputParser()
