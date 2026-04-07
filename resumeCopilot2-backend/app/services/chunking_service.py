"""
Chunking Service — 把履歷文字切成結構化的段落（Section-based Chunking）。

履歷的結構通常是：
  名字 / 聯絡資訊
  Technical Skills
  Working Experience
  Education
  Projects
  ...

策略：
1. 用常見的 section 標題關鍵字比對，找出每個段落的起始位置
2. 根據起始位置把文字切開，歸類到對應的 section（experience / education / project / skills）
3. 如果某個 section 太長（超過 600 字），再細切成多個 chunks

切好的 chunks 之後會：
- 存進 PostgreSQL（resume_chunks table）— 當作原始紀錄
- 存進 Chroma 向量資料庫 — 用來做 RAG 檢索
"""

import re
import uuid


# --- Section 標題關鍵字對照表 ---
# key = 我們定義的 section 名稱（會存進 DB）
# value = 可能出現在履歷裡的標題關鍵字（不分大小寫）
SECTION_KEYWORDS: dict[str, list[str]] = {
    "experience": [
        "experience", "working experience", "work experience",
        "employment", "professional experience", "career",
    ],
    "education": [
        "education", "academic", "certificate", "certification",
        "diploma", "degree",
    ],
    "project": [
        "projects", "project", "programming projects", "programming project",
        "personal projects", "side projects", "portfolio",
    ],
    "skills": [
        "skills", "skill", "technical skills", "technologies", "tech stack",
        "competencies", "proficiency",
    ],
}

# 每個 chunk 的目標字數上限（超過就細切）
MAX_CHUNK_SIZE = 600


def chunk_resume(text: str) -> list[dict]:
    """
    把履歷全文切成結構化的 chunks。

    Args:
        text: 履歷全文（從 PDF 提取或使用者直接貼上的）

    Returns:
        list of dict，每個 dict 包含：
        - section_name: str（experience / education / project / skills / header）
        - content: str（該段落的文字）
        - chunk_index: int（同一 section 內的流水號，從 0 開始）

    範例：
        [
            {"section_name": "header", "content": "Po-Yu Chao...", "chunk_index": 0},
            {"section_name": "skills", "content": "Programming Languages...", "chunk_index": 0},
            {"section_name": "experience", "content": "Full-Stack Developer...", "chunk_index": 0},
            {"section_name": "experience", "content": "Software Engineer...", "chunk_index": 1},
            ...
        ]
    """
    # Step 1: 找出每個 section 的起始位置
    sections = _find_sections(text)

    # Step 2: 如果完全找不到任何 section，就整份當一個 chunk
    if not sections:
        return [{"section_name": "full_resume", "content": text.strip(), "chunk_index": 0}]

    # Step 3: 把文字切開，歸類到對應 section
    raw_chunks = _split_by_sections(text, sections)

    # Step 4: 太長的 section 再細切
    final_chunks = _split_long_chunks(raw_chunks)

    return final_chunks


def _find_sections(text: str) -> list[tuple[int, str]]:
    """
    掃描全文，找出每個 section 標題的位置。

    回傳 [(起始位置, section名稱), ...] 按位置排序。

    辨識邏輯：逐行檢查，如果某一行「像標題」（短、含關鍵字），
    就認定它是某個 section 的開頭。
    """
    sections = []
    lines = text.split("\n")
    current_pos = 0  # 追蹤目前在全文中的字元位置

    for line in lines:
        stripped = line.strip()

        # 標題通常很短（< 80 字元）且含有關鍵字
        if stripped and len(stripped) < 80:
            section_name = _match_section(stripped)
            if section_name:
                sections.append((current_pos, section_name))

        # 移動位置指標（+1 是換行符號）
        current_pos += len(line) + 1

    return sections


def _match_section(line: str) -> str | None:
    """
    判斷一行文字是否是某個 section 的標題。

    把行文字轉小寫，去掉常見的裝飾符號後，
    跟每個 section 的關鍵字比對。
    """
    # 清理：去掉裝飾符號（常見的有 •、-、:、|、=）
    cleaned = re.sub(r"[•\-:|\=\*#]", " ", line).strip().lower()

    for section_name, keywords in SECTION_KEYWORDS.items():
        for keyword in keywords:
            # 用 word boundary 確保不會誤判（例如 "inexperience" 不應匹配 "experience"）
            if re.search(rf"\b{re.escape(keyword)}\b", cleaned):
                return section_name

    return None


def _split_by_sections(text: str, sections: list[tuple[int, str]]) -> list[dict]:
    """
    根據找到的 section 位置，把文字切開。

    sections[0] 之前的文字歸類為 "header"（通常是姓名、聯絡資訊）。
    """
    chunks = []

    # 第一個 section 之前的內容 → header
    first_pos = sections[0][0]
    header_text = text[:first_pos].strip()
    if header_text:
        chunks.append({
            "section_name": "header",
            "content": header_text,
            "chunk_index": 0,
        })

    # 依序切出每個 section 的內容
    for i, (pos, section_name) in enumerate(sections):
        # 結束位置 = 下一個 section 的起始位置，或全文結尾
        end_pos = sections[i + 1][0] if i + 1 < len(sections) else len(text)
        content = text[pos:end_pos].strip()

        if content:
            chunks.append({
                "section_name": section_name,
                "content": content,
                "chunk_index": 0,  # 先暫時填 0，後面再重新編號
            })

    return chunks


def _split_long_chunks(chunks: list[dict]) -> list[dict]:
    """
    如果某個 chunk 超過 MAX_CHUNK_SIZE 字，按段落切成多個小 chunk。
    同時重新編排 chunk_index（同一 section 內從 0 開始）。
    """
    final = []
    # 追蹤每個 section 目前的 index
    section_counters: dict[str, int] = {}

    for chunk in chunks:
        section = chunk["section_name"]
        content = chunk["content"]

        if section not in section_counters:
            section_counters[section] = 0

        if len(content) <= MAX_CHUNK_SIZE:
            # 不需要切，直接加入
            chunk["chunk_index"] = section_counters[section]
            section_counters[section] += 1
            final.append(chunk)
        else:
            # 太長了，按「空行」切開（履歷裡不同經歷通常用空行分隔）
            sub_chunks = _split_by_paragraphs(content, MAX_CHUNK_SIZE)
            for sub in sub_chunks:
                final.append({
                    "section_name": section,
                    "content": sub,
                    "chunk_index": section_counters[section],
                })
                section_counters[section] += 1

    return final


def _split_by_paragraphs(text: str, max_size: int) -> list[str]:
    """
    按段落（空行）切分文字，盡量讓每個 chunk 不超過 max_size 字。

    如果單一段落就超過 max_size，那就保留原樣（不硬切，避免破壞語意）。
    """
    # 用「連續兩個以上換行」來分段
    paragraphs = re.split(r"\n{2,}", text)
    result = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if not current:
            current = para
        elif len(current) + len(para) + 2 <= max_size:
            current += "\n\n" + para
        else:
            result.append(current)
            current = para

    if current:
        result.append(current)

    return result
