from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_ollama import ChatOllama
from langdetect import detect
import json
import logging
from typing import Literal
from .models import GraphState
from .rag_engine import RAGComponents
from .config import settings
import opencc
from .prompts import (
    CLASSIFICATION_PROMPT,
    CLARIFICATION_PROMPT,
    REWRITE_PROMPT_RETRY,
    REWRITE_PROMPT_NORMAL,
    GENERATE_SYSTEM_PROMPT,
    GUARDRAIL_PROMPT,
    OPTIMIZE_RESPONSE_PROMPT
)


logger = logging.getLogger(__name__)

class GraphBuilder:
    def __init__(self, rag_components):
        self.rag_engine = rag_components
        self.model = ChatOllama(
            model=settings.OLLAMA_MODEL, 
            base_url=settings.OLLAMA_BASE_URL, 
            temperature=0, 
            format="json"
        )
        
        # Classification Chain
        classification_prompt = ChatPromptTemplate.from_template(CLASSIFICATION_PROMPT)
        self.classification_chain = classification_prompt | self.model | StrOutputParser()
        
        # Clarification Chain
        clarification_prompt = ChatPromptTemplate.from_template(CLARIFICATION_PROMPT)
        # Clarification Chain
        clarification_prompt = ChatPromptTemplate.from_template(CLARIFICATION_PROMPT)
        self.clarification_chain = clarification_prompt | self.model | StrOutputParser()

        # Guardrail Chain (LLM-based)
        guardrail_prompt = ChatPromptTemplate.from_template(GUARDRAIL_PROMPT)
        self.guardrail_chain = guardrail_prompt | self.model | StrOutputParser()
        
        # Optimization Chain
        optimization_prompt = ChatPromptTemplate.from_template(OPTIMIZE_RESPONSE_PROMPT)
        self.optimization_chain = optimization_prompt | self.model | StrOutputParser()
        
        # Initialize OpenCC for Simplified to Traditional conversion
        self.cc = opencc.OpenCC('s2t')
    
    def _format_messages_to_str(self, messages) -> str:
        """Helper to format messages into a string history for rewriter/generator"""
        history_str = ""
        # 排除最後一條 HumanMessage，因為它通常是當前正在處理的問題
        # 這樣可以避免 rewriter 看到重複的問題
        msgs_to_process = messages[:-1] if messages and isinstance(messages[-1], HumanMessage) else messages
        
        for msg in msgs_to_process:
            if isinstance(msg, HumanMessage):
                history_str += f"Human: {msg.content}\n"
            elif isinstance(msg, SystemMessage):
                continue
            elif hasattr(msg, '__class__') and msg.__class__.__name__ == 'ToolMessage':
                # 將工具結果摘要加入歷史，有助於上下文理解
                content = str(msg.content)
                if len(content) > 100:
                    content = content[:100] + "..."
                history_str += f"System (Tool Result): {content}\n"
            else:
                # AI Message
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    # 如果 AI 調用了工具，記錄一下調用的動作
                    tool_names = [tc.get('name') for tc in msg.tool_calls]
                    history_str += f"AI (Action): 調用了工具 {', '.join(tool_names)}\n"
                
                if msg.content:
                    history_str += f"AI: {msg.content}\n"
    
        return history_str.strip()

    def initialize_conversation(self, state: GraphState) -> GraphState:
        """節點 0: 初始化對話，將用戶新問題加入 messages"""
        logger.info("Checking conversation initialization...")
        original_query = state["original_query"]
        messages = state.get("messages", [])
        
        # 檢查最後一條訊息是否已經是這個問題（避免重複添加）
        if not messages or (isinstance(messages[-1], HumanMessage) and messages[-1].content != original_query) or not isinstance(messages[-1], HumanMessage):
             logger.info(f"Adding new user query to messages: {original_query[:50]}...")
             return {
                "messages": [HumanMessage(content=original_query)]
            }
        
        logger.info(f"Question already in messages, skipping duplication")
        return {"messages": []}

    def guardrail_node(self, state: GraphState) -> GraphState:
        """節點 0.5: 路由守衛（LLM 篩選）"""
        logger.info("Executing router guardrail (LLM)...")
        query = state["original_query"]
        messages = state.get("messages", [])
        
        # 準備對話歷史概要
        history_str = self._format_messages_to_str(messages)
        
        # 調用 LLM 判斷
        try:
            response = self.guardrail_chain.invoke({
                "history_str": history_str if history_str else "無先前對話",
                "query": query
            })
            result = json.loads(response)
            decision = result.get("decision", "allowed")
            reason = result.get("reason", "無原因")
            block_msg = result.get("response", "")
            
            logger.info(f"Guard decision: {decision} ({reason})")
            
            if decision == "blocked":
                logger.warning(f"Request blocked: {block_msg}")
                return {
                    "error": "blocked",
                    "final_answer": block_msg if block_msg else "抱歉，我只能回答與請假或差勤相關的問題。"
                }
            
        except Exception as e:
            logger.error(f"Guard execution error (defaulting to pass): {e}")
            return {"error": "pass"}
            
        logger.info("Request passed")
        return {"error": "pass"}
    
    def check_guardrail(self, state: GraphState) -> Literal["continue", "end"]:
        """條件判斷: 守衛攔截結果"""
        error = state.get("error")
        if error == "blocked":
            return "end"
        return "continue"

    def rewrite_node(self, state: GraphState) -> GraphState:
        """節點 1: 查詢重寫（支援多輪對話上下文）"""
        logger.info("Executing query rewrite...")
        query = state["original_query"]
        retry_count = state.get("retry_count", 0)
        
        # 取得對話歷史
        messages = state.get("messages", [])
        history_str = self._format_messages_to_str(messages)
        
        # 🔍 調試輸出：檢查是否有歷史
        logger.debug(f"History status - Messages: {len(messages)}, History len: {len(history_str)}")
        if history_str:
            logger.debug(f"History content: {history_str}")
        else:
            logger.debug("No history (likely first turn)")
        
        # 根據重試次數選擇提示詞
        if retry_count > 0:
            logger.info(f"Retry count {retry_count}, attempting different keywords...")
            prompt = REWRITE_PROMPT_RETRY.format(
                history_str=history_str if history_str else "無先前對話",
                query=query
            )
        else:
            prompt = REWRITE_PROMPT_NORMAL.format(
                history_str=history_str if history_str else "無先前對話",
                query=query
            )
        
        rewritten = self.rag_engine.llm_rewriter.invoke(prompt).strip()
        
        logger.info(f"Original query: {query}")
        logger.info(f"Rewritten query: {rewritten}")
        logger.info(f"Used history: {'Yes' if history_str else 'No'}")
        
        return {
            "rewritten_query": rewritten,
            "retry_count": retry_count + 1
        }
    
    def classify_query(self, state: GraphState) -> GraphState:
        """節點 2: 查詢分類"""
        logger.info("Executing query classification...")
        original_query = state["original_query"]
        query_to_classify = state.get("rewritten_query") or original_query
        
        response = self.classification_chain.invoke({"question": query_to_classify})
        
        try:
            category_data = json.loads(response)
            category = category_data.get("category", "other")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse classification JSON: {response}")
            category = "other"
        
        logger.info(f"Original query: {original_query}")
        logger.info(f"Classification: {category}")
        
        return {"category": category}

    
    def retrieve_node(self, state: GraphState) -> GraphState:
        """節點 3: 文件檢索"""
        logger.info("Executing document retrieval...")
        query = state["rewritten_query"]
        category = state.get("category", "other")
        
        retrieved_docs = self.rag_engine.search(query, category=category)
        
        return {"retrieved_docs": retrieved_docs}
    
    def rerank_node(self, state: GraphState) -> GraphState:
        """節點 4: 檢索重排序"""
        logger.info("Executing reranking...")
        query = state["rewritten_query"]
        docs = state.get("retrieved_docs", [])
        
        # 針對檢索到的問題與使用者問題進行rerank
        reranked_docs = self.rag_engine.rerank(docs, query)
        
        # 附加答案到檢索到的問題
        context_parts = []
        for i, doc in enumerate(reranked_docs, start=1):
            question = doc.page_content.replace('問題:', '').strip()
            answer = doc.metadata.get("answer", "")
            doc.page_content = f"問題: {question}\n答案: {answer}"
            
            context_parts.append(
                f"第{i}名相關文件:\n問題: {question}\n答案: {answer}"
            )
        
        context = "\n\n".join(context_parts)
        logger.debug(f"Context length: {len(context)}")
        
        return {
            "reranked_docs": reranked_docs,
            "context": context
        }
    
    def clarify_node(self, state: GraphState) -> GraphState:
        """節點 5: 檢索結果驗證"""
        logger.info("Executing retrieval verification...")
        original_query = state["original_query"]
        context = state.get("context", "")
        
        if not context:
            logger.warning("No context found, defaulting to fail")
            return {"error": "no_content"}
            
        decision = self.clarification_chain.invoke({
            "question": original_query, 
            "context": context
        }).strip().lower()
        
        if "yes" in decision:
            decision = "yes"
        else:
            decision = "no"
        
        logger.info(f"Verification result: {decision}")
        
        return {"error": decision} 
    
    def generate_node(self, state: GraphState) -> GraphState:
        """節點 4: 答案生成 (支援 Tool Call)"""
        logger.info("Generating answer or calling tools...")
        
        messages = state.get("messages", [])
        logger.debug(f"Current messages count: {len(messages)}")
        
        # 打印訊息摘要
        for i, msg in enumerate(messages):
            msg_type = type(msg).__name__
            if isinstance(msg, HumanMessage):
                preview = f"Q: {msg.content[:50]}..."
            elif isinstance(msg, SystemMessage):
                preview = "[System]"
            elif hasattr(msg, 'tool_calls') and msg.tool_calls:
                preview = f"[Tool Call: {len(msg.tool_calls)}]"
            elif hasattr(msg, '__class__') and msg.__class__.__name__ == 'ToolMessage':
                preview = f"[Tool Result: {str(msg.content)[:50]}...]"
            else:
                preview = f"A: {str(msg.content)[:50]}..."
            logger.debug(f"  [{i}] {msg_type}: {preview}")
        
        # 取得歷史對話字串（用於構建新的系統提示）
        history_str = self._format_messages_to_str(messages)
        
        # 建立系統提示詞
        system_prompt = GENERATE_SYSTEM_PROMPT.format(
            context=state.get('context')
        )
        
        # 🔑 構建要發送給 LLM 的訊息列表
        # 策略：始終在最前面放置最新的 SystemMessage
        llm_messages = [SystemMessage(content=system_prompt)]
        
        # 然後加入所有非 SystemMessage 的訊息
        for msg in messages:
            if not isinstance(msg, SystemMessage):
                llm_messages.append(msg)
        
        logger.debug(f"Calling LLM with {len(llm_messages)} messages")
        
        # 呼叫 LLM
        response = self.rag_engine.llm_generator.invoke(llm_messages)
        
        logger.debug(f"LLM Response type: {type(response).__name__}")
        logger.debug(f"Content preview: {response.content[:150] if response.content else 'None'}...")
        if response.tool_calls:
            logger.info(f"Tool calls detected: {len(response.tool_calls)}")
            for tc in response.tool_calls:
                logger.debug(f"  - {tc.get('name', 'unknown')}")
        
        # 只返回新的 response，add_messages 會自動追加
        return {
            "messages": [response],
            "final_answer": response.content if not response.tool_calls else None
        }


    def increment_tool_count(self, state: GraphState) -> GraphState:
        """在工具執行後增加計數"""
        tool_call_count = state.get("tool_call_count", 0) + 1
        logger.info(f"Tool execution completed, count: {tool_call_count}")
        return {"tool_call_count": tool_call_count}
        
    def decide_to_rewrite(self, state: GraphState) -> Literal["rewrite", "generate"]:
        """條件判斷: 是否重寫"""
        decision = state.get("error")
        retry_count = state.get("retry_count", 0)
        
        if decision == "no" and retry_count < 3:
            logger.info("Retrieval validation failed, returning to Rewrite...")
            return "rewrite"
        else:
            if decision == "no":
                logger.warning("Max retries reached, proceeding to generation...")
            else:
                logger.info("Retrieval validation passed, proceeding to generation...")
            return "generate"
    
    def should_continue(self, state: GraphState) -> Literal["tools", "__end__"]:
        """條件判斷: 是否應該繼續（調用工具或結束）"""
        logger.debug("Deciding execution path (should_continue)...")
        
        messages = state.get("messages", [])
        tool_call_count = state.get("tool_call_count", 0)
        
        logger.debug(f"Current state - Messages: {len(messages)}, Tool count: {tool_call_count}")
        
        if not messages:
            logger.warning("Message list is empty, ending process")
            return END
        
        last_message = messages[-1]
        
        has_tool_calls = hasattr(last_message, 'tool_calls') and last_message.tool_calls
        
        if has_tool_calls:
            logger.debug(f"Tool calls detected: {last_message.tool_calls}")
            
            # 檢查工具調用次數限制
            if tool_call_count >= 3:
                logger.warning("Max tool calls reached (3), forcing end")
                return END
            
            logger.info("Tool usage confirmed, switching to tools node")
            return "tools"
        else:
            logger.info("No tool calls, generation complete, proceeding to optimization")
            return "optimize"

    def optimize_response_node(self, state: GraphState) -> GraphState:
        """節點: 回答優化 (格式、語言、結尾)"""
        logger.info("Executing response optimization...")
        
        final_answer = state.get("final_answer")
        
        # Fallback if final_answer is missing but last message is likely the answer
        if not final_answer:
            messages = state.get("messages", [])
            if messages and isinstance(messages[-1], AIMessage):
                final_answer = messages[-1].content
        
        if not final_answer:
             logger.warning("No answer to optimize.")
             return {}

        try:
            response = self.optimization_chain.invoke({"answer": final_answer})
            
            # Parse JSON response
            try:
                data = json.loads(response)
                # Get the optimized answer, or fallback to the whole response if key missing
                optimized_answer = data.get("optimized_answer") or data.get("response", response)
                
                # If for some reason the value is not a string (e.g. nested dict), convert to string
                if not isinstance(optimized_answer, str):
                    optimized_answer = str(optimized_answer)
                    
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse optimization JSON, using raw response: {response[:50]}...")
                optimized_answer = response

            # Ensure Traditional Chinese
            optimized_answer = self.cc.convert(optimized_answer)

            logger.info("Response optimized successfully.")
            return {"final_answer": optimized_answer}
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return {"final_answer": final_answer + "\n\n若有其他需求歡迎詢問"}

    # 此節點暫不使用


    def build(self):
        """建立 LangGraph 工作流程"""
        workflow = StateGraph(GraphState)
        
        # 添加所有節點
        workflow.add_node("initialize", self.initialize_conversation)  # 新增
        workflow.add_node("guardrail", self.guardrail_node)      # 新增
        workflow.add_node("rewrite", self.rewrite_node)
        workflow.add_node("classify_query", self.classify_query)
        workflow.add_node("retrieve", self.retrieve_node)
        workflow.add_node("rerank", self.rerank_node) 
        workflow.add_node("clarify", self.clarify_node)
        workflow.add_node("generate", self.generate_node)
        workflow.add_node("tools", ToolNode(self.rag_engine.tools))
        workflow.add_node("increment_count", self.increment_tool_count)  # 新增
        workflow.add_node("optimize_response", self.optimize_response_node) # 新增優化節點

        # 定義流程邊
        workflow.set_entry_point("initialize")  # 從初始化開始
        workflow.add_edge("initialize", "guardrail") # 改為接守衛
        
        # 守衛條件邊
        workflow.add_conditional_edges(
            "guardrail",
            self.check_guardrail,
            {
                "continue": "rewrite",
                "end": END
            }
        )
        workflow.add_edge("rewrite", "classify_query")
        workflow.add_edge("classify_query", "retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "clarify")
        
        # 條件邊：Clarify -> Rewrite or Generate
        workflow.add_conditional_edges(
            "clarify",
            self.decide_to_rewrite,
            {
                "rewrite": "rewrite",
                "generate": "generate"
            }
        )

        # 條件邊：Generate 後決定是否調用工具
        workflow.add_conditional_edges(
            "generate",
            self.should_continue,
            {
                "tools": "tools",
                "optimize": "optimize_response"
            }
        )

        # 優化完成後結束
        workflow.add_edge("optimize_response", END)

        # 工具執行完 -> 增加計數 -> 回到 generate
        workflow.add_edge("tools", "increment_count")
        workflow.add_edge("increment_count", "generate")

        checkpointer = MemorySaver()
        return workflow.compile(checkpointer=checkpointer)