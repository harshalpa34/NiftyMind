from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration (with safe defaults)
    api_title: str = Field(default="NiftyMind GenAI API")
    api_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # CORS Configuration
    cors_origins: list = Field(default=["http://localhost:3000", "http://localhost:3001"])
    
    # SENSITIVE: AI/ML Configuration (REQUIRED from .env)
    openai_api_key: str = Field(..., description="Must be set in .env file")
    model_name: str = Field(default="gpt-4")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
