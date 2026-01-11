from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

from .config import settings
from .models import QueryRequest, QueryResponse
from .rag_engine import RAGComponents
from .graph import GraphBuilder
from .logger import setup_logging
import logging

logger = logging.getLogger(__name__)

# Global Variables (State)
rag_system = None
app_graph = None

async def init_system():
    """初始化系統元件"""
    global rag_system, app_graph
    rag_system = RAGComponents()
    builder = GraphBuilder(rag_system)
    app_graph = builder.build()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    await init_system()
    yield
    # Shutdown
    # Clean up if necessary

app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """健康檢查"""
    return {
        "status": "running",
        "message": f"{settings.APP_TITLE} API"
    }

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """查詢端點"""
    if not app_graph:
        raise HTTPException(status_code=503, detail="系統未初始化")
    
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="問題不能為空")
    
    # 執行查詢
    initial_state = {
        "original_query": request.question,
        "rewritten_query": "",
        "retrieved_docs": [],
        "reranked_docs": [],
        "context": "",
        "final_answer": "",
        "error": "",
        "tool_call_count": 0,  # 初始化工具調用計數器
        "messages": []
    }
    
    try:
        # 🔑 建立包含 thread_id 的配置項目
        config = {"configurable": {"thread_id": request.thread_id}}
        
        # invoke returns the final state
        result = app_graph.invoke(initial_state, config=config)
        
        # 處理 final_answer 可能為 None 的情況（例如達到工具調用限制時）
        final_answer = result.get("final_answer")
        if final_answer is None:
            # 檢查是否達到工具調用限制
            tool_call_count = result.get("tool_call_count", 0)
            if tool_call_count > 3:
                final_answer = "抱歉，我無法完成這個操作（達到工具調用次數限制）。請簡化您的問題或提供更明確的資訊。"
            else:
                final_answer = "抱歉，我無法生成適當的回覆。請重新表述您的問題。"
        
        return QueryResponse(
            success=True,
            original_query=result.get("original_query", ""),
            rewritten_query=result.get("rewritten_query", ""),
            answer=final_answer,
            context=result.get("context", "")
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return QueryResponse(
            success=False,
            error=str(e)
        )

@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "system_initialized": app_graph is not None
    }

if __name__ == "__main__":
    logger.info(f"Starting {settings.APP_TITLE}")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
