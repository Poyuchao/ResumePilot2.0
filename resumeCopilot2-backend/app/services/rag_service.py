"""
RAG Service — 用 LangChain 組裝 Retrieval-Augmented Generation 流程。

RAG 的完整流程：
1. 使用者提問
2. 從向量資料庫檢索相關的履歷 chunks（Retriever）
3. 把 chunks + 問題組成 prompt（PromptTemplate）
4. 送給 LLM 產生回答（ChatModel）

LangChain 用 chain（鏈）把這些步驟串起來，
資料會像流水線一樣依序通過每個步驟。
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from app.services.llm_service import get_llm
from app.services.vectorstore_service import get_vectorstore


# --- Prompt 模板 ---
# 不同模式用不同的 system prompt，讓 AI 扮演不同角色

PROMPT_TEMPLATES = {
    "general": "你是一位專業的履歷顧問。根據以下履歷內容回答使用者的問題，提供具體、有建設性的建議。",
    "hr": "你是一位資深 HR 主管。從招募者的角度分析履歷，關注求職者的整體印象、職涯發展軌跡、以及是否符合職位需求。",
    "technical": "你是一位資深技術面試官。從技術能力的角度分析履歷，評估技術深度、專案經驗的含金量、以及潛在的技術面試問題。",
}

# --- 分析用 Prompt（依 mode 切換角色）---

ANALYSIS_SYSTEM_PROMPTS = {
    "general": "你是一位專業的履歷顧問。請從整體角度分析這份履歷，提供全面的評估和改善建議。",
    "hr": "你是一位資深 HR 主管。請從招募者的角度分析這份履歷，關注求職者的整體印象、職涯發展軌跡、是否能通過初步篩選。",
    "technical": "你是一位資深技術面試官。請從技術能力的角度分析這份履歷，評估技術深度、專案經驗的含金量、以及可能的技術面試問題。",
}

ANALYSIS_HUMAN_TEMPLATE = (
    "請分析這份履歷：\n\n{resume_text}\n\n"
    "你必須只回傳純 JSON，不要加任何 markdown 格式或額外文字。\n"
    '格式如下：\n'
    '{{\n'
    '  "summary": "一段簡短的履歷摘要（2-3 句話）",\n'
    '  "education_background": {{"school": "學校名稱", "major": "科系", "degree": "學位"}},\n'
    '  "recommended_roles": ["職位1", "職位2", "職位3"],\n'
    '  "suggestions": ["建議1", "建議2", "建議3"]\n'
    '}}'
)


def build_chat_chain(mode: str = "general"):
    """
    建立對話用的 RAG chain。

    LangChain 的 chain 就像樂高積木：
    retriever → 取得相關 chunks
    prompt    → 把 chunks + 問題組成完整 prompt
    llm       → 送給 AI 回答
    parser    → 把 AI 回覆轉成純文字

    用 | 運算子把它們串起來（LangChain 的 LCEL 語法）。
    """
    llm = get_llm()
    vectorstore = get_vectorstore()

    # Retriever：從向量資料庫檢索最相關的 3 個 chunks
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3},
    )

    system_message = PROMPT_TEMPLATES.get(mode, PROMPT_TEMPLATES["general"])

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message + "\n\n參考的履歷內容：\n{context}"),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{question}"),
    ])

    # 用 LCEL（LangChain Expression Language）串接各步驟
    chain = (
        {
            "context": retriever | _format_docs,  # 檢索 → 格式化
            "question": RunnablePassthrough(),     # 問題直接傳過去
            "chat_history": lambda x: x.get("chat_history", []),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


def build_analysis_chain(mode: str = "general"):
    """
    建立履歷分析用的 chain（不需要 RAG，直接分析全文）。
    根據 mode 切換不同的 system prompt（不同角色）。
    """
    llm = get_llm()
    system_msg = ANALYSIS_SYSTEM_PROMPTS.get(mode, ANALYSIS_SYSTEM_PROMPTS["general"])

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_msg),
        ("human", ANALYSIS_HUMAN_TEMPLATE),
    ])

    return prompt | llm | StrOutputParser()


def _format_docs(docs) -> str:
    """把檢索到的 Document 物件格式化成文字"""
    return "\n\n---\n\n".join(doc.page_content for doc in docs)
