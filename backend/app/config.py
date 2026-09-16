from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./appointments.db"
    nvidia_api_key: str = ""
    nvidia_chat_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_embed_model: str = "nvidia/nemotron-3-embed-1b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    chroma_persist_dir: str = "./chroma_data"
    # Empirically calibrated against nvidia/nemotron-3-embed-1b, not guessed: real paraphrases
    # ("my back has been hurting for days" -> "back pain") scored ~0.45-0.65 cosine similarity,
    # near-exact repeats scored ~0.85-0.95, and genuinely unrelated text scored ~0.07-0.15.
    # 0.45 sits just above the unrelated-text ceiling, so it catches paraphrases without
    # accepting noise. This is model-specific — recalibrate if the embed model changes.
    embedding_similarity_threshold: float = 0.45
    fuzzy_match_threshold: int = 85
    cancellation_window_minutes: int = 60


settings = Settings()
