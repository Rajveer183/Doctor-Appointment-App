from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./appointments.db"
    nvidia_api_key: str = ""
    nvidia_chat_model: str = "meta/llama-3.1-70b-instruct"
    nvidia_embed_model: str = "nvidia/nv-embedqa-e5-v5"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    chroma_persist_dir: str = "./chroma_data"
    embedding_similarity_threshold: float = 0.72
    fuzzy_match_threshold: int = 85
    cancellation_window_minutes: int = 60


settings = Settings()
