"""
core/chat_engine.py — Hàm ask() chính và quản lý lịch sử hội thoại.

Đây là module trung tâm, điều phối toàn bộ luồng xử lý:
  1. Build history context (summary + recent)
  2. Chuẩn hóa query (Query Rewriting)
  3. Retrieve từ VectorStore
  4. Đánh giá retrieval → fallback Google Search
  5. Gọi chain chính để sinh câu trả lời
"""

from core.config import vectorstore
from core.chains import chain, summary_chain, rewrite_chain
from core.retrieval import evaluate_retrieval_sufficiency, build_web_context
from search.google import search_on_google


def summarize_old_history(old_messages: list[dict]) -> str:
    """
    Gọi LLM để tóm tắt các lượt hội thoại cũ (trước 3 lượt gần nhất).
 
    Args:
        old_messages: Danh sách message cũ (mỗi phần tử là dict role/content).
 
    Returns:
        Chuỗi tóm tắt từ LLM.
    """
    lines = []
    for msg in old_messages:
        role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý"
        lines.append(f"{role_label}: {msg['content']}")
    old_history_text = "\n".join(lines)
 
    return summary_chain.invoke({"old_history": old_history_text})


def build_history_context(chat_history: list[dict]) -> tuple[str, str]:
    """
    Tách lịch sử thành:
    - summary: tóm tắt các lượt cũ hơn 3 lượt (chỉ gọi LLM khi có > 3 lượt)
    - recent_history: 3 lượt gần nhất dạng văn bản
 
    Mỗi "lượt" = 1 cặp user + assistant = 2 message.
 
    Returns:
        (summary_text, recent_history_text)
    """
    RECENT_TURNS = 3
    recent_messages = chat_history[-(RECENT_TURNS * 2):]  # 3 lượt × 2 message
    old_messages = chat_history[:-(RECENT_TURNS * 2)]     # phần còn lại
 
    # Format 3 lượt gần nhất
    if recent_messages:
        recent_lines = []
        for msg in recent_messages:
            role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            recent_lines.append(f"{role_label}: {msg['content']}")
        recent_history_text = "\n".join(recent_lines)
    else:
        recent_history_text = "Chưa có lịch sử hội thoại."
 
    # Tóm tắt lịch sử cũ (chỉ khi có > 3 lượt)
    total_turns = len(chat_history) // 2
    if total_turns > RECENT_TURNS and old_messages:
        print("[Đang tóm tắt lịch sử hội thoại cũ...]")
        summary_text = summarize_old_history(old_messages)
    else:
        summary_text = "Không có."
 
    return summary_text, recent_history_text


def ask(query: str, chat_history: list[dict]) -> dict:
    """
    Nhận câu hỏi và lịch sử chat, trả về câu trả lời từ LLM kèm context.
 
    Luồng xử lý:
      1. Build history context (summary + recent)
      2. Chuẩn hóa query (nếu có lịch sử)
      3. Retrieve Top 3 từ VectorStore
      4. Đánh giá context bằng Qwen3-32b
         - SUFFICIENT → dùng context nội bộ
         - INSUFFICIENT → bổ sung bằng Google Search
      5. Gọi chain chính với context đã được bổ sung (nếu cần)
 
    Args:
        query: Câu hỏi hiện tại của người dùng.
        chat_history: Danh sách dict {"role": ..., "content": ...}.
 
    Returns:
        Dict gồm:
          - "answer": Chuỗi câu trả lời từ mô hình.
          - "contexts": Danh sách dict chứa nội dung và metadata.
          - "used_web_search": Boolean — có dùng Google Search không.
    """
    # ── Bước 1: Tách lịch sử thành summary (cũ) + recent (3 lượt gần nhất)
    summary, recent_history = build_history_context(chat_history)
 
    # ── Bước 2: Chuẩn hóa Query
    if recent_history != "Chưa có lịch sử hội thoại.":
        print("\n[Đang chuẩn hóa câu truy vấn...]")
        standalone_query = rewrite_chain.invoke({
            "history": recent_history,
            "query": query
        }).strip()
        print(f"[Query sau chuẩn hóa]: {standalone_query}")
    else:
        standalone_query = query
 
    # ── Bước 3: Retrieve Top 3 từ VectorStore
    print("\n[Đang truy xuất tài liệu nội bộ...]")
    docs = vectorstore.similarity_search(standalone_query, k=3)
    internal_context = "\n\n".join(
        f"Metadata: {doc.page_content}"
        for doc in docs
    )
 
    # Thu thập context nội bộ cho UI
    contexts_for_ui = []
    for i, doc in enumerate(docs):
        contexts_for_ui.append({
            "index": i + 1,
            "content": doc.page_content,
            "metadata": doc.metadata if doc.metadata else {},
            "type": "internal",
        })
 
    # ── Bước 4: Đánh giá retrieval với Qwen3-32b
    is_sufficient = evaluate_retrieval_sufficiency(standalone_query, internal_context)
    used_web_search = False
    final_context = internal_context
 
    if not is_sufficient:
        # ── Bước 4b: Fallback — tìm kiếm Google và gộp context
        print(f"\n[Đang tìm kiếm bổ sung trên Google: '{standalone_query}'...]")
        web_results = search_on_google(standalone_query, num_results=3)
 
        if web_results:
            web_context_text, web_contexts_for_ui = build_web_context(web_results)
            used_web_search = True
 
            # Gộp context: nội bộ trước, web sau
            final_context = (
                "=== Tài liệu dược thư quốc gia ===\n"
                + internal_context
                + "\n\n=== Kết quả tìm kiếm Internet ===\n"
                + web_context_text
            )
 
            # Đánh số lại index cho web contexts
            for wc in web_contexts_for_ui:
                wc["index"] += len(contexts_for_ui)
            contexts_for_ui.extend(web_contexts_for_ui)
 
            print(f"[Đã bổ sung {len(web_results)} nguồn web vào context.]")
        else:
            print("[Không tìm thấy kết quả web phù hợp, tiếp tục với context nội bộ.]")
 
    # ── Bước 5: Gọi chain chính
    answer = chain.invoke({
        "context": final_context,
        "summary": summary,
        "recent_history": recent_history,
        "query": query,
    })
 
    return {
        "answer": answer,
        "contexts": contexts_for_ui,
        "used_web_search": used_web_search,
    }


# ──────────────────────────────────────────────
# Vòng lặp chat chính (CLI)
# ──────────────────────────────────────────────
def main():
    print("=== Dược sĩ lâm sàng AI (nhập 'exit' để thoát) ===\n")
    chat_history: list[dict] = []
 
    while True:
        query = input("Bạn: ").strip()
        if not query:
            continue
        if query.lower() in ("exit", "quit", "thoát"):
            print("Tạm biệt!")
            break
 
        result = ask(query, chat_history)
        answer = result["answer"]
 
        # Lưu vào lịch sử
        chat_history.append({"role": "user", "content": query})
        chat_history.append({"role": "assistant", "content": answer})
 
        # Hiển thị kết quả
        source_label = "GROQ + WEB SEARCH" if result["used_web_search"] else "GROQ (NỘI BỘ)"
        print(f"\n=== CÂU TRẢ LỜI TỪ {source_label} ===")
        print(answer)
        print()
 
 
if __name__ == "__main__":
    main()
