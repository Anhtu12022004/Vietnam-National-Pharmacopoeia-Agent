import os
import re
import sys

# ============================================================================
# PHARMARAG-VN HEADER NORMALIZER
# Chuẩn hóa tất cả header trong các file chuyên luận thuốc (Dược thư QGVN)
# ============================================================================

# --- Configuration ---

# Standard level-2 section headings (key variants -> normalized form)
# Covers typos, variations, and different formatting
STANDARD_HEADERS_MAP = {
    # Dạng thuốc và hàm lượng
    "Dạng thuốc và hàm lượng": "## **Dạng thuốc và hàm lượng**",
    "Dang thuốc và hàm lượng": "## **Dạng thuốc và hàm lượng**",
    "Dang thuốc và hàm lương": "## **Dạng thuốc và hàm lượng**",
    "Dạng thuốc và hàm lượng:": "## **Dạng thuốc và hàm lượng**",
    # Dược lý và cơ chế tác dụng
    "Dược lý và cơ chế tác dụng": "## **Dược lý và cơ chế tác dụng**",
    # Chỉ định
    "Chỉ định": "## **Chỉ định**",
    # Chống chỉ định
    "Chống chỉ định": "## **Chống chỉ định**",
    # Thận trọng
    "Thận trọng": "## **Thận trọng**",
    # Thời kỳ mang thai
    "Thời kỳ mang thai": "## **Thời kỳ mang thai**",
    # Thời kỳ cho con bú
    "Thời kỳ cho con bú": "## **Thời kỳ cho con bú**",
    # Tác dụng không mong muốn (ADR)
    "Tác dụng không mong muốn (ADR)": "## **Tác dụng không mong muốn (ADR)**",
    "Tác dụng không mong muốn": "## **Tác dụng không mong muốn (ADR)**",
    # Hướng dẫn cách xử trí ADR
    "Hướng dẫn cách xử trí ADR": "## **Hướng dẫn cách xử trí ADR**",
    "Hướng dẫn cách xử trí": "## **Hướng dẫn cách xử trí ADR**",
    # Liều lượng và cách dùng
    "Liều lượng và cách dùng": "## **Liều lượng và cách dùng**",
    "Liều lượng và cách dùng:": "## **Liều lượng và cách dùng**",
    # Tương tác thuốc
    "Tương tác thuốc": "## **Tương tác thuốc**",
    # Độ ổn định và bảo quản
    "Độ ổn định và bảo quản": "## **Độ ổn định và bảo quản**",
    # Tương kỵ
    "Tương kỵ": "## **Tương kỵ**",
    "Tương ky": "## **Tương kỵ**",
    # Quá liều và xử trí
    "Quá liều và xử trí": "## **Quá liều và xử trí**",
    "Ouá liều và xử trí": "## **Quá liều và xử trí**",
    "Quá liều và cách xử trí": "## **Quá liều và xử trí**",
    # Thông tin quy chế
    "Thông tin quy chế": "## **Thông tin quy chế**",
    "Thông tin qui chế": "## **Thông tin quy chế**",
    # Tên thương mại
    "Tên thương mại": "## **Tên thương mại**",
    "Tên thương mại:": "## **Tên thương mại**",
}

# Sub-headings (level 3)
SUB_HEADERS_MAP = {
    "Cách dùng": "### *Cách dùng:*",
    "Cách dùng:": "### *Cách dùng:*",
    "Liều dùng": "### *Liều dùng:*",
    "Liều dùng:": "### *Liều dùng:*",
    "Liều lượng": "### *Liều lượng:*",
    "Liều lượng:": "### *Liều lượng:*",
}

# Metadata keys that should be on their own line as ## **Key:** Value
METADATA_KEYS = [
    "Tên chung quốc tế",
    "Mã ATC",
    "Loại thuốc",
]


def clean_header_text(text):
    """Strip markdown header markers (#), bold markers (**), and whitespace."""
    return text.strip().lstrip("#").strip().strip("*").strip().rstrip(":")


def is_page_header_footer(line):
    """
    Detects running headers/footers from PDF extraction.
    Examples:
        '116 **Aciclovir** DTQGVN 2 DTQGVN 2 **Acid acetylsalicylic** 117'
        'DTQGVN 2 **Ganciclovir** 711'
        '1030 **Natri clorid** DTQGVN 2'
        '412 Clobetasol propionat DTQGVN 2'
    """
    stripped = line.strip()
    if not stripped:
        return False

    if "DTQGVN" not in stripped:
        return False

    # Pattern 1: starts with number, has DTQGVN
    # e.g. "116 **Aciclovir** DTQGVN 2 DTQGVN 2 **Acid acetylsalicylic** 117"
    if re.match(r'^\d+\s+.*DTQGVN', stripped):
        return True

    # Pattern 2: starts with DTQGVN
    # e.g. "DTQGVN 2 **Ganciclovir** 711"
    if re.match(r'^DTQGVN\s+\d+', stripped):
        return True

    # Pattern 3: ends with DTQGVN 2 or DTQGVN 2 <number>
    # e.g. "1030 **Natri clorid** DTQGVN 2"
    if re.search(r'DTQGVN\s+\d+\s*$', stripped):
        return True

    # Pattern 4: contains DTQGVN in the middle of line with bold drug names and page numbers
    if re.search(r'DTQGVN\s+\d+\s+DTQGVN', stripped):
        return True

    # Pattern 5: Just "DTQGVN 2 <number>" or "<number> DTQGVN 2"
    if re.match(r'^DTQGVN\s+\d+\s+\d+$', stripped):
        return True

    return False


def is_drug_title(stripped):
    """
    Detect drug title lines. These are:
    - Lines starting with # (any level) followed by **UPPERCASE_NAME**
    - Lines starting with ## **UPPERCASE_NAME**
    Drug names are fully uppercase (Vietnamese) and may contain parenthetical notes.
    Examples:
        '# **ACID ACETYLSALICYLIC (Aspirin)**'
        '### **CLINDAMYCIN**'
        '## **GANCICLOVIR**'
        '## **SPIRONOLACTON**'
    """
    # Match any heading level followed by bold uppercase drug name
    # Vietnamese uppercase includes: ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯ
    match = re.match(
        r'^#{1,4}\s+\*\*([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯ0-9][A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯ0-9\s\-\(\),.]*)\*\*\s*$',
        stripped
    )
    if match:
        name = match.group(1).strip()
        # At least 3 characters and mostly uppercase
        if len(name) >= 3:
            return name
    return None


def split_inline_metadata(line):
    """
    Handle lines where multiple metadata fields are on one line.
    Example:
        '**Tên chung quốc tế:** Ganciclovir. **Mã ATC:** J05AB06, S01AD09. **Loại thuốc:** Thuốc chống virus.'
    Returns a list of individual formatted lines.
    """
    results = []
    remaining = line.strip()

    # Remove any leading # markers
    remaining = re.sub(r'^#+\s*', '', remaining)

    for key in METADATA_KEYS:
        # Find key in remaining text
        pattern = re.compile(
            r'\*{0,2}' + re.escape(key) + r'\*{0,2}\s*[:：]\s*',
            re.IGNORECASE
        )
        match = pattern.search(remaining)
        if match:
            # Everything before this key (might contain a previous value)
            before = remaining[:match.start()].strip().rstrip('.')
            if before and results:
                # Append the value to the last result
                results[-1] = results[-1].rstrip() + ' ' + before

            # Find the value: everything after the key until the next key or end
            after = remaining[match.end():]

            # Check if there's another key coming
            next_key_pos = len(after)
            for other_key in METADATA_KEYS:
                other_pattern = re.compile(
                    r'\*{0,2}' + re.escape(other_key) + r'\*{0,2}\s*[:：]',
                    re.IGNORECASE
                )
                other_match = other_pattern.search(after)
                if other_match:
                    next_key_pos = min(next_key_pos, other_match.start())

            value = after[:next_key_pos].strip().strip('*').strip()
            # Clean trailing period
            if value.endswith('.'):
                value = value[:-1].strip()

            results.append(f"**{key}:** {value}.")
            remaining = after[next_key_pos:]

    return results


def normalize_metadata_line(stripped):
    """
    Normalize a single metadata line.
    Input could be: '**Tên chung quốc tế**: Sodium chloride.'
    Output: '**Tên chung quốc tế:** Sodium chloride.'
    """
    for key in METADATA_KEYS:
        if key in stripped:
            # Extract value after the key
            pattern = re.compile(
                r'(?:#{1,4}\s+)?\*{0,2}' + re.escape(key) + r'\*{0,2}\s*[:：]\s*(.*)$'
            )
            match = pattern.search(stripped)
            if match:
                value = match.group(1).strip().strip('*').strip()
                if value and not value.endswith('.'):
                    value += '.'
                return f"**{key}:** {value}"
    return None


def extract_header_content(stripped):
    """
    Try to extract a standard or sub-header from the stripped line text.
    Handles:
        '#### **Tương tác thuốc**'
        '## **Chỉ định**'
        '# **Liều lượng và cách dùng**'
        '#### Tương tác thuốc'  (no bold)
        '#### Thời kỳ mang thai' (no bold)
        '**Dạng thuốc và hàm lượng**' (no # at all)
    Returns (clean_text, has_trailing_content) or None.
    """
    # Try to match: optional # markers, optional bold markers, header text, optional bold markers
    # Pattern: ^#{0,4}\s*\*{0,2}\s*(header_text)\s*\*{0,2}\s*(remaining?)$
    match = re.match(
        r'^(?:#{1,4}\s+)?(?:\*{2})?\s*(.+?)\s*(?:\*{2})?\s*$',
        stripped
    )
    if match:
        text = match.group(1).strip()
        # Remove bold markers within
        text_clean = text.strip('*').strip()
        return text_clean
    return None


def has_inline_content_after_header(stripped, header_key):
    """
    Check if a line has content after the header part.
    Example: '**Dạng thuốc và hàm lượng** Kem, thuốc mỡ: 3%.'
    Returns the trailing content or None.
    """
    # Find the header in the stripped line
    # It could be wrapped in ** or preceded by #
    patterns = [
        re.compile(r'(?:#{1,4}\s+)?\*{2}' + re.escape(header_key) + r'[:：]?\*{2}\s+(.+)$'),
        re.compile(r'(?:#{1,4}\s+)?' + re.escape(header_key) + r'[:：]?\s+(.+)$'),
    ]
    for p in patterns:
        m = p.match(stripped)
        if m:
            trailing = m.group(1).strip()
            if trailing:
                return trailing
    return None


def normalize_markdown_content(content_lines, stats=None):
    """
    Processes and normalizes headings in the markdown content.

    Normalization rules:
    1. Drug titles -> # **DRUG_NAME**
    2. Metadata (Tên chung quốc tế, Mã ATC, Loại thuốc) -> **Key:** Value.
    3. Standard sections -> ## **Section Name**
    4. Sub-sections (Cách dùng, Liều dùng) -> ### *Sub-section:*
    5. Running headers/footers (DTQGVN) -> removed
    """
    if stats is None:
        stats = {"titles": 0, "metadata": 0, "sections": 0, "subsections": 0, "footers": 0}

    normalized_lines = []
    inside_code_block = False
    inside_table = False

    for idx, line in enumerate(content_lines, start=1):
        stripped = line.strip()

        # Toggle code block state
        if stripped.startswith("```"):
            inside_code_block = not inside_code_block
            normalized_lines.append(line)
            continue

        # If inside a code block, keep as is
        if inside_code_block:
            normalized_lines.append(line)
            continue

        # Keep empty lines
        if not stripped:
            normalized_lines.append(line)
            continue

        # Detect table lines (starting with |) - keep as is
        if stripped.startswith("|") or stripped.startswith("|-"):
            normalized_lines.append(line)
            continue

        # --- Step 1: Detect and remove PDF running headers/footers ---
        if is_page_header_footer(stripped):
            stats["footers"] += 1
            continue  # Remove the line entirely

        # --- Step 2: Detect inline DTQGVN within a content line ---
        # Some lines have DTQGVN embedded mid-sentence, e.g.:
        # "... viêm đại tràng do dùng clindamycin vì ... 408 **Clindamycin** DTQGVN 2 DTQGVN 2 **Clindamycin** 409"
        # We need to strip the trailing DTQGVN portion but keep the content
        dtqgvn_inline = re.search(
            r'\s+\d+\s+\*{0,2}[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯa-zàáâãèéêìíòóôõùúýăđĩũơư\s]+\*{0,2}\s+DTQGVN\s+\d+(?:\s+DTQGVN\s+\d+\s+\*{0,2}[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠƯa-zàáâãèéêìíòóôõùúýăđĩũơư\s]+\*{0,2}\s+\d+)?\s*$',
            stripped
        )
        if dtqgvn_inline and dtqgvn_inline.start() > 20:
            # There's meaningful content before the DTQGVN part
            cleaned = stripped[:dtqgvn_inline.start()].strip()
            if cleaned:
                stats["footers"] += 1
                normalized_lines.append(cleaned + "\n")
                continue

        # --- Step 3: Drug title ---
        drug_name = is_drug_title(stripped)
        if drug_name:
            stats["titles"] += 1
            normalized_lines.append(f"\n# **{drug_name}**\n")
            continue

        # --- Step 4: Inline metadata (multiple keys on one line) ---
        # Check if line has 2+ metadata keys
        meta_count = sum(1 for key in METADATA_KEYS if key in stripped)
        if meta_count >= 2:
            parts = split_inline_metadata(stripped)
            if parts:
                stats["metadata"] += len(parts)
                for part in parts:
                    normalized_lines.append(part + "\n")
                    normalized_lines.append("\n")
                continue

        # --- Step 5: Single metadata line ---
        for key in METADATA_KEYS:
            if key in stripped:
                result = normalize_metadata_line(stripped)
                if result:
                    stats["metadata"] += 1
                    normalized_lines.append(result + "\n")
                    break
        else:
            # Not a metadata line, continue to header check
            pass

        # Check if we already handled this line as metadata
        if any(key in stripped for key in METADATA_KEYS):
            result = normalize_metadata_line(stripped)
            if result:
                continue

        # --- Step 6: Standard section headers ---
        # Clean the header text by removing #, **, whitespace
        header_text = extract_header_content(stripped)
        if header_text:
            # Check standard headers
            for variant, normalized in STANDARD_HEADERS_MAP.items():
                if header_text == variant or header_text.rstrip(':') == variant.rstrip(':'):
                    # Check for inline content after header
                    trailing = has_inline_content_after_header(stripped, variant)
                    if trailing is None:
                        # Also check without colon
                        trailing = has_inline_content_after_header(stripped, variant.rstrip(':'))

                    stats["sections"] += 1
                    normalized_lines.append(normalized + "\n")
                    if trailing:
                        normalized_lines.append("\n")
                        normalized_lines.append(trailing + "\n")
                    break
            else:
                # Check sub-headers
                for variant, normalized in SUB_HEADERS_MAP.items():
                    if header_text == variant or header_text.rstrip(':') == variant.rstrip(':'):
                        stats["subsections"] += 1
                        normalized_lines.append(normalized + "\n")
                        break
                else:
                    # Not a recognized header, keep original
                    normalized_lines.append(line)
                    continue
            continue

        # --- Default: keep original line ---
        normalized_lines.append(line)

    return normalized_lines, stats


def process_file(file_path, overwrite=False, dry_run=False):
    """
    Reads the file, normalizes headings, and writes the output.
    Returns stats dict.
    """
    if not os.path.exists(file_path):
        print(f"  [ERROR] File not found: {file_path}")
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    stats = {"titles": 0, "metadata": 0, "sections": 0, "subsections": 0, "footers": 0}
    normalized, stats = normalize_markdown_content(lines, stats)

    total_changes = sum(stats.values())
    print(f"  {os.path.basename(file_path)}: {total_changes} changes "
          f"(titles={stats['titles']}, metadata={stats['metadata']}, "
          f"sections={stats['sections']}, subsections={stats['subsections']}, "
          f"footers_removed={stats['footers']})")

    if dry_run:
        return stats

    if overwrite:
        output_path = file_path
    else:
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_normalized{ext}"

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(normalized)

    return stats


def main():
    print("=" * 70)
    print("PHARMARAG-VN HEADER NORMALIZER v2.0".center(70))
    print("Chuẩn hóa header trong các chuyên luận Dược thư Quốc gia VN".center(70))
    print("=" * 70)
    print()
    print("Chọn chế độ:")
    print("  1. DRY-RUN - Xem trước (không thay đổi file)")
    print("  2. Chuẩn hóa và ghi ra file mới (*_normalized.md)")
    print("  3. Chuẩn hóa và GHI ĐÈ trực tiếp lên file gốc")
    print("  4. Xử lý CHỈ 1 file (chọn file)")
    print("-" * 70)

    choice = input("Nhập lựa chọn (1/2/3/4, mặc định 1): ").strip()
    if not choice:
        choice = "1"

    data_dir = r"d:\PharmaRAG-VN\Data\Cac_Chuyen_Luan_Thuoc"

    if not os.path.exists(data_dir):
        print(f"[ERROR] Không tìm thấy thư mục: {data_dir}")
        return

    # Get all markdown files (excluding already normalized ones)
    all_files = sorted([
        f for f in os.listdir(data_dir)
        if f.endswith(".md") and not f.endswith("_normalized.md")
    ])

    if choice == "4":
        print("\nCác file có sẵn:")
        for i, f in enumerate(all_files, 1):
            print(f"  {i}. {f}")
        file_idx = input("Chọn số thứ tự file: ").strip()
        try:
            selected = all_files[int(file_idx) - 1]
            all_files = [selected]
        except (ValueError, IndexError):
            print("[ERROR] Lựa chọn không hợp lệ!")
            return

    dry_run = choice == "1"
    overwrite = choice == "3"

    print(f"\nTìm thấy {len(all_files)} file:")
    for f in all_files:
        print(f"  - {f}")

    if not dry_run:
        mode = "GHI ĐÈ file gốc" if overwrite else "ghi ra file mới"
        confirm = input(f"\nBắt đầu xử lý ({mode})? (y/n, mặc định y): ").strip().lower()
        if confirm == "n":
            print("Đã hủy.")
            return

    print()
    total_stats = {"titles": 0, "metadata": 0, "sections": 0, "subsections": 0, "footers": 0}

    for f in all_files:
        file_path = os.path.join(data_dir, f)
        stats = process_file(file_path, overwrite=overwrite, dry_run=dry_run)
        if stats:
            for k in total_stats:
                total_stats[k] += stats[k]

    print()
    print("=" * 70)
    print("TỔNG KẾT".center(70))
    print("-" * 70)
    print(f"  Tiêu đề thuốc chuẩn hóa:     {total_stats['titles']}")
    print(f"  Metadata chuẩn hóa:           {total_stats['metadata']}")
    print(f"  Section headers chuẩn hóa:    {total_stats['sections']}")
    print(f"  Sub-section headers chuẩn hóa:{total_stats['subsections']}")
    print(f"  Running headers/footers xóa:  {total_stats['footers']}")
    print(f"  TỔNG THAY ĐỔI:                {sum(total_stats.values())}")
    print("=" * 70)

    if dry_run:
        print("\n[DRY-RUN] Không có file nào bị thay đổi.")
        print("Chạy lại với chế độ 2 hoặc 3 để áp dụng thay đổi.")


if __name__ == "__main__":
    main()
