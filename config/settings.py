from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI - LATER
    openai_api_key: str = Field("placeholder")
    openai_model_agent1: str = Field("gpt-4o")
    openai_model_agent3: str = Field("gpt-4o")

    # Groq 
    groq_api_key: str = Field("placeholder")
    groq_model_agent1: str = Field("openai/gpt-oss-120b")
    groq_model_agent3: str = Field("openai/gpt-oss-120b")

    # Ollama (for Agent 2 - runs locally)
    ollama_base_url: str = Field("http://localhost:11434")
    ollama_model_agent2: str = Field("deepseek-coder:33b")

    # ChromaDB
    chroma_db_path: str = Field("./data/chroma_db")
    chroma_collection_name: str = Field("repo_index")

    # RAG
    rag_chunk_size: int = Field(512)
    rag_chunk_overlap: int = Field(64)
    rag_top_k: int = Field(5)

    # Agent 2
    max_repair_iterations: int = Field(3)

    # Evaluation
    evaluation_timeout_seconds: int = Field(90)

    # API
    api_host: str = Field("0.0.0.0")
    api_port: int = Field(8000)


settings = Settings()