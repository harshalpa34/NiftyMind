from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    api_title: str = "NiftyMind GenAI API"
    api_version: str = "1.0.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS Configuration
    cors_origins: list = ["http://localhost:3000", "http://localhost:3001"]
    
    # Optional: AI/ML Configuration
    openai_api_key: str = ""
    model_name: str = "gpt-4"
    temperature: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
