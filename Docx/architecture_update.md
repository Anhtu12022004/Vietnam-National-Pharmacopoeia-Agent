# BÁO CÁO NGHIÊN CỨU VÀ THIẾT KẾ KIẾN TRÚC HỆ THỐNG RAG TRA CỨU DƯỢC THƯ QUỐC GIA

## 1. TỔNG QUAN DỰ ÁN
Dự án nhằm mục đích xây dựng một hệ thống **RAG (Retrieval-Augmented Generation)** thông minh hỗ trợ hỏi đáp, tra cứu thông tin chuyên sâu về thành phần, chỉ định, chống chỉ định và các quy chế y khoa liên quan đến thuốc. Dữ liệu cốt lõi (Ground Truth) được sử dụng cho hệ thống là **"Dược thư quốc gia Việt Nam"** – bộ tài liệu chính thống, có tính pháp lý và độ chính xác tuyệt đối do Bộ Y tế ban hành.

---

## 2. PHÂN TÍCH KIẾN TRÚC

Kiến trúc hệ thống được xây dựng dựa trên cơ chế Xử lý lịch sử, Chuẩn hóa truy vấn (Query Rewriting), Truy xuất (Retrieval) và Tối ưu hóa ngữ cảnh thông qua sự phối hợp của 3 mô hình chuyên biệt (Fast LLM, Reranker và Main LLM) cùng công cụ tìm kiếm mở rộng (Web Search).

### 2.1. Luồng xử lý dữ liệu (Workflow)

1. **Tiếp nhận Query và Quản lý Lịch sử:**
* Hệ thống nhận câu hỏi từ người dùng.
* Lịch sử trò chuyện được tự động phân tách: **3 lượt hội thoại gần nhất** được giữ nguyên nguyên bản làm ngữ cảnh trực tiếp. Các lượt cũ hơn sẽ được đưa qua một LLM để **tóm tắt lại**, giúp tiết kiệm token mà vẫn giữ được mạch câu chuyện.


2. **Chuẩn hóa truy vấn (Query Rewriting):**
* Câu hỏi hiện tại và 3 lượt lịch sử gần nhất được đưa qua **Fast LLM (Llama-3.1-8B-Instant)**.
* LLM này có nhiệm vụ phân tích và viết lại câu hỏi thành một câu truy vấn độc lập, đầy đủ chủ ngữ và ngữ nghĩa chuyên môn (bỏ qua các từ nối giao tiếp) để tối ưu hóa khả năng tìm kiếm tài liệu.


3. **Truy xuất tài liệu nội bộ (Retrieval):**
* Hệ thống sử dụng câu truy vấn vừa được chuẩn hóa để tìm kiếm nội suy (Similarity Search) ra Top 10 đoạn tài liệu liên quan nhất từ VectorStore (chứa Dữ liệu Dược thư quốc gia).


4. **Đánh giá ngữ cảnh (Context Evaluation):**
* Sử dụng mô hình rerank để lấy điểm tương đồng giữa câu query và các đoạn tài liệu nội bộ vừa trích xuất. Hệ thống sẽ sử dụng Top 3 đoạn tài liệu có điểm tương đồng cao nhất để đưa vào Main LLM.


5. **Tối ưu và Bổ sung ngữ cảnh (Fallback Web Search):**
* **Nếu ĐỦ thông tin max_rerank_score >=0.7 và average_rerank_score >= 0.5:** Hệ thống chốt sử dụng duy nhất tài liệu nội bộ làm ngữ cảnh.
* **Nếu THIẾU thông tin max_rerank_score < 0.7 hoặc average_rerank_score < 0.5 :** Hệ thống kích hoạt API tìm kiếm trên Google để lấy thêm 3 nguồn kết quả trên Web. Ngữ cảnh cuối cùng sẽ được **gộp chung** (Bao gồm phần Tài liệu dược thư nội bộ ở trên (nếu rerank_score >= 0.4) và phần Kết quả Web ở dưới).


6. **Tổng hợp câu trả lời cuối (Final Generation):**
* Toàn bộ bộ dữ liệu đã được xử lý bao gồm: Ngữ cảnh cuối cùng, Tóm tắt lịch sử cũ, Lịch sử 3 lượt gần nhất, và Câu hỏi gốc được đưa vào **Main LLM (Llama-3.3-70B-Versatile)**.
* Mô hình mạnh nhất này sẽ đảm nhiệm vai trò Dược sĩ lâm sàng, dựa hoàn toàn vào dữ liệu được cung cấp để lập luận và trả lời người dùng một cách chính xác, an toàn và dễ hiểu nhất.

---

## 3. ĐÁNH GIÁ CHIẾN LƯỢC KIẾN TRÚC

Kiến trúc hệ thống được xây dựng mang đậm tính chất của một mô hình **Adaptive RAG (RAG thích ứng)** kết hợp với chiến lược **Multi-LLM Orchestration (Điều phối đa mô hình)**. Việc phân rã các tác vụ cho từng dòng model có kích thước (parameter size) khác nhau cho thấy một sự tính toán kỹ lưỡng về sự cân bằng giữa hiệu năng (Performance), độ trễ (Latency) và chi phí tài nguyên (Cost).

### 3.1. Ưu điểm vượt trội

1. **Tối ưu hóa tài nguyên qua chiến lược Multi-LLM:**
* Thay vì sử dụng một mô hình khổng lồ cho toàn bộ quy trình, hệ thống đã khéo léo "cắt lớp" tác vụ: Dùng mô hình nhỏ, tốc độ phản hồi cực nhanh (`Llama-3.1-8B-Instant`) cho tác vụ biến đổi văn bản cơ bản (Query Rewriting); dùng mô hình reranker cho nhiệm vụ đánh giá độ tương đồng giữa query và dữ liệu nội bộ; và chỉ dành mô hình nặng nhất (`Llama-3.3-70B`) cho bước sinh văn bản cuối cùng. Điều này tối ưu hóa đáng kể lượng token tiêu thụ và chi phí tính toán.


2. **Cơ chế quản lý Context Window thông minh:**
* Việc kết hợp song song giữa duy trì nguyên bản (3 lượt gần nhất) và nén thông tin (tóm tắt các lượt cũ) giải quyết triệt để bài toán tràn bộ nhớ ngữ cảnh (Context length overflow) khi đoạn chat kéo dài. Cơ chế này giúp mô hình 70B không bị nhiễu bởi các "noise" từ hội thoại quá cũ, đồng thời không làm mất đi các coreference (từ đồng chỉ định) nhờ vào Query Rewriting.


3. **Giảm thiểu tối đa rủi ro Ảo giác (Hallucination) trong y khoa:**
* Trong lĩnh vực y tế, tính chính xác là yếu tố sống còn. Cơ chế chọn score cao (rerank_score >= 0.7) của "người gác cổng" giúp hệ thống có khả năng tự nhận thức giới hạn tri thức của VectorStore nội bộ. Việc kích hoạt Web Search fallback khi rerank_score < 0.7 đảm bảo hệ thống không tự suy diễn (confabulation) khi gặp các loại thuốc mới hoặc ca bệnh chưa có trong "Dược thư quốc gia".



### 3.2. Hạn chế và Rủi ro tiềm ẩn

1. **Độ trễ tích lũy (Latency Bottleneck):**
* Kiến trúc đang vận hành theo cơ chế tuần tự (Sequential Pipeline): *Summary -> Rewrite -> Retrieve -> Rerank -> Web Search (nếu có) -> Generate*. Việc phải chờ API của nhiều LLM phản hồi nối tiếp nhau có thể gây ra độ trễ (latency) đáng kể cho người dùng cuối, đặc biệt trong kịch bản kích hoạt Fallback Web Search.



2. **Phụ thuộc hạ tầng và rủi ro bảo mật y tế:**
* Việc gọi dữ liệu thông qua các API bên ngoài (Groq, OpenAI Embeddings, Google Search) đặt ra thách thức về tính ổn định của mạng. Đồng thời, đối với hệ thống tư vấn lâm sàng, việc gửi trực tiếp các truy vấn y tế qua nền tảng bên thứ ba cần sự kiểm duyệt chặt chẽ về việc ẩn danh hóa dữ liệu người dùng (Data Masking / PII removal) để tránh vi phạm các tiêu chuẩn bảo mật.



### 3.3. Đề xuất hướng cải tiến

* **Xử lý bất đồng bộ (Asynchronous Execution):** Có thể chạy song song quá trình *Retrieve VectorStore* và *Tóm tắt lịch sử cũ* để tiết kiệm thời gian phản hồi.
* **Tích hợp Semantic Cache:** Xây dựng một lớp cache ngữ nghĩa lưu trữ các cặp câu hỏi - câu trả lời nội bộ đã được xác thực. Nếu truy vấn mới trùng khớp ngữ nghĩa (Cosine similarity cao) với truy vấn cũ, hệ thống có thể trả về đáp án ngay lập tức mà không cần đi qua toàn bộ Pipeline của 3 LLM.

---

## 4. PHÂN TÍCH ĐẶC ĐIỂM DỮ LIỆU NGUỒN
Dựa trên mẫu dữ liệu thực tế trích xuất từ "Dược thư quốc gia Việt Nam 2018", tài liệu được chia làm hai cấu trúc văn bản rõ rệt:

### 4.1. Các chuyên luận chung (General Guidelines)
* **Nội dung:** Hướng dẫn quy chế kê đơn thuốc, nguyên tắc sử dụng thuốc cho các đối tượng đặc biệt (người cao tuổi, trẻ em, người suy giảm chức năng gan/thận), hướng dẫn sử dụng an toàn thuốc giảm đau, v.v.
* **Đặc điểm:** Văn bản mang tính diễn giải logic, phân cấp sâu bằng các thẻ Heading (`#`, `##`, `###`), chứa các bảng tiêu chuẩn lâm sàng quan trọng (Bảng phân loại Child-Pugh, Phân loại mức độ suy thận theo GFR) và công thức toán học y học (Công thức Cockcroft & Gault tính độ thanh thải creatinin $Cl_{cr}$).

### 4.2. Các chuyên luận thuốc cụ thể (Drug Monographs)
Mỗi dược chất trong số khoảng 700 dược chất của Dược thư được cấu trúc hóa nghiêm ngặt theo bố cục 19 phần cố định:
1. Tên chuyên luận thuốc (Tên Việt hóa)
2. Tên chung quốc tế (INN)
3. Mã ATC
4. Loại thuốc
5. Dạng thuốc và hàm lượng
6. Dược lý và cơ chế tác dụng
7. Chỉ định
8. Chống chỉ định
9. Thận trọng
10. Thời kỳ mang thai
11. Thời kỳ cho con bú
12. Tác dụng không mong muốn (ADR)
13. Hướng dẫn cách xử trí ADR
14. Liều lượng và cách dùng
15. Tương tác thuốc
16. Độ ổn định và bảo quản
17. Tương kỵ
18. Quá liều và xử trí
19. Thông tin quy chế
