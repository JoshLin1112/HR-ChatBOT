import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Settings
    APP_TITLE: str = "請假差勤問答系統"
    APP_DESCRIPTION: str = "基於 LangGraph 的 RAG 系統"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "ministral-3:4b"
    REWRITER_TEMPERATURE: float = 0.3
    GENERATOR_TEMPERATURE: float = 0.4
    
    # Retrieval Settings
    EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-0.6B"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    TOP_K_RETRIEVAL: int = 8
    TOP_N_RERANK: int = 2
    SIMILARITY_THRESHOLD: float = 0.4
    
    # Data Settings
    DATA_PATH: str = r"backend\data\QA617.csv"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_absolute_data_path(self) -> str:
        """Returns the absolute path to the data file."""
        if os.path.isabs(self.DATA_PATH):
            return self.DATA_PATH
        # Access the project root (assuming we run from root)
        return os.path.abspath(self.DATA_PATH)

settings = Settings()
