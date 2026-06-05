import os
import requests
import json
import trafilatura
from dotenv import load_dotenv

load_dotenv()

def serper_search(query):
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

    serper_response = serper_search(query)

    list_url = []

    for i in range(num_results):
        list_url.append(serper_response['organic'][i]['link'])

    return list_url

# def extract_content_by_Jina(list_url) -> list:

#     contexts = []

#     for idx, url in enumerate(list_url, 1):
#         print(f"  [{idx}] Đang cào dữ liệu qua Jina: {url}")
#         jina_url = f"https://r.jina.ai/{url}"
        
#         try:
#             # Bạn có thể thêm Authorization Bearer Token của Jina nếu bị giới hạn lượt gọi tự do
#             jina_response = requests.get(jina_url)
#             if jina_response.status_code == 200:
#                 contexts.append({
#                     "source_url": url,
#                     "markdown_content": jina_response.text
#                 })
#         except Exception as e:
#             print(f"  -> Lỗi khi đọc link {url}: {e}")

#     return contexts

def extract_content_by_Trafilatura(list_url) -> list:
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