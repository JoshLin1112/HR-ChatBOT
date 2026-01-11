from typing import TypedDict, List, Annotated, Sequence
from pydantic import BaseModel
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# --- Pydantic Models for API ---
class QueryRequest(BaseModel):
    question: str
    thread_id: str = "default_thread"  # 新增 thread_id 支援多輪對話

class QueryResponse(BaseModel):
    success: bool
    original_query: str = ""
    rewritten_query: str = ""
    answer: str = ""
    context: str = ""
    error: str = ""

# --- TypedDict for LangGraph State ---
class GraphState(TypedDict):
    """LangGraph 狀態定義"""
    original_query: str
    rewritten_query: str
    retrieved_docs: List[Document]
    reranked_docs: List[Document]
    answer: str
    category: str # User question category (e.g., sick_leave)
    final_answer: str
    error: str
    context: str
    retry_count: int
    tool_call_count: int  # 追蹤工具調用次數，避免無限循環
    # 用 Annotated 標註 add_messages，讓訊息可以自動累加
    messages: Annotated[Sequence[BaseMessage], add_messages]
