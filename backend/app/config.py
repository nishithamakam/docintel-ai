from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # API credentials
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"

    # Model names
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-5.2"

    # Storage paths
    data_dir: str = "./data"

    # RAG settings
    chunk_size: int = 800
    chunk_overlap: int = 100
    top_k: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a single settings instance to use across the app
settings = Settings()

# Set up data directories
DATA_DIR = Path(settings.data_dir)
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "uploads").mkdir(exist_ok=True)
(DATA_DIR / "faiss_index").mkdir(exist_ok=True)
