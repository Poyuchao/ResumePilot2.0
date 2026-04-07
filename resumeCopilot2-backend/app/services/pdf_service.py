"""
PDF 解析 Service — 從 PDF 檔案提取純文字。

使用 pypdf 讀取 PDF 的每一頁，合併成完整文字。
這是 PDF 上傳功能的核心：拿到文字後就能存進資料庫，
後續跟純文字履歷走一樣的分析流程。
"""

from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    從 PDF 的 bytes 內容提取文字。

    Args:
        file_bytes: PDF 檔案的二進位內容（從 UploadFile.read() 取得）

    Returns:
        提取出的純文字（各頁之間用換行分隔）

    Raises:
        ValueError: PDF 無法解析或提取不到任何文字
    """
    reader = PdfReader(BytesIO(file_bytes))

    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)

    full_text = "\n".join(pages_text).strip()

    if not full_text:
        raise ValueError("PDF 中沒有可提取的文字，可能是純圖片的掃描檔")

    return full_text
