from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./appointments.db"
    # Comma-separated list of browser origins allowed to call this API.
    # Set to the deployed frontend URL on Cloud Run (see commands.md step 8).
    frontend_origin: str = "http://localhost:5173"
    nvidia_api_key: str = ""
    nvidia_chat_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_embed_model: str = "nvidia/nemotron-3-embed-1b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    chroma_persist_dir: str = "./chroma_data"
    # Empirically calibrated against nvidia/nemotron-3-embed-1b, not guessed: real paraphrases
    # scored ~0.39-0.65 cosine similarity ("my little one has been running a temperature
    # since last night" -> "child has a fever" scored 0.39; "my back has been hurting for
    # days" -> "back pain" scored 0.62), near-exact repeats scored ~0.85-0.95, and genuinely
    # unrelated text scored ~0.07-0.15. 0.35 sits well above the unrelated-text ceiling while
    # covering the weaker end of real paraphrases seen so far. Model-specific — recalibrate
    # if the embed model changes.
    embedding_similarity_threshold: float = 0.35
    fuzzy_match_threshold: int = 85
    cancellation_window_minutes: int = 60

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origin.split(",") if o.strip()]


settings = Settings()
