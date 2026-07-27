"""
core/config.py — Khởi tạo Embeddings, VectorStore và các LLM instances.

Tập trung toàn bộ cấu hình mô hình và kết nối dữ liệu tại đây
để các module khác chỉ cần import sử dụng.
"""

import os
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Tải biến môi trường từ file .env
load_dotenv()

# ──────────────────────────────────────────────
# 1. Khởi tạo Embeddings & VectorStore
# ──────────────────────────────────────────────
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large"
)

FAISS_INDEX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Data", "VectorStore", "faiss_index"
)

vectorstore = FAISS.load_local(
    FAISS_INDEX_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)

# ──────────────────────────────────────────────
# 2. LLM chính — Llama-3.3-70B (suy luận logic tốt, hỗ trợ tiếng Việt)
# ──────────────────────────────────────────────
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile"
)

# ──────────────────────────────────────────────
# 3. LLM nhỏ, tốc độ cao — chỉ để viết lại câu hỏi (Query Rewriting)
# ──────────────────────────────────────────────
fast_llm = ChatGroq(
    temperature=0,
    model_name="llama-3.1-8b-instant"
)

# ──────────────────────────────────────────────
# 4. LLM trung — Qwen3-32b — dùng cho tóm tắt lịch sử hội thoại
# ──────────────────────────────────────────────
mid_llm = ChatGroq(
    temperature=0,
    model_name="qwen/qwen3-32b"
)

# ──────────────────────────────────────────────
# 5. Jina Reranker v3 — Cấu hình API
# ──────────────────────────────────────────────
JINA_RERANKER_URL = "https://api.jina.ai/v1/rerank"
JINA_RERANKER_MODEL = "jina-reranker-v3"
JINA_API_KEY = os.getenv("JINA_API_KEY")
