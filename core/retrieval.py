"""
core/retrieval.py — Logic đánh giá chất lượng retrieval bằng Reranker và xây dựng web context.

Chứa:
- rerank_documents: Gọi Jina Reranker v3 API để chấm điểm tương đồng.
- evaluate_by_rerank_scores: Đánh giá SUFFICIENT/INSUFFICIENT dựa trên ngưỡng điểm.
- filter_docs_by_threshold: Lọc tài liệu nội bộ theo ngưỡng rerank score.
- build_web_context: Chuyển đổi kết quả Google Search thành context text + UI data.
"""

import requests

from core.config import JINA_RERANKER_URL, JINA_RERANKER_MODEL, JINA_API_KEY


def rerank_documents(query: str, docs: list) -> list[dict]:
    """
    Gọi Jina Reranker v3 API để chấm điểm tương đồng giữa query và documents.

    Args:
        query: Câu hỏi đã chuẩn hóa.
        docs: Danh sách Document objects từ VectorStore (có .page_content và .metadata).

    Returns:
        Danh sách dict sắp xếp theo rerank_score giảm dần:
        [
            {
                "doc": Document object gốc,
                "rerank_score": float (0-1),
                "original_index": int
            },
            ...
        ]
    """
    if not docs:
        return []

    # Chuẩn bị danh sách nội dung documents cho API
    document_texts = [doc.page_content for doc in docs]

    headers = {
        "Authorization": f"Bearer {JINA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "model": JINA_RERANKER_MODEL,
        "query": query,
        "documents": document_texts,
        "top_n": len(document_texts),  # Lấy điểm cho tất cả documents
    }

    try:
        print(f"\n[Đang gọi Jina Reranker v3 để chấm điểm {len(docs)} tài liệu...]")
        response = requests.post(JINA_RERANKER_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        # Jina API trả về danh sách results đã sắp xếp theo relevance_score giảm dần
        reranked = []
        for item in result.get("results", []):
            original_index = item["index"]
            reranked.append({
                "doc": docs[original_index],
                "rerank_score": item["relevance_score"],
                "original_index": original_index,
            })

        # Sắp xếp theo rerank_score giảm dần (API đã sắp xếp, nhưng đảm bảo chắc chắn)
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Log điểm số
        for i, item in enumerate(reranked[:5]):  # In top 5 để debug
            print(f"  [Rank {i+1}] Score: {item['rerank_score']:.4f} | "
                  f"{item['doc'].page_content[:80]}...")

        return reranked

    except Exception as e:
        print(f"[LỖI] Jina Reranker API thất bại: {e}")
        # Fallback: trả về docs gốc với score = 0 (sẽ trigger web search)
        return [
            {"doc": doc, "rerank_score": 0.0, "original_index": i}
            for i, doc in enumerate(docs)
        ]


def evaluate_by_rerank_scores(
    reranked_docs: list[dict],
    top_k: int = 3,
    max_threshold: float = 0.7,
    avg_threshold: float = 0.5,
) -> tuple[list[dict], bool, float, float]:
    """
    Lấy Top-K documents sau reranking và đánh giá đủ/không đủ dựa trên ngưỡng điểm.

    Logic đánh giá:
    - SUFFICIENT: max_rerank_score >= 0.7 VÀ average_rerank_score >= 0.5
    - INSUFFICIENT: max_rerank_score < 0.7 HOẶC average_rerank_score < 0.5

    Args:
        reranked_docs: Danh sách docs đã rerank (sắp xếp giảm dần theo score).
        top_k: Số lượng documents cần lấy (mặc định 3).
        max_threshold: Ngưỡng điểm cao nhất (mặc định 0.7).
        avg_threshold: Ngưỡng điểm trung bình (mặc định 0.5).

    Returns:
        (top_docs, is_sufficient, max_score, avg_score)
    """
    if not reranked_docs:
        return [], False, 0.0, 0.0

    # Lấy Top-K
    top_docs = reranked_docs[:top_k]

    # Tính max và average score từ Top-K
    scores = [item["rerank_score"] for item in top_docs]
    max_score = max(scores)
    avg_score = sum(scores) / len(scores)

    # Đánh giá theo ngưỡng
    is_sufficient = (max_score >= max_threshold) and (avg_score >= avg_threshold)

    print(f"\n[Đánh giá Rerank Scores]")
    print(f"  Max Score:  {max_score:.4f}  (ngưỡng ≥ {max_threshold})")
    print(f"  Avg Score:  {avg_score:.4f}  (ngưỡng ≥ {avg_threshold})")
    print(f"  Kết quả:   {'✅ SUFFICIENT — Đủ thông tin' if is_sufficient else '⚠️ INSUFFICIENT — Không đủ, sẽ tìm kiếm Google'}")

    return top_docs, is_sufficient, max_score, avg_score


def filter_docs_by_threshold(reranked_docs: list[dict], threshold: float = 0.4) -> list[dict]:
    """
    Lọc chỉ giữ lại các documents có rerank_score >= threshold.
    Dùng khi fallback web search được kích hoạt để loại bỏ tài liệu nội bộ chất lượng kém.

    Args:
        reranked_docs: Danh sách docs đã rerank.
        threshold: Ngưỡng score tối thiểu (mặc định 0.4).

    Returns:
        Danh sách docs đã lọc (chỉ giữ score >= threshold).
    """
    filtered = [item for item in reranked_docs if item["rerank_score"] >= threshold]
    print(f"[Lọc tài liệu nội bộ] Giữ {len(filtered)}/{len(reranked_docs)} tài liệu "
          f"(ngưỡng score ≥ {threshold})")
    return filtered


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
