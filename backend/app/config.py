import os
from pathlib import Path
from pydantic import BaseModel
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None  # python-dotenv is optional


def _load_env_files():
    if load_dotenv is None:
        return
    # Try project root and backend dir; load .env then fallback to .env.example
    cwd = Path(os.getcwd())
    candidates = [
        cwd / ".env",
        cwd / "backend" / ".env",
        cwd / ".env.example",
        cwd / "backend" / ".env.example",
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(dotenv_path=str(p), override=False)


_load_env_files()


class Settings(BaseModel):
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    # Main classification model - using available model
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Resolve storage_dir to repo root/storage by default (stable even if app-dir changes)
    storage_dir: str = os.getenv(
        "STORAGE_DIR",
        str(Path(__file__).resolve().parents[2] / "storage"),
    )
    nacre_dict_path: str = os.getenv(
        "NACRE_DICT_PATH", os.path.join(os.getcwd(), "storage", "data", "nacre_dictionary.csv")
    )
    max_candidates: int = int(os.getenv("MAX_CANDIDATES", "25"))
    preview_rows: int = int(os.getenv("PREVIEW_ROWS", "20"))
    # Sophie (orchestrator) settings
    sophie_enabled: bool = os.getenv("SOPHIE_ENABLED", "true").lower() in {"1","true","yes"}
    # Sophie orchestrator model - using available model
    sophie_model: str = os.getenv("SOPHIE_MODEL", "gpt-4o-mini")
    # Sophie advanced settings for GPT-5
    sophie_max_context: int = int(os.getenv("SOPHIE_MAX_CONTEXT", "16000"))
    sophie_temperature: float = float(os.getenv("SOPHIE_TEMPERATURE", "0.2"))
    sophie_max_tokens: int = int(os.getenv("SOPHIE_MAX_TOKENS", "1000"))
    # Embeddings model - GPT-5 compatible
    embeddings_model: str = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-large")
    # Training and learning model - using available model
    training_model: str = os.getenv("TRAINING_MODEL", "gpt-4o-mini")
    # Analysis and explanation model - using available model
    analysis_model: str = os.getenv("ANALYSIS_MODEL", "gpt-4o-mini")
    batch_size: int = int(os.getenv("BATCH_SIZE", "10"))
    # Enhanced AI settings for GPT-5
    enable_advanced_reasoning: bool = os.getenv("ENABLE_ADVANCED_REASONING", "true").lower() in {"1","true","yes"}
    enable_multi_step_analysis: bool = os.getenv("ENABLE_MULTI_STEP_ANALYSIS", "true").lower() in {"1","true","yes"}
    enable_context_enhancement: bool = os.getenv("ENABLE_CONTEXT_ENHANCEMENT", "true").lower() in {"1","true","yes"}
    # Logging settings
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", "nacre.log")


settings = Settings()

# GPT-5 Model Configuration
GPT5_MODELS = {
    "classification": settings.openai_model,
    "orchestrator": settings.sophie_model,
    "communication": os.getenv("COMMUNICATION_MODEL", "gpt-4o-mini"),  # GPT-5 mini pour communication naturelle
    "embeddings": settings.embeddings_model,
    "training": settings.training_model,
    "analysis": settings.analysis_model,
}

# GPT-5 Enhanced Parameters
GPT5_PARAMS = {
    "classification": {
        "temperature": 0.1,
        "max_tokens": 2000,
        "top_p": 0.95,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    },
    "orchestrator": {
        "temperature": settings.sophie_temperature,
        "max_tokens": settings.sophie_max_tokens,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1,
    },
    "training": {
        "temperature": 0.2,
        "max_tokens": 1500,
        "top_p": 0.95,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
    },
    "analysis": {
        "temperature": 0.3,
        "max_tokens": 2000,
        "top_p": 0.9,
        "frequency_penalty": 0.1,
        "presence_penalty": 0.1,
    },
    "communication": {
        "temperature": 0.8,  # Plus créatif pour communication naturelle
        "max_tokens": 800,
        "top_p": 0.9,
        "frequency_penalty": 0.2,  # Éviter répétitions
        "presence_penalty": 0.3,   # Encourager diversité
    },
}
