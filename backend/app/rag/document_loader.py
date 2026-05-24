import logging
import glob
import os
from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


logger = logging.getLogger(__name__)

# Module-level text splitter
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " ", ""]
)


def load_transcripts(directory: str = "data/transcripts") -> list[Document]:
    """
    Load all transcript files from the specified directory.
    
    Args:
        directory: Path to directory containing .txt transcript files
        
    Returns:
        List of langchain Document objects with metadata
    """
    documents = []
    
    # Glob all .txt files in directory
    pattern = os.path.join(directory, "*.txt")
    transcript_files = glob.glob(pattern)
    
    if not transcript_files:
        logger.warning(f"No transcript files found in {directory}")
        return documents
    
    for file_path in transcript_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            filename = os.path.basename(file_path)
            metadata = _extract_metadata(text, filename)
            
            doc = Document(page_content=text, metadata=metadata)
            documents.append(doc)
            
            logger.info(
                f"Loaded transcript: {metadata.get('company', 'Unknown')} "
                f"({metadata.get('quarter', 'Unknown')})",
                extra={
                    "file_name": filename,
                    "company": metadata.get("company"),
                    "quarter": metadata.get("quarter"),
                    "chars": len(text)
                }
            )
        except Exception as e:
            logger.error(f"Failed to load transcript {file_path}: {e}")
            continue
    
    logger.info(f"Total documents loaded: {len(documents)}")
    return documents


def chunk_documents(documents: list[Document]) -> list[Document]:
    """
    Split documents into chunks with metadata.
    
    Args:
        documents: List of Document objects
        
    Returns:
        List of chunked Document objects with chunk metadata
    """
    all_chunks = []
    
    for doc in documents:
        chunks = _splitter.split_documents([doc])
        
        # Add chunk metadata
        total_chunks = len(chunks)
        for chunk_index, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = chunk_index
            chunk.metadata["total_chunks"] = total_chunks
            chunk.metadata["chunk_id"] = f"{chunk.metadata.get('source', 'unknown')}_{chunk_index}"
            all_chunks.append(chunk)
    
    avg_chunk_size = (
        sum(len(chunk.page_content) for chunk in all_chunks) / len(all_chunks)
        if all_chunks else 0
    )
    
    logger.info(
        f"Documents chunked",
        extra={
            "input_docs": len(documents),
            "output_chunks": len(all_chunks),
            "avg_chunk_size": round(avg_chunk_size, 1)
        }
    )
    
    return all_chunks


def _extract_metadata(text: str, filename: str) -> dict:
    """
    Extract metadata from transcript text.
    
    Args:
        text: Full transcript text
        filename: Name of the transcript file
        
    Returns:
        Dictionary with extracted metadata
    """
    metadata = {
        "source": filename,
        "company": "Unknown",
        "quarter": "Unknown",
        "date": "Unknown",
        "doc_type": "earnings_transcript"
    }
    
    # Parse first 10 lines for metadata
    lines = text.split("\n")[:10]
    
    for line in lines:
        line_lower = line.lower()
        
        if "company:" in line_lower:
            metadata["company"] = line.split(":", 1)[-1].strip()
        elif "quarter:" in line_lower:
            metadata["quarter"] = line.split(":", 1)[-1].strip()
        elif "date:" in line_lower:
            metadata["date"] = line.split(":", 1)[-1].strip()
    
    return metadata
