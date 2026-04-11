"""Configuration settings for Schedula FastAPI backend."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # FastAPI
    app_name: str = "Schedula Schedule Solver"
    debug: bool = False
    cors_origins: list[str] = Field(default=["*"])
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")

    # MongoDB
    mongodb_uri: str = Field(
        default="mongodb+srv://user:password@cluster.mongodb.net",
        description="MongoDB Atlas connection URI",
    )
    mongodb_db_name: str = Field(default="schedula")

    # OR-Tools Solver
    solver_time_limit_seconds: int = Field(
        default=55,
        description="55s budget — 5s headroom for response serialization",
    )
    solver_num_workers: int = Field(
        default=8,
        description="CP-SAT parallel portfolio workers (LNS + SAT + LP + heuristics)",
    )

    # Fallback soft constraint weights (overridden by constraints collection in DB)
    soft_weight_break_window: int = Field(default=100)
    soft_weight_consecutive_slots: int = Field(default=80)
    soft_weight_session_spread: int = Field(default=60)
    soft_weight_campus_clustering: int = Field(default=40)

    # Development mode
    # When dev_mode=true, requests with Authorization: Bearer <dev_api_token>
    # bypass any future auth guards. NEVER enable in production.
    dev_mode: bool = Field(default=False)
    dev_api_token: str = Field(default="")


settings = Settings()
