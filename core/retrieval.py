"""
core/retrieval.py — Logic đánh giá chất lượng retrieval và xây dựng web context.

Chứa:
- evaluate_retrieval_sufficiency: Dùng Qwen3-32b đánh giá context đủ/không đủ.
- build_web_context: Chuyển đổi kết quả Google Search thành context text + UI data.
"""

import re

from core.chains import retrieval_eval_chain


def evaluate_retrieval_sufficiency(query: str, context: str) -> bool:
    """
    Dùng Qwen3-32b để đánh giá context có đủ để trả lời câu hỏi không.
 
    Args:
        query: Câu hỏi của người dùng (đã được chuẩn hóa).
        context: Văn bản context đã retrieve từ VectorStore.
 
    Returns:
        True nếu context đủ (SUFFICIENT), False nếu không đủ (INSUFFICIENT).
    """
    print("\n[Đang đánh giá chất lượng retrieval với Qwen3-32b...]")
    verdict = retrieval_eval_chain.invoke({
        "query": query,
        "context": context
    }).strip().upper()

    print(f"[Raw Verdict]: {verdict}")
 
    # Dùng Regex để loại bỏ toàn bộ thẻ <THINK>...</THINK> và nội dung bên trong
    clean_verdict = re.sub(r'<THINK>.*?</THINK>', '', verdict, flags=re.DOTALL | re.IGNORECASE).strip()
    
    # Lấy từ đầu tiên của chuỗi ĐÃ ĐƯỢC LÀM SẠCH
    first_word = clean_verdict.split()[0] if clean_verdict else "INSUFFICIENT"
    is_sufficient = first_word == "SUFFICIENT"
 
    print(f"[Kết quả đánh giá]: {first_word} → {'✅ Đủ thông tin' if is_sufficient else '⚠️ Không đủ, sẽ tìm kiếm Google'}")
    return is_sufficient


def build_web_context(web_results: list[dict]) -> tuple[str, list[dict]]:
    """
    Chuyển đổi kết quả từ search_on_google thành context text và danh sách UI.
 
    Args:
        web_results: Danh sách dict {"source_url": ..., "markdown_content": ...}.
 
    Returns:
        (context_text, contexts_for_ui)
    """
    context_lines = []
    contexts_for_ui = []
 
    for i, item in enumerate(web_results):
        source = item.get("source_url", "Không rõ nguồn")
        content = item.get("markdown_content", "").strip()
        if content:
            context_lines.append(f"[Nguồn Web {i+1}] {source}\n{content}")
            contexts_for_ui.append({
                "index": i + 1,
                "content": content,
                "metadata": {"source": source, "type": "web_search"},
            })
 
    return "\n\n".join(context_lines), contexts_for_ui
