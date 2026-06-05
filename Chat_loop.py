import os
from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from Search_On_Google import search_on_google

# Tải biến môi trường từ file .env
load_dotenv()

# ──────────────────────────────────────────────
# 1. Khởi tạo Embeddings & VectorStore
# ──────────────────────────────────────────────
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large"
)

vectorstore = FAISS.load_local(
    r"D:\PharmaRAG-VN\Data\VectorStore\faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)

# ──────────────────────────────────────────────
# 2. Prompt Template chính (có summary + 3 lịch sử gần nhất)
# ──────────────────────────────────────────────
prompt_template = """
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

prompt = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "summary", "recent_history", "query"]
)

# ──────────────────────────────────────────────
# 3. Khởi tạo LLM với Groq
# ──────────────────────────────────────────────
# Llama-3-70B hiện là một trong những model mã nguồn mở tốt nhất,
# suy luận logic cực tốt và hỗ trợ tiếng Việt khá ổn.
llm = ChatGroq(
    temperature=0,
    model_name="llama-3.3-70b-versatile"
    # Bạn cũng có thể thử: "mixtral-8x7b-32768" hoặc "gemma2-9b-it"
)

# ──────────────────────────────────────────────
# 4. Prompt Template để summary lịch sử cũ
# ──────────────────────────────────────────────
summary_prompt_template = """
Hãy tóm tắt ngắn gọn nội dung các cuộc hội thoại dưới đây giữa người dùng và trợ lý dược sĩ lâm sàng AI.
Tóm tắt cần nắm bắt các chủ đề chính, câu hỏi quan trọng và thông tin y dược đã được đề cập.
Viết bằng tiếng Việt, súc tích trong khoảng 4-5 câu.
 
Lịch sử hội thoại cần tóm tắt:
{old_history}
 
Tóm tắt:
"""
 
summary_prompt = PromptTemplate(
    template=summary_prompt_template,
    input_variables=["old_history"]
)
 
summary_chain = summary_prompt | llm | StrOutputParser()

# ──────────────────────────────────────────────
# 5. Khởi tọa Chain chuẩn hóa Query (Query Rewriting)
# ──────────────────────────────────────────────

# Chỉ sử dụng model nhỏ, tốc độ cao chỉ để viết lại câu hỏi.
fast_llm = ChatGroq(
    temperature=0,
    model_name="llama-3.1-8b-instant"
    # Bạn cũng có thể thử: "mixtral-8x7b-32768" hoặc "gemma2-9b-it"
)

rewrite_prompt_template = """
Bạn là một trợ lý AI xử lý ngôn ngữ. Dựa vào lịch sử trò chuyện dưới đây, hãy viết lại câu hỏi hiện tại của người dùng thành một câu truy vấn độc lập, đầy đủ chủ ngữ, danh từ chuyên môn và ngữ nghĩa để phục vụ cho hệ thống tìm kiếm tài liệu y khoa.
Nếu câu hỏi đã đầy đủ ý nghĩa hoặc không liên quan đến lịch sử, hãy giữ nguyên.
KHÔNG trả lời câu hỏi, KHÔNG giải thích, CHỈ in ra câu hỏi đã được viết lại.

Lịch sử trò chuyện gần nhất:
{history}

Câu hỏi hiện tại: {query}

Câu truy vấn độc lập:
"""

rewrite_prompt = PromptTemplate(
    template=rewrite_prompt_template,
    input_variables=["history", "query"]
)

rewrite_chain = rewrite_prompt | fast_llm | StrOutputParser()


# ──────────────────────────────────────────────
# 6. Khởi tạo LLM đánh giá Retrieval (Qwen3-32b)
# ──────────────────────────────────────────────
# Qwen3-32b có khả năng suy luận tốt, phù hợp để đánh giá mức độ liên quan.
# Lưu ý: Groq hỗ trợ qwen/qwen3-32b qua OpenAI-compatible endpoint.
eval_llm = ChatGroq(
    temperature=0,
    model_name="qwen/qwen3-32b"
)

retrieval_eval_prompt_template = """
Bạn là một chuyên gia đánh giá chất lượng thông tin y dược. Nhiệm vụ của bạn là đánh giá xem ngữ cảnh được truy xuất có đủ thông tin để trả lời câu hỏi của người dùng hay không.
 
Câu hỏi của người dùng:
{query}
 
Ngữ cảnh đã truy xuất từ tài liệu nội bộ:
{context}
 
Hãy đánh giá theo các tiêu chí sau:
1. Ngữ cảnh có đề cập trực tiếp hoặc liên quan chặt chẽ đến chủ đề của câu hỏi không?
2. Thông tin trong ngữ cảnh có đủ chi tiết để đưa ra câu trả lời đáng tin cậy không?
3. Có thiếu các thông tin quan trọng mà câu hỏi yêu cầu không?
 
Chỉ trả lời MỘT trong hai từ sau (không thêm bất kỳ nội dung nào khác):
- SUFFICIENT: nếu ngữ cảnh đủ để trả lời câu hỏi
- INSUFFICIENT: nếu ngữ cảnh không đủ hoặc không liên quan
"""

retrieval_eval_prompt = PromptTemplate(
    template=retrieval_eval_prompt_template,
    input_variables=["query", "context"]
)

retrieval_eval_chain = retrieval_eval_prompt | eval_llm | StrOutputParser()
 

# ──────────────────────────────────────────────
# 7. Kết nối thành một Chain chính
# ──────────────────────────────────────────────
chain = prompt | llm | StrOutputParser()

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
 
    # Chỉ lấy từ đầu tiên để tránh model trả về text dư thừa
    first_word = verdict.split()[0] if verdict else "INSUFFICIENT"
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
                "=== Tài liệu nội bộ ===\n"
                + internal_context
                + "\n\n=== Kết quả tìm kiếm Web ===\n"
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
# 6. Vòng lặp chat chính
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
