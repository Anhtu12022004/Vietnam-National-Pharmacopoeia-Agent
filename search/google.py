"""
search/google.py — Tìm kiếm Google qua Serper API và trích xuất nội dung bằng Trafilatura.

Di chuyển từ Search_On_Google.py gốc để tổ chức theo package.
"""

import os
import requests
import json
import trafilatura
from dotenv import load_dotenv

load_dotenv()


def serper_search(query):
    """Gọi Serper API để tìm kiếm Google."""
    url = "https://google.serper.dev/search"
    payload = json.dumps({
        "q": query,
        "gl": "vn",
        "hl": "vi"
    })
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Lỗi khi gọi Serper API: {e}")
        return None


def extract_url_from_serper_search(query, num_results=3) -> list:
    """Trích xuất danh sách URL từ kết quả Serper."""
    serper_response = serper_search(query)

    list_url = []

    for i in range(num_results):
        list_url.append(serper_response['organic'][i]['link'])

    return list_url


def extract_content_by_Trafilatura(list_url) -> list:
    """Cào và làm sạch nội dung trang web bằng Trafilatura."""
    contexts = []
    for idx, url in enumerate(list_url, 1):
        print(f"  [{idx}] Đang cào và làm sạch dữ liệu qua Trafilatura: {url}")
        
        try:
            # Tải HTML của trang web
            downloaded = trafilatura.fetch_url(url)
            
            if downloaded:
                # Hàm extract tự động nhận diện bài viết chính, bỏ qua menu/footer/quảng cáo
                text = trafilatura.extract(downloaded, include_links=False, include_images=False)
                
                if text:
                    contexts.append({
                        "source_url": url,
                        "markdown_content": text
                    })
                else:
                    print(f"  -> Không tìm thấy nội dung chính ở {url}")
        except Exception as e:
            print(f"  -> Lỗi khi đọc link {url}: {e}")

    return contexts


def search_on_google(query, num_results=3) -> list:
    """
    Tìm kiếm Google và trả về nội dung đã trích xuất.

    Args:
        query: Câu truy vấn tìm kiếm.
        num_results: Số kết quả cần lấy.

    Returns:
        Danh sách dict {"source_url": ..., "markdown_content": ...}.
    """
    url = extract_url_from_serper_search(query, num_results)
    context = extract_content_by_Trafilatura(url)
    return context


def main():
    query = "Silymarin có tác dụng gì?"
    k = 3
    contexts = search_on_google(query, k)
    for idx, context in enumerate(contexts, 1):
        print(f"Context {idx}: {context['source_url']}")
        print(context['markdown_content'])
        print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    main()
