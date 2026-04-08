"""
VectorStore Service — 用 pgvector 做向量搜尋。

改用 pgvector 後，向量資料直接存在 PostgreSQL 裡（Cloud SQL），
不需要額外維護 Chroma 服務。
"""

import uuid
from functools import lru_cache

from langchain_postgres import PGVector
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings

from app.config import get_settings


@lru_cache
def get_embeddings() -> Embeddings:
    """
    建立 Embedding 模型實例。
    不管 LLM 用 OpenAI 或 Claude，Embedding 都統一用 OpenAI。
    """
    settings = get_settings()

    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.openai_api_key,
    )


@lru_cache
def get_vectorstore() -> PGVector:
    """
    建立 pgvector 向量資料庫連線。
    直接用同一個 PostgreSQL，不需要額外服務。
    """
    settings = get_settings()
    # pgvector 需要同步的 connection string（psycopg）
    # 把 asyncpg 換成 psycopg
    sync_url = settings.database_url.replace(
        "postgresql+asyncpg", "postgresql+psycopg"
    )

    return PGVector(
        collection_name="resume_chunks",
        embeddings=get_embeddings(),
        connection=sync_url,
    )


def store_chunks_to_vectorstore(
    resume_id: uuid.UUID, chunks: list[dict]
) -> list[str]:
    """
    把切好的 chunks 存進 pgvector。
    """
    vectorstore = get_vectorstore()

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

    ids = vectorstore.add_documents(documents)
    return ids


def search_chunks_by_resume(
    resume_id: uuid.UUID, query: str, k: int = 3
) -> list[Document]:
    """
    搜尋某份履歷中最相關的 chunks。
    用 metadata 篩選只搜指定 resume_id 的 chunks。
    """
    vectorstore = get_vectorstore()
    return vectorstore.similarity_search(
        query=query,
        k=k,
        filter={"resume_id": str(resume_id)},
    )


def delete_chunks_from_vectorstore(resume_id: uuid.UUID) -> None:
    """
    刪除某份履歷在 pgvector 中的所有 chunks。
    """
    vectorstore = get_vectorstore()
    # PGVector 的刪除方式：透過 collection 過濾
    results = vectorstore.similarity_search(
        query="",
        k=1000,
        filter={"resume_id": str(resume_id)},
    )
    if results:
        ids = [doc.metadata.get("id") for doc in results if doc.metadata.get("id")]
        if ids:
            vectorstore.delete(ids=ids)
