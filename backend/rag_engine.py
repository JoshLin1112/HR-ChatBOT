import pandas as pd
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import SentenceTransformer
from langchain_ollama import OllamaLLM, ChatOllama
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.prompts import ChatPromptTemplate
from .config import settings
from .tools import calculate_vacation_pay, calculate_unused_overtime_pay
import logging

logger = logging.getLogger(__name__)

class RAGComponents:
    def __init__(self):
        logger.info("Initializing RAG system components...")
        self.documents = []
        self.vectorstore = None
        self.base_retriever = None
        self.reranking_retriever = None
        self.llm_rewriter = None
        self.llm_generator = None
        self.tools = [calculate_vacation_pay, calculate_unused_overtime_pay]
        
        self._load_data()
        self._setup_vectorstore()
        self._setup_reranker()
        self._setup_llms()
        
    
    def _load_data(self):
        """載入並處理資料"""
        try:
            data_path = settings.get_absolute_data_path()
            logger.info(f"Loading data from: {data_path}")
            data = pd.read_csv(data_path, usecols=['question', 'answer', 'category'])
            
            self.documents = []
            for _, row in data.iterrows():
                if not isinstance(row["question"], str):
                    continue
                self.documents.append(
                    Document(
                        page_content=f"問題: {row['question']}",
                        metadata={
                            "answer": row["answer"],
                            "category": row.get("category", "other")
                        }
                    )
                )
            
            logger.info(f"Knowledge base loaded with {len(self.documents)} records")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            # Raise or handle error appropriately
    
    def _setup_vectorstore(self):
        """建立向量資料庫"""
        logger.info("Building vector store...")
        embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        self.vectorstore = FAISS.from_documents(self.documents, embeddings)
        self.base_retriever = self.vectorstore.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={
                "k": settings.TOP_K_RETRIEVAL,
                "score_threshold": settings.SIMILARITY_THRESHOLD, 
            }
        )
        logger.info("Vector store built successfully")
    
    def _setup_reranker(self):
        """設定 Reranker"""
        logger.info("Setting up Reranker...")
        reranker_model = HuggingFaceCrossEncoder(
            model_name=settings.RERANKER_MODEL
        )
        rerank_compressor = CrossEncoderReranker(
            model=reranker_model, 
            top_n=settings.TOP_N_RERANK
        )
        self.reranking_retriever = ContextualCompressionRetriever(
            base_compressor=rerank_compressor,
            base_retriever=self.base_retriever
        )
        logger.info("Reranker setup complete")
    def _setup_llms(self):
        """設定 LLM"""
        logger.info("Setting up LLMs...")
        
        self.llm_rewriter = OllamaLLM(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=settings.REWRITER_TEMPERATURE
        )
        
        self.llm_generator = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=settings.GENERATOR_TEMPERATURE
        ).bind_tools(self.tools)
        
        logger.info("LLMs setup complete")
        logger.info("RAG system components initialization complete")
        
    def search(self, query: str, category: str = None) -> List[Document]:
        """
        執行初步檢索 (Vector Search)
        """
        logger.info(f"Initial search: {query} (Category: {category})")
        
        if category and category != "other":
            logger.debug(f"Applying filter: category='{category}'")
            docs = self.vectorstore.similarity_search(
                query, 
                k=settings.TOP_K_RETRIEVAL,
                filter={"category": category}
            )
        else:
            docs = self.base_retriever.invoke(query)
        
        logger.info(f"Found {len(docs)} documents")
        # 打印文件內容
        for i, doc in enumerate(docs):
            logger.debug(f"Doc {i}: {doc.page_content}")
        return docs

    def rerank(self, documents: List[Document], query: str) -> List[Document]:
        """
        執行重排序 (Rerank)
        """
        if not documents:
            return []
            
        logger.info(f"Reranking {len(documents)} documents...")
        # CrossEncoderReranker expects (document, score) or similar but the compressor takes docs and query
        # compress_documents returns Sequence[Document]
        reranked_docs = self.reranking_retriever.base_compressor.compress_documents(documents, query)
        
        logger.info(f"Retained {len(reranked_docs)} documents after reranking")
        for i, doc in enumerate(reranked_docs):
            logger.debug(f"Reranked Doc {i}: {doc.page_content}")
        return reranked_docs

    def retrieve(self, query: str, category: str = None) -> List[Document]:
        """
        執行完整檢索與 Rerank (Backward Compatibility)
        """
        docs = self.search(query, category)
        return self.rerank(docs, query)
    

