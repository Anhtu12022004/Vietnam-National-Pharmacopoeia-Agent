"""
Flask Web Server cho PharmaRAG-VN Chat UI.
Cung cấp giao diện chat giống ChatGPT với khả năng hiển thị context đã truy vấn.
"""

from flask import Flask, render_template, request, jsonify, session
from core.chat_engine import ask
import os
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)


@app.route("/")
def index():
    """Trang chủ - hiển thị giao diện chat."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    API endpoint nhận câu hỏi và trả về câu trả lời + contexts.
    
    Request JSON: { "message": "..." }
    Response JSON: { "answer": "...", "contexts": [...] }
    """
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Tin nhắn không được để trống."}), 400

    # Lấy lịch sử chat từ session
    if "chat_history" not in session:
        session["chat_history"] = []

    chat_history = session["chat_history"]

    try:
        # Gọi hàm ask() từ Chat_loop.py
        result = ask(user_message, chat_history)

        # Cập nhật lịch sử
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": result["answer"]})
        session["chat_history"] = chat_history
        session.modified = True

        return jsonify({
            "answer": result["answer"],
            "contexts": result["contexts"],
            "used_web_search": result.get("used_web_search", False),
        })
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": f"Đã xảy ra lỗi: {str(e)}"}), 500


@app.route("/api/clear", methods=["POST"])
def clear_history():
    """Xóa lịch sử chat."""
    session["chat_history"] = []
    session.modified = True
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
