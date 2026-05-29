# BÁO CÁO NGHIÊN CỨU VÀ THIẾT KẾ KIẾN TRÚC HỆ THỐNG RAG AGENT TRA CỨU DƯỢC THƯ QUỐC GIA

## 1. TỔNG QUAN DỰ ÁN
Dự án nhằm mục đích xây dựng một hệ thống **RAG Agent (Retrieval-Augmented Generation)** thông minh hỗ trợ hỏi đáp, tra cứu thông tin chuyên sâu về thành phần, chỉ định, chống chỉ định và các quy chế y khoa liên quan đến thuốc. Dữ liệu cốt lõi (Ground Truth) được sử dụng cho hệ thống là **"Dược thư quốc gia Việt Nam"** – bộ tài liệu chính thống, có tính pháp lý và độ chính xác tuyệt đối do Bộ Y tế ban hành.

---

## 2. PHÂN TÍCH KIẾN TRÚC ĐỀ XUẤT BAN ĐẦU
Kiến trúc hệ thống do dựa trên mô hình tự động điều hướng và tối ưu hóa ngữ cảnh thông qua hai tầng LLM (Small LLM và Strong LLM) cùng cơ chế tìm kiếm mở rộng (Web Search).

### 2.1. Luồng xử lý dữ liệu (Workflow)
1. **Tiếp nhận Query:** Hệ thống nhận câu hỏi từ người dùng.
2. **Định tuyến (Routing):** Câu hỏi được đưa vào một **LLM nhỏ (Small LLM)** để phân loại xem có cần sử dụng cơ sở dữ liệu nội bộ (Dược thư) để trả lời hay không.
    * **Trường hợp KHÔNG cần dữ liệu nội bộ:** Câu hỏi (ví dụ: giao tiếp, hỏi đáp thông thường) được chuyển thẳng đến **LLM mạnh (Strong LLM)** để phản hồi nhanh.
    * **Trường hợp CẦN dữ liệu nội bộ:** Hệ thống tiến hành trích xuất thông tin tương ứng từ cơ sở dữ liệu "Dược thư quốc gia Việt Nam" để làm ngữ cảnh (Context).
3. **Đánh giá ngữ cảnh (Context Evaluation):** Đoạn dữ liệu trích xuất cùng câu hỏi được đưa qua một LLM để đánh giá xem thông tin đã đủ để trả lời chính xác chưa.
    * **Nếu ĐỦ thông tin:** Đưa toàn bộ Query và Context vào **Strong LLM** để tổng hợp câu trả lời cuối cùng.
    * **Nếu THIẾU thông tin:** Hệ thống kích hoạt Agent tìm kiếm thêm thông tin trên Web để bổ sung vào Context. Quá trình này lặp lại cho đến khi bộ kiểm duyệt đánh giá đủ thông tin, sau đó mới chuyển sang **Strong LLM** để trả lời.

---

## 3. ĐÁNH GIÁ CHIẾN LƯỢC KIẾN TRÚC
Chiến lược thiết kế trên phản ánh tư duy kiến trúc hệ thống LLM hiện đại, tiệm cận với hai mô hình tiên tiến hiện nay là **Adaptive RAG** (Định tuyến câu hỏi linh hoạt) và **Corrective RAG - CRAG** (Đánh giá và sửa lỗi ngữ cảnh).

### 3.1. Ưu điểm nổi bật
* **Tối ưu hóa tài nguyên và chi phí:** Việc sử dụng LLM nhỏ làm nhiệm vụ định tuyến (Router) ở bước đầu giúp giảm tải đáng kể cho hệ thống, bỏ qua các bước xử lý RAG phức tạp đối với các câu hỏi phổ thông.
* **Kiểm soát chất lượng và giảm thiểu ảo giác (Hallucination):** Tầng LLM đánh giá ngữ cảnh đóng vai trò như một bộ kiểm duyệt (Evaluator), đảm bảo LLM thế hệ cuối không tự suy diễn khi dữ liệu nội bộ bị khuyết thiếu. Điều này cực kỳ quan trọng trong domain Y tế/Dược học – nơi độ chính xác ảnh hưởng trực tiếp đến sức khỏe con người.
* **Khả năng mở rộng tri thức dynamic:** Việc tích hợp Web Search fallback giúp hệ thống giải quyết được điểm nghẽn về "hạn chế tri thức theo thời gian" của các bộ dữ liệu tĩnh, hỗ trợ cập nhật các loại thuốc mới hoặc phác đồ điều trị mới chưa kịp biên soạn vào Dược thư.

### 3.2. Rủi ro kỹ thuật và Điểm nghẽn hệ thống
* **Bẫy vòng lặp vô hạn (Infinite Loop):** Cơ chế "tìm kiếm trên web cho đến khi đủ thông tin" ẩn chứa rủi ro lớn. Đối với các câu hỏi không có lời giải, thông tin sai lệch hoặc câu hỏi phá hoại từ người dùng, Evaluator có thể liên tục đánh giá là "thiếu", dẫn đến Agent gọi API tìm kiếm vô hạn gây treo hệ thống và cạn kiệt chi phí API.
* **Xung đột độ tin cậy của nguồn dữ liệu (Data Authority):** Dược thư quốc gia là chân lý tuyệt đối (Ground Truth), trong khi dữ liệu Web Search thường có nhiều nhiễu, quảng cáo hoặc kiến thức y khoa đại chúng chưa kiểm chứng. Việc trộn lẫn hai nguồn này có thể làm giảm tính chính xác pháp lý của câu trả lời.
* **Độ trễ phản hồi lớn (High Latency):** Một câu hỏi phức tạp cần đi qua tối thiểu 3-4 lượt gọi LLM và API tìm kiếm sẽ tạo ra độ trễ tích lũy cao, gây ảnh hưởng xấu đến trải nghiệm người dùng theo thời gian thực (Real-time UX).

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

---

## 5. ĐỀ XUẤT CẤU TRÚC VÀ LƯU TRỮ DỮ LIỆU TỐI ƯU
Để hiện thực hóa kiến trúc RAG nâng cao này, hệ thống cần áp dụng chiến lược xử lý dữ liệu lai (Hybrid Parsing & Storage).

### 5.1. Chiến lược Phân tách Dữ liệu (Parsing & Chunking)
* **Đối với Chuyên luận thuốc:** Tuyệt đối không dùng phương pháp cắt nhỏ cơ học theo số lượng từ (Fixed-size chunking). Cần sử dụng mã script (Python + Regular Expression) để bóc tách triệt để tài liệu Markdown thành các cấu trúc dữ liệu **JSON** chuẩn hóa theo đúng 19 trường thông tin quy định.
* **Đối với Chuyên luận chung:** Áp dụng phương pháp **Header-based Chunking** (cắt theo phân cấp tiêu đề Markdown). Toàn bộ nội dung nằm dưới một tiêu đề nhỏ kèm theo bảng biểu/công thức liên quan sẽ được đóng gói thành một chunk hoàn chỉnh nhằm giữ nguyên vẹn ngữ cảnh logic.

### 5.2. Kiến trúc lưu trữ lai (Hybrid Storage Architecture)
Hệ thống khuyến nghị triển khai phối hợp 3 loại hình lưu trữ nhằm phát huy tối đa hiệu năng tra cứu:

```
                  ┌─────────────────────────────────────────┐
                  │          Dữ liệu Dược Thư (MD)          │
                  └────────────────────┬────────────────────┘
                                       │
                        [Bộ phân tách dữ liệu / Parser]
                                       │
             ┌─────────────────────────┼─────────────────────────┐
             ▼                         ▼                         ▼
   ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
   │ Document Database │     │  Vector Database  │     │  Graph Database   │
   │ (Mongo / Postgres)│     │(Qdrant/Chroma/Mil)│     │     (Neo4j)       │
   ├───────────────────┤     ├───────────────────┤     ├───────────────────┤
   │Lưu trữ JSON gốc,  │     │Lưu trữ Embeddings │     │Xây dựng quan hệ   │
   │hỗ trợ Keyword     │     │từng phân mục phục │     │Thuốc - Thuốc,     │
   │Search (BM25)      │     │vụ Semantic Search │     │Thuốc - Chỉ định   │
   └───────────────────┘     └───────────────────┘     └───────────────────┘
```

1. **Document Database (MongoDB / PostgreSQL JSONB):** Lưu trữ toàn bộ các bản ghi JSON của chuyên luận thuốc. Phục vụ cho việc tìm kiếm chính xác tuyệt đối theo từ khóa (Keyword/BM25 Search) khi người dùng nhập đúng tên thuốc, mã ATC, giúp bốc nhanh trường dữ liệu cụ thể (như Chỉ định, Chống chỉ định) mà không qua xử lý vector nhiễu.
2. **Vector Database (Qdrant / Milvus / ChromaDB):** Lưu trữ các đoạn nhúng vector (Embeddings) của các phần nội dung diễn giải (như Cơ chế dược lý, Thận trọng) và các chuyên luận chung. Phục vụ tìm kiếm theo ngữ nghĩa (Semantic Search) cho các câu hỏi mang tính triệu chứng hoặc tình huống lâm sàng tổng quát.
3. **Graph Database (Neo4j - Tùy chọn nâng cao):** Biến đổi Dược thư thành một **Knowledge Graph (Đồ thị tri thức)**. Các thực thể như *Thuốc*, *Hoạt chất*, *Mã ATC*, *Bệnh lý/Chỉ định*, *Tác dụng phụ* sẽ đóng vai trò là các Nút (Nodes). Mối quan hệ tương kỵ, tương tác thuốc sẽ là các Cạnh (Edges). Cấu trúc này tối ưu cho việc xử lý các bài toán kiểm tra đơn thuốc phức tạp (nhiều loại thuốc phối hợp).

---

## 6. KHUYẾN NGHỊ TỐI ƯU HÓA HỆ THỐNG
Để giải quyết triệt để các rủi ro đã nêu ở mục 3.2, kiến trúc hệ thống cần bổ sung các cơ chế kiểm soát sau:

1. **Đặt ngưỡng giới hạn vòng lặp tìm kiếm (Max Iterations Guard):** Cấu hình cứng tham số `max_retries` (ví dụ: tối đa 2 lần tìm kiếm web). Nếu vượt quá giới hạn mà thông tin vẫn không đủ, Agent phải dừng lại và phản hồi theo kịch bản an toàn: *"Hệ thống không tìm thấy đủ dữ liệu y khoa chính thống để trả lời an toàn cho câu hỏi này"*.
2. **Phân tầng trọng số ngữ cảnh (Context Weighting & Prompt Engineering):** Khi thiết kế Prompt cho Strong LLM trả lời cuối cùng, cấu trúc ngữ cảnh phải phân định rõ ràng quyền hạn:
    * Ưu tiên số 1 (Độ tin cậy tối cao): Dữ liệu từ Dược thư quốc gia.
    * Ưu tiên số 2 (Tham khảo bổ sung): Dữ liệu trích xuất từ Web Search.
    * Chỉ thị LLM: Nếu có sự mâu thuẫn thông tin, bắt buộc phải tuân theo hoặc cảnh báo dựa trên dữ liệu Dược thư.
3. **Chiến lược Tìm kiếm Kết hợp (Hybrid Search):** Do đặc thù tên thuốc chuyên ngành rất dễ sai lệch chính tả, hệ thống trích xuất cần kết hợp chặt chẽ giữa Tìm kiếm từ khóa (BM25) và Tìm kiếm ngữ nghĩa (Dense Vector) thông qua một bộ tái xếp hạng (**Reranker** như Cohere Rerank hoặc BGE-Reranker) để chọn ra Context cô đọng nhất, giảm thiểu tối đa token thừa nhằm hạ thấp Latency.
