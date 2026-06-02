"""
normalize_headers.py
--------------------
Chuẩn hóa header trong file markdown theo chuẩn Format.md:
  - Tên thuốc (ALL CAPS): # **TÊN THUỐC**
  - Các section chính:    ## **Tên section**
  - Sub-section italic:   ### *Tên italic*

Cách dùng:
    python normalize_headers.py input.md output.md
    python normalize_headers.py input.md          (tạo input_normalized.md)
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Danh sách section chuẩn (## level)
# ---------------------------------------------------------------------------
SECTION_NAMES = [
    "Dạng thuốc và hàm lượng",
    "Dạng bào chế và hàm lượng",
    "Dược lý và cơ chế tác dụng",
    "Chỉ định",
    "Chống chỉ định",
    "Thận trọng",
    "Thời kỳ mang thai",
    "Thời kì mang thai",
    "Thời kỳ cho con bú",
    "Thời kì cho con bú",
    "Tác dụng không mong muốn (ADR)",
    "Tác dụng không mong muốn(ADR)",
    "Tác dụng không mong muốn",
    "Hướng dẫn cách xử trí ADR",
    "Liều lượng và cách dùng",
    "Liều dùng và cách dùng",
    "Tương tác thuốc",
    "Độ ổn định và bảo quản",
    "Bảo quản",
    "Tương kỵ",
    "Tương ky",
    "Quá liều và xử trí",
    "Quá liều cấp tính và xử trí",
    "Quá liều mạn tính",
    "Thông tin qui chế",
    "Thông tin quy chế",
    "Thông tin và quy chế",
    "Tên thương mại",
    "Tên thương mai",
]

# Chuẩn hóa tên không đồng nhất
SECTION_NORMALIZE = {
    "Thời kì mang thai":               "Thời kỳ mang thai",
    "Thời kì cho con bú":              "Thời kỳ cho con bú",
    "Tác dụng không mong muốn(ADR)":   "Tác dụng không mong muốn (ADR)",
    "Tác dụng không mong muốn":        "Tác dụng không mong muốn (ADR)",
    "Liều dùng và cách dùng":          "Liều lượng và cách dùng",
    "Tương ky":                        "Tương kỵ",
    "Tên thương mai":                  "Tên thương mại",
    "Thông tin qui chế":               "Thông tin quy chế",
    "Thông tin và quy chế":            "Thông tin quy chế",
    "Bảo quản":                        "Độ ổn định và bảo quản",
    "Dạng bào chế và hàm lượng":       "Dạng thuốc và hàm lượng",
    "Quá liều cấp tính và xử trí":     "Quá liều và xử trí",
    "Quá liều mạn tính":               "Quá liều và xử trí",
}

# Sub-section nhỏ (giữ italic ###)
SUB_SECTION_NAMES = [
    "Liều lượng", "Liều dùng", "Cách dùng",
    "Dự phòng loãng xương",
]

# ---------------------------------------------------------------------------
# 2. Helpers
# ---------------------------------------------------------------------------
def strip_markup(text: str) -> str:
    """Xóa **, * bọc ngoài và khoảng trắng thừa."""
    text = text.strip()
    # Xóa ** bọc
    text = re.sub(r'^\*\*(.*?)\*\*$', r'\1', text)
    # Xóa * đơn bọc (italic), không phải **
    text = re.sub(r'^\*(?!\*)(.*?)(?<!\*)\*$', r'\1', text)
    return text.strip()

def is_drug_name(name: str) -> bool:
    """
    Tên thuốc: phần trước dấu ngoặc đầu tiên gần như toàn chữ hoa Latin.
    Ví dụ: 'CLINDAMYCIN', 'CLOBETASOL PROPIONAT', 'ERGOMETRIN (Ergonovin)'
    """
    # Chỉ xét phần trước '(' để bỏ qua chú thích tiếng Việt trong ngoặc
    base = re.sub(r'\(.*', '', name).strip()
    cleaned = re.sub(r'[0-9\s\-/,\.\*]', '', base)
    if not cleaned:
        return False
    upper_count = sum(1 for c in cleaned if c.isupper())
    return upper_count / len(cleaned) >= 0.85

# ---------------------------------------------------------------------------
# 3. Xử lý từng dòng
# ---------------------------------------------------------------------------
def classify_and_rewrite(line: str) -> str:
    """Chuẩn hóa dòng header; trả về nguyên bản nếu không phải header."""
    stripped = line.rstrip('\n').lstrip()

    if not stripped.startswith('#'):
        return line

    m = re.match(r'^(#{1,4})\s+(.*)', stripped)
    if not m:
        return line

    rest = m.group(2).strip()
    name_clean = strip_markup(rest)

    # A) Italic sub-header: * đơn (không phải **)
    italic_m = re.match(r'^\*(?!\*)(.+?)(?<!\*)\*$', rest)
    if italic_m:
        inner = italic_m.group(1).strip()
        return f'### *{inner}*\n'

    # B) Tên thuốc (all-caps, kể cả có chú thích trong ngoặc)
    if is_drug_name(name_clean):
        return f'# **{name_clean}**\n'

    # C) Combo: "Liều lượng và cách dùng *Cách dùng:*" trên cùng một dòng
    combo_m = re.match(
        r'^(?:\*\*)?(Liều lượng và cách dùng|Liều dùng và cách dùng)(?:\*\*)?\s+'
        r'(\*.+)',
        rest
    )
    if combo_m:
        italic_part = combo_m.group(2).strip()
        return f'## **Liều lượng và cách dùng**\n\n{italic_part}\n'

    # D) Combo: "Liều lượng và cách dùng Cách dùng:" không có italic markers
    combo2_m = re.match(
        r'^(?:\*\*)?(Liều lượng và cách dùng|Liều dùng và cách dùng)(?:\*\*)?\s+'
        r'(Cách dùng:?)',
        rest
    )
    if combo2_m:
        return f'## **Liều lượng và cách dùng**\n\n### *Cách dùng:*\n'

    # E) Section chuẩn (so sánh không phân biệt hoa thường, bỏ dấu : cuối)
    name_compare = name_clean.rstrip(':').strip().lower()
    for sec in SECTION_NAMES:
        if sec.lower() == name_compare:
            canonical = SECTION_NORMALIZE.get(sec, sec)
            return f'## **{canonical}**\n'

    # F) Sub-section nhỏ không có italic marker
    for sub in SUB_SECTION_NAMES:
        if name_compare == sub.lower():
            return f'### *{name_clean.rstrip(":")}:*\n'

    # G) Không khớp -> giữ nguyên
    return line


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------
def normalize_file(input_path: str, output_path: str):
    src = Path(input_path).read_text(encoding='utf-8')
    lines = src.splitlines(keepends=True)
    result = [classify_and_rewrite(line) for line in lines]
    Path(output_path).write_text(''.join(result), encoding='utf-8')

    # Thống kê
    total_headers = sum(1 for l in lines if l.lstrip().startswith('#'))
    changed = sum(1 for a, b in zip(lines, result) if a != b)
    print(f"✅ Đã chuẩn hóa xong: {output_path}")
    print(f"   Tổng header: {total_headers} | Đã sửa: {changed}")


if __name__ == '__main__':
    if len(sys.argv) == 3:
        inp, out = sys.argv[1], sys.argv[2]
    elif len(sys.argv) == 2:
        inp = sys.argv[1]
        out = Path(inp).stem + '_normalized.md'
    else:
        inp = 'page_1301_1495.md'
        out = 'page_1301_1495_normalized.md'

    normalize_file(inp, out)
