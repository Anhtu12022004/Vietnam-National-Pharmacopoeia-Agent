import re

def remove_ocr_headers_interactively(input_file, output_file):
    # Đọc nội dung file gốc
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Không tìm thấy file: {input_file}")
        return

    # Tìm tất cả các "từ" (chuỗi không chứa khoảng trắng) và vị trí của chúng
    all_words = list(re.finditer(r'\S+', text))

    # Lấy ra danh sách các vị trí (index) của từ có chứa chuỗi "DTQGVN"
    target_indices = [i for i, match in enumerate(all_words) if 'DTQGVN' in match.group()]

    if not target_indices:
        print("Không tìm thấy chuỗi 'DTQGVN' nào trong file.")
        return

    print(f"Tìm thấy {len(target_indices)} vị trí có chứa 'DTQGVN'. Bắt đầu lọc...\n")

    # Duyệt ngược từ dưới lên để việc cắt chuỗi không làm sai lệch vị trí của các từ phía trên
    for i in reversed(target_indices):
        # Lấy 7 từ phía trước và 7 từ phía sau để tạo ngữ cảnh (bạn có thể đổi số 7 thành số khác)
        start_window = max(0, i - 7)
        end_window = min(len(all_words) - 1, i + 7)

        window_words = all_words[start_window:end_window + 1]

        print("=" * 70)
        
        # In ra các từ kèm theo số thứ tự (từ 0 đến n)
        for idx, wm in enumerate(window_words):
            print(f"[{idx}] {wm.group()}", end="  ")
        print("\n")

        # Vòng lặp chờ người dùng nhập lệnh
        while True:
            try:
                user_input = input("Nhập 'bắt_đầu kết_thúc' để xóa (VD: '2 5'). Nhấn Enter để bỏ qua: ")
                
                # Nếu người dùng chỉ nhấn Enter, bỏ qua và đi tới cụm DTQGVN tiếp theo
                if not user_input.strip():
                    print("-> Đã bỏ qua.")
                    break 

                parts = user_input.split()
                if len(parts) != 2:
                    print("Lỗi: Vui lòng nhập đúng 2 số cách nhau bởi khoảng trắng.")
                    continue

                start_idx = int(parts[0])
                end_idx = int(parts[1])

                if start_idx < 0 or end_idx >= len(window_words) or start_idx > end_idx:
                    print(f"Lỗi: Số nhập vào phải từ 0 đến {len(window_words)-1} và số đầu phải <= số cuối.")
                    continue

                # Xác định vị trí ký tự gốc trong chuỗi văn bản
                del_char_start = window_words[start_idx].start()
                del_char_end = window_words[end_idx].end()

                # Cắt đoạn văn bản đi và thay bằng 1 khoảng trắng để nối 2 đầu lại
                text = text[:del_char_start] + " " + text[del_char_end:]
                print("-> Đã cắt đoạn thành công!")
                break 

            except ValueError:
                print("Lỗi: Vui lòng chỉ nhập số nguyên.")

    # Lưu lại kết quả ra file mới
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)

    print("\nHoàn thành! Đã lưu kết quả vào file:", output_file)


# === HƯỚNG DẪN SỬ DỤNG ===
# Sửa tên file đầu vào và đầu ra cho phù hợp với máy của bạn
file_dau_vao = 'page_711_1029.md'  
file_dau_ra = 'page_711_1029_clean.md'

remove_ocr_headers_interactively(file_dau_vao, file_dau_ra)