import os
from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
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
# 5. Kết nối thành một Chain chính
# ──────────────────────────────────────────────
chain = prompt | llm | StrOutputParser()

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
 
    Args:
        query: Câu hỏi hiện tại của người dùng.
        chat_history: Danh sách dict {"role": ..., "content": ...}.
 
    Returns:
        Dict gồm:
          - "answer": Chuỗi câu trả lời từ mô hình.
          - "contexts": Danh sách dict chứa nội dung và metadata của từng tài liệu đã truy vấn.
    """
    # Retrieve Top 5 tài liệu liên quan từ VectorStore
    docs = vectorstore.similarity_search(query, k=5)
    context = "\n\n".join(
        f"Metadata: {doc.page_content}"
        for doc in docs
    )

    # Thu thập thông tin context để hiển thị trên UI
    contexts_for_ui = []
    for i, doc in enumerate(docs):
        contexts_for_ui.append({
            "index": i + 1,
            "content": doc.page_content,
            "metadata": doc.metadata if doc.metadata else {},
        })
 
    # Tách lịch sử thành summary (cũ) + recent (3 lượt gần nhất)
    summary, recent_history = build_history_context(chat_history)
 
    # Gọi chain chính
    answer = chain.invoke({
        "context": context,
        "summary": summary,
        "recent_history": recent_history,
        "query": query,
    })
    return {"answer": answer, "contexts": contexts_for_ui}


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
 
        print(f"\n=== CÂU TRẢ LỜI TỪ GROQ ===")
        print(answer)
        print()
 
 
if __name__ == "__main__":
    main()
