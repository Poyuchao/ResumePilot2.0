"""
VectorStore Service — 用 LangChain 整合 Chroma 向量資料庫。

LangChain 的 RAG 流程：
1. 文字 → Embedding 模型 → 向量
2. 向量存入 VectorStore（這裡用 Chroma）
3. 查詢時，把問題也轉成向量，找出最相似的 chunks

這個 service 負責：
- get_vectorstore()：取得 Chroma 連線（讀取 / 檢索用）
- store_chunks_to_vectorstore()：把切好的 chunks 存進 Chroma（寫入用）
- delete_chunks_from_vectorstore()：刪除某份履歷的所有 chunks
"""

import uuid
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings

from app.config import get_settings


@lru_cache
def get_embeddings() -> Embeddings:
    """
    建立 Embedding 模型實例。
    Embedding = 把文字轉成向量（一串數字），用來計算文字之間的相似度。

    注意：Claude 沒有提供 Embedding API，
    所以不管 LLM 用 OpenAI 或 Claude，Embedding 都統一用 OpenAI。
    這是業界常見做法，embedding 和 chat 用不同 provider 完全沒問題。
    """
    settings = get_settings()

    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.openai_api_key,
    )


@lru_cache
def get_vectorstore() -> Chroma:
    """
    建立 Chroma 向量資料庫連線。

    collection_name 就像 DB 的 table 名稱，
    同一個 collection 裡的文件可以一起被搜尋。

    persist_directory：指定 Chroma 資料存放位置。
    有了這個，重啟 server 後資料還在，不同 process 也能共享。
    沒指定的話是 in-memory，server 一關就沒了。
    """
    return Chroma(
        collection_name="resume_chunks",
        embedding_function=get_embeddings(),
        persist_directory="./chroma_data",  # 持久化到本地資料夾
        collection_metadata={"hnsw:space": "cosine"},  # 用 cosine 相似度
    )


def store_chunks_to_vectorstore(
    resume_id: uuid.UUID, chunks: list[dict]
) -> list[str]:
    """
    把切好的 chunks 存進 Chroma 向量資料庫。

    每個 chunk 會被轉成 LangChain 的 Document 物件：
    - page_content = chunk 的文字內容
    - metadata = 額外資訊（resume_id, section_name, chunk_index）
      → 之後檢索時可以用 metadata 做篩選（例如只搜某份履歷的 chunks）

    Args:
        resume_id: 這份履歷的 UUID
        chunks: chunking_service.chunk_resume() 回傳的 list of dict

    Returns:
        Chroma 回傳的 document IDs
    """
    vectorstore = get_vectorstore()

    # 把 dict 轉成 LangChain Document
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk["content"],
            metadata={
                "resume_id": str(resume_id),
                "section_name": chunk["section_name"],
                "chunk_index": chunk["chunk_index"],
            },
        )
        documents.append(doc)

    # 存入 Chroma（內部會自動呼叫 embedding 模型把文字轉向量）
    ids = vectorstore.add_documents(documents)
    return ids


def search_chunks_by_resume(
    resume_id: uuid.UUID, query: str, k: int = 3
) -> list[Document]:
    """
    搜尋某份履歷中最相關的 chunks。

    跟一般的 similarity_search 不同，這裡加了 metadata 篩選：
    只搜屬於指定 resume_id 的 chunks，不會撈到別的履歷的內容。

    Args:
        resume_id: 要搜的那份履歷的 UUID
        query: 使用者的問題
        k: 回傳幾個最相關的 chunks（預設 3）

    Returns:
        LangChain Document 的 list，按相似度排序
    """
    vectorstore = get_vectorstore()
    return vectorstore.similarity_search(
        query=query,
        k=k,
        filter={"resume_id": str(resume_id)},  # 只搜這份履歷的 chunks
    )


def delete_chunks_from_vectorstore(resume_id: uuid.UUID) -> None:
    """
    刪除某份履歷在 Chroma 中的所有 chunks。
    刪除履歷時要一併清除向量資料庫裡的資料。
    """
    vectorstore = get_vectorstore()
    vectorstore._collection.delete(
        where={"resume_id": str(resume_id)}
    )
