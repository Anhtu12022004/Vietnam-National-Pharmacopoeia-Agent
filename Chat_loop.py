import os
from dotenv import load_dotenv

# Tải biến môi trường từ file .env
load_dotenv()

from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

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
# 2. Prompt Template (có hỗ trợ lịch sử chat)
# ──────────────────────────────────────────────
prompt_template = """
Bạn là một dược sĩ lâm sàng giàu kinh nghiệm. Hãy sử dụng CÁC THÔNG TIN TRONG PHẦN NGỮ CẢNH dưới đây để trả lời câu hỏi của người dùng một cách chính xác và dễ hiểu.
Nếu thông tin trong Ngữ cảnh không đủ để trả lời, hãy nói rõ là "Tài liệu hiện tại không chứa đủ thông tin để trả lời câu hỏi này", tuyệt đối không tự bịa ra kiến thức ngoài.

Ngữ cảnh (Context):
{context}

Lịch sử hội thoại (Chat History - 5 lượt gần nhất):
{chat_history}

Câu hỏi của người dùng (Query):
{query}

Câu trả lời:
"""

prompt = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "chat_history", "query"]
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
# 4. Kết nối thành một Chain
# ──────────────────────────────────────────────
chain = prompt | llm | StrOutputParser()


def format_chat_history(history: list[dict]) -> str:
    """
    Chuyển danh sách lịch sử chat thành chuỗi văn bản.
    Mỗi phần tử trong history là dict {"role": "user"/"assistant", "content": "..."}.
    Chỉ lấy 5 lượt (10 message) gần nhất.
    """
    recent = history[-10:]  # mỗi lượt gồm 1 user + 1 assistant → 5 lượt = 10 message
    if not recent:
        return "Chưa có lịch sử hội thoại."
    lines = []
    for msg in recent:
        role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý"
        lines.append(f"{role_label}: {msg['content']}")
    return "\n".join(lines)


def ask(query: str, chat_history: list[dict]) -> str:
    """
    Nhận câu hỏi và lịch sử chat, trả về câu trả lời từ LLM.

    Args:
        query: Câu hỏi hiện tại của người dùng.
        chat_history: Danh sách dict {"role": ..., "content": ...}.

    Returns:
        Chuỗi câu trả lời từ mô hình.
    """
    # Retrieve Top 5 tài liệu liên quan
    docs = vectorstore.similarity_search(query, k=5)
    context = "\n\n".join(
        f"Metadata: {doc.page_content}"
        for doc in docs
    )

    # Format lịch sử 5 lượt gần nhất
    history_text = format_chat_history(chat_history)

    # Gọi chain
    answer = chain.invoke({
        "context": context,
        "chat_history": history_text,
        "query": query,
    })
    return answer


# ──────────────────────────────────────────────
# 5. Vòng lặp chat chính
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

        answer = ask(query, chat_history)

        # Lưu vào lịch sử
        chat_history.append({"role": "user", "content": query})
        chat_history.append({"role": "assistant", "content": answer})

        print(f"\n=== CÂU TRẢ LỜI TỪ GROQ ===")
        print(answer)
        print()


if __name__ == "__main__":
    main()