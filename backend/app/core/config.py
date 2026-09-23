"""
Application configuration using Pydantic Settings.
Loads from environment variables with .env file support.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Use .env file for local development.
    """

    # Application
    APP_NAME: str = "Cognitive Accessibility Simplifier"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    MAX_FILENAME_LENGTH: int = 255
    UPLOAD_DIRECTORY: str = "uploads"
    GENERATED_DIRECTORY: str = "generated"

    # Document Processing
    MAX_DOCUMENT_LENGTH: int = 100000  # characters
    CHUNK_SIZE: int = 2000  # for large documents

    # Simplification
    MAX_SIMPLIFICATION_ATTEMPTS: int = 2
    TARGET_GRADE_LEVEL: int = 5

    # LLM Configuration
    LLM_PROVIDER: str = "auto"  # openai, gemini, groq, openrouter, mock, etc.
    LLM_API_KEY: str = ""  # For backward compatibility
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_TEMPERATURE: float = 0.3  # Lower = more consistent/factual
    LLM_MAX_TOKENS: int = 2000
    
    # Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-pro"
    
    # Groq Configuration
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-oss-20b"

    # Translation Configuration
    TRANSLATION_PROVIDER: str = "nllb"  # nllb, indicTrans, google, etc.
    TRANSLATION_API_KEY: str = ""

    # TTS Configuration
    TTS_PROVIDER: str = "google"  # google, azure, coqui, etc.
    TTS_API_KEY: str = ""

    # Database Configuration (MILESTONE 11)
    DATABASE_URL: str = "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/cognitive_accessibility_db"
    USE_DATABASE: bool = True

    # URL Fetching (MILESTONE 2)
    URL_FETCH_TIMEOUT: int = 10  # seconds
    URL_FETCH_MAX_SIZE: int = 10485760  # 10MB
    DOCUMENT_ID_PREFIX: str = "doc"

    # OCR Configuration (MILESTONE 3)
    TESSERACT_PATH: str = "tesseract"  # Path to Tesseract executable
    OCR_CONFIDENCE_THRESHOLD: float = 0.5
    MAX_OCR_PAGES: int = 50  # Max pages to OCR in one document
    OCR_TIMEOUT: int = 300  # Seconds per page

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Initialize settings
settings = Settings()
