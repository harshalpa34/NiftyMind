from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import get_settings


def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """
    Get embeddings model for document embedding (ingestion).
    
    Returns:
        GoogleGenerativeAIEmbeddings instance configured for document task
    """
    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2",
        google_api_key=settings.gemini_api_key,
        task_type="retrieval_document",
        output_dimensionality=settings.embedding_dimension,
    )


def get_query_embeddings() -> GoogleGenerativeAIEmbeddings:
    """
    Get embeddings model for query embedding (search).
    
    Returns:
        GoogleGenerativeAIEmbeddings instance configured for query task
    """
    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2",
        google_api_key=settings.gemini_api_key,
        task_type="retrieval_query",
        output_dimensionality=settings.embedding_dimension,
    )
