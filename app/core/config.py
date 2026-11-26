from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings validated via Pydantic.
    Reads values from environment variables or a local .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database
    DATABASE_URL: str

    # Security / Auth
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Gemini
    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    LLM_MODEL: str = "gemini-2.5-flash"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"


# Singleton instance used throughout the application
settings = Settings()
