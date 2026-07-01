from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )
    
    # API Configuration (with safe defaults)
    api_title: str = Field(default="NiftyMind GenAI API")
    api_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Authentication Configuration
    secret_key: str = Field(
        default="changeme-use-32-chars-minimum-in-production"
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    
    # CORS Configuration
    cors_origins: list = Field(default=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"])
    
    # SENSITIVE: AI/ML Configuration (REQUIRED from .env)
    openai_api_key: str = Field(..., description="Must be set in .env file")
    gemini_api_key: str = Field(default="", description="Gemini API key")
    model_name: str = Field(default="gemini-2.5-flash", description="LLM model to use (e.g., gpt-4, gemini-2.5-flash)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    embedding_dimension: int = Field(default=3072, description="Embedding vector size; must match Pinecone index dimension")
    pinecone_api_key: str = Field(default="", description="Pinecone API key")
    pinecone_index_name: str = Field(default="", description="Pinecone index name")
    
    # Claude/Anthropic Configuration (for NLP analysis)
    anthropic_api_key: str = Field(default="")
    
    # Database Configuration
    database_url: str = Field(default="", description="PostgreSQL async URL: postgresql+asyncpg://user:password@host/dbname")
    db_path: str = Field(default="./data/niftymind.db")
    # Neo4j configuration
    neo4j_uri: str = Field(default="", description="Bolt URI for Neo4j, e.g. bolt://localhost:7687")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="", description="Neo4j password")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value
    
@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
