import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from google import genai
from google.genai import errors, types
from langchain_core.documents import Document

from app.config import get_settings
from app.graph.graph_query import graph_query
from app.rag.vector_store import vector_store
from app.db.session import pg_pool
from app.db.crud.cache_registry import get_active_cache, register_cache

logger = logging.getLogger(__name__)
settings = get_settings()

HIGH_CONFIDENCE_THRESHOLD = 0.75
MEDIUM_CONFIDENCE_THRESHOLD = 0.50

class CorporateHighlightItem(BaseModel):
    symbol: str = Field(description="The uppercase stock ticker symbol, matching the query.")
    highlight: str = Field(description="3-5 sentences factual summary of management guidance, operating margin performance, and risk factors retrieved ONLY from the provided excerpts.")

class BatchCorporateHighlightsSchema(BaseModel):
    highlights: List[CorporateHighlightItem] = Field(description="List of corporate highlights summaries, one for each requested stock symbol.")

QA_SYSTEM_PROMPT = """
You are a financial analyst assistant for NiftyMind.
Answer ONLY from provided context, never use outside knowledge,
cite company and quarter for numbers, keep answers 3-5 sentences, and use factual language.
""".strip()


class CorrectiveRAGService:
    def __init__(self):
        self._client = genai.Client(api_key=settings.gemini_api_key)

    async def _get_or_create_context_cache(self, static_context: str, system_instruction: str) -> Optional[str]:
        if not pg_pool:
            return None
            
        try:
            # 1. Count tokens to check threshold (minimum 32k for caching)
            token_count_resp = await self._client.aio.models.count_tokens(
                model=settings.model_name,
                contents=static_context
            )
            num_tokens = token_count_resp.total_tokens
            if num_tokens < 32768:
                logger.info(f"[CorrectiveRAG] Context tokens ({num_tokens}) below threshold (32768). Skipping cache.")
                return None
                
            # 2. Compute hash of the static context
            context_hash = hashlib.md5(static_context.encode("utf-8")).hexdigest()
            
            async with pg_pool.acquire() as conn:
                # 3. Check registry for active cache
                active = await get_active_cache(conn, context_hash)
                if active:
                    return active["google_cache_name"]
                
                # 4. Create new cache on Google GenAI
                logger.info(f"[CorrectiveRAG] Creating Google GenAI Context Cache for {num_tokens} tokens...")
                cache = await self._client.aio.caches.create(
                    model=settings.model_name,
                    config=types.CreateCachedContentConfig(
                        display_name=f"rag_static_{context_hash[:8]}",
                        system_instruction=system_instruction,
                        contents=[static_context],
                        ttl="1800s",  # 30 minutes cache duration
                    )
                )
                
                # Convert expire_time from string format or datetime object
                expires_dt = None
                if hasattr(cache, "expire_time") and cache.expire_time:
                    expire_time = cache.expire_time
                    if isinstance(expire_time, str):
                        if expire_time.endswith("Z"):
                            expire_time = expire_time[:-1] + "+00:00"
                        expires_dt = datetime.fromisoformat(expire_time)
                    elif isinstance(expire_time, datetime):
                        expires_dt = expire_time
                if not expires_dt:
                    from datetime import timedelta
                    expires_dt = datetime.now(timezone.utc) + timedelta(minutes=30)
                    
                # 5. Register in DB
                await register_cache(conn, context_hash, cache.name, expires_dt)
                return cache.name
        except Exception as exc:
            logger.warning(f"[CorrectiveRAG] Failed to manage context cache: {exc}. Falling back to normal flow.")
            return None

    async def ask(
        self,
        question: str,
        top_k: int = 4,
        confidence_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
        filter_company: Optional[str] = None,
        namespace: str = "earnings",
    ) -> dict:
        try:
            vector_results = self._retrieve_from_vector(
                question,
                top_k,
                filter_company,
                namespace,
            )

            confidence = self._compute_confidence(vector_results)
            mode = self._determine_mode(confidence, confidence_threshold)
            graph_results = []

            from app.graph.neo4j_client import neo4j_client
            if neo4j_client.is_connected() and mode in ("hybrid", "graph_fallback"):
                graph_results = self._retrieve_from_graph(question)

            context = self._build_context(vector_results, graph_results, mode)
            answer, is_fallback = await self._generate_answer(question, context)

            sources = [
                {
                    "company": doc.metadata.get("company", "Unknown"),
                    "quarter": doc.metadata.get("quarter", "Unknown"),
                    "source": doc.metadata.get("source", "Unknown"),
                    "chunk_id": doc.metadata.get("chunk_id", "Unknown"),
                    "score": doc.metadata.get("score", 0.0),
                }
                for doc in vector_results
            ]

            vector_chunks = [
                {
                    "content": doc.page_content,
                    "company": doc.metadata.get("company", "Unknown"),
                    "quarter": doc.metadata.get("quarter", "Unknown"),
                    "source": doc.metadata.get("source", "Unknown"),
                    "chunk_id": doc.metadata.get("chunk_id", "Unknown"),
                    "score": doc.metadata.get("score", 0.0),
                }
                for doc in vector_results
            ]

            return {
                "question": question,
                "answer": answer,
                "confidence": confidence,
                "retrieval_method": mode,
                "sources": sources,
                "graph_facts": graph_results,
                "vector_chunks": vector_chunks,
                "graph_results_count": len(graph_results),
                "is_fallback": is_fallback,
                "generated_by": settings.model_name,
            }

        except Exception as exc:
            logger.error(
                "Corrective RAG ask failed",
                extra={
                    "question_preview": question[:80],
                    "top_k": top_k,
                    "filter_company": filter_company,
                    "error": str(exc),
                },
                exc_info=True,
            )
            return {
                "question": question,
                "answer": "Unable to generate an answer at this time.",
                "confidence": 0.0,
                "retrieval_method": "error",
                "sources": [],
                "graph_facts": [],
                "vector_chunks": [],
                "graph_results_count": 0,
                "is_fallback": True,
                "generated_by": settings.model_name,
            }

    def _retrieve_from_vector(
        self,
        question: str,
        top_k: int,
        filter_company: Optional[str],
        namespace: str = "earnings",
    ) -> list[Document]:
        try:
            return vector_store.query(
                question=question,
                top_k=top_k,
                filter_company=filter_company,
                namespace=namespace,
            )
        except Exception as exc:
            logger.error(
                "Vector retrieval failed",
                extra={
                    "question_preview": question[:80],
                    "top_k": top_k,
                    "filter_company": filter_company,
                    "error": str(exc),
                },
                exc_info=True,
            )
            return []

    def _compute_confidence(self, results: list[Document]) -> float:
        if not results:
            return 0.0

        scores = [
            float(doc.metadata.get("score", 0.0))
            for doc in results
            if isinstance(doc.metadata.get("score"), (int, float))
        ]

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    def _determine_mode(self, confidence: float, threshold: float) -> str:
        if confidence >= threshold:
            return "vector_only"
        if confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
            return "hybrid"
        return "graph_fallback"

    def _retrieve_from_graph(self, question: str) -> list[dict]:
        try:
            return graph_query.natural_language_to_graph(question)
        except Exception as exc:
            logger.error(
                "Graph retrieval failed",
                extra={"question_preview": question[:80], "error": str(exc)},
                exc_info=True,
            )
            return []

    def _build_context(
        self,
        vector_results: list[Document],
        graph_results: list[dict],
        mode: str,
    ) -> str:
        parts = []

        if vector_results and mode != "graph_fallback":
            parts.append("=== TRANSCRIPT EXCERPTS ===")
            for doc in vector_results:
                company = doc.metadata.get("company", "Unknown")
                quarter = doc.metadata.get("quarter", "Unknown")
                score = doc.metadata.get("score", 0.0)
                parts.append(
                    f"Company: {company} | Quarter: {quarter} | Score: {score}"
                )
                parts.append(doc.page_content.strip())

        if graph_results:
            parts.append("=== STRUCTURED FINANCIAL DATA ===")
            parts.append(json.dumps(graph_results, indent=2))

        if not parts:
            return "No relevant context found."

        return "\n\n".join(parts)

    async def _generate_answer(self, question: str, context: str) -> tuple[str, bool]:
        try:
            # Check for active static context cache
            cache_name = await self._get_or_create_context_cache(context, QA_SYSTEM_PROMPT)
            
            if cache_name:
                logger.info(f"[CorrectiveRAG] Querying with context cache: {cache_name}")
                response = await self._client.aio.models.generate_content(
                    model=settings.model_name,
                    contents=f"QUESTION:\n{question}",
                    config=types.GenerateContentConfig(
                        cached_content=cache_name,
                        max_output_tokens=512,
                        temperature=0.1,
                    ),
                )
            else:
                prompt = (
                    f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"
                )
                response = await self._client.aio.models.generate_content(
                    model=settings.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=QA_SYSTEM_PROMPT,
                        max_output_tokens=512,
                        temperature=0.1,
                    ),
                )

            token_usage = getattr(response, "token_usage", None)
            logger.info(
                "Generated corrective RAG answer",
                extra={
                    "model": settings.model_name,
                    "question_preview": question[:80],
                    "token_usage": token_usage,
                },
            )

            return response.text.strip(), False

        except errors.ClientError as exc:
            logger.warning(
                "Gemini client error during corrective RAG generation",
                extra={"question_preview": question[:80], "error": str(exc)},
                exc_info=True,
            )
            return (
                "I could not generate an answer from the language model at this time.",
                True,
            )

        except Exception as exc:
            logger.error(
                "Unexpected error during corrective RAG generation",
                extra={"question_preview": question[:80], "error": str(exc)},
                exc_info=True,
            )
            return (
                "I could not generate an answer due to an internal error.",
                True,
            )

    async def ask_batch(
        self,
        symbols: List[str],
        top_k: int = 3,
        confidence_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
        namespace: str = "earnings",
    ) -> Dict[str, str]:
        """
        Runs batched corrective RAG for multiple stock symbols:
        1. Embeds all symbol questions in a single Google Embeddings API call.
        2. Retrieves vector store and graph database context for each symbol.
        3. Invokes a single batched Gemini call with BatchCorporateHighlightsSchema to summarize guidance/margins/risks.
        """
        if not symbols:
            return {}

        logger.info(f"[RAGBatch] Gathers corporate insights for symbols: {symbols}")

        from app.rag.embeddings import get_query_embeddings
        from app.graph.neo4j_client import neo4j_client

        # Initialize vector store lazy connection
        vector_store._initialize()

        # 1. Prepare questions
        questions = [
            f"What is the management guidance, operating margin performance, and main risk factors reported for {symbol}?"
            for symbol in symbols
        ]

        # 2. Embed all query questions sequentially using embed_query
        try:
            embedder = get_query_embeddings()
            query_embeddings = []
            for q in questions:
                query_embeddings.append(embedder.embed_query(q))
        except Exception as exc:
            logger.exception(f"[RAGBatch] Failed to embed questions: {exc}")
            return {sym: "Failed to retrieve corporate transcript insights due to an embeddings call error." for sym in symbols}

        # 3. Retrieve context fragments for each symbol using its embedding
        contexts_by_symbol = {}
        for idx, symbol in enumerate(symbols):
            sym = symbol.upper()
            q_emb = query_embeddings[idx]
            question = questions[idx]

            try:
                # Query vector database directly using the embedding
                fetch_k = top_k * 4
                query_response = vector_store._index.query(
                    vector=q_emb,
                    top_k=fetch_k,
                    namespace=namespace,
                    include_metadata=True,
                )

                # Convert to Documents
                vector_results = []
                for match in query_response.get("matches", []):
                    metadata = dict(match.get("metadata", {}))
                    content = metadata.pop("text", "")
                    vector_results.append(Document(
                        page_content=content,
                        metadata={
                            **metadata,
                            "score": round(match.get("score", 0.0), 4),
                        },
                    ))

                # Post-filter by company
                vector_results = [
                    d for d in vector_results
                    if sym.lower() in d.metadata.get("company", "").lower()
                ][:top_k]

                # Compute confidence & determine mode
                confidence = self._compute_confidence(vector_results)
                mode = self._determine_mode(confidence, confidence_threshold)

                # Neo4j fallback query (only if connected)
                graph_results = []
                if neo4j_client.is_connected() and mode in ("hybrid", "graph_fallback"):
                    graph_results = self._retrieve_from_graph(question)

                # Build context block
                contexts_by_symbol[sym] = self._build_context(vector_results, graph_results, mode)
            except Exception as e:
                logger.error(f"[RAGBatch] Failed to retrieve context for {sym}: {e}")
                contexts_by_symbol[sym] = "No transcript guidance available."

        # 4. Synthesize all contexts into a single batched prompt
        formatted_contexts = []
        for sym in symbols:
            sym_upper = sym.upper()
            ctx = contexts_by_symbol.get(sym_upper, "No relevant context found.")
            formatted_contexts.append(
                f"=== CONTEXT FOR {sym_upper} ===\n"
                f"{ctx}\n"
            )
        contexts_prompt = "\n\n".join(formatted_contexts)

        try:
            # Check for active static context cache
            cache_name = await self._get_or_create_context_cache(contexts_prompt, QA_SYSTEM_PROMPT)
            
            if cache_name:
                logger.info(f"[RAGBatch] Querying with context cache: {cache_name}")
                prompt = f"""
                You are a financial news and corporate highlights analyst. Given the cached transcript/data contexts, extract the corporate transcript insights (management guidance, operating margin performance, and main risk factors) for the following stock symbols.
                
                Generate highlights for each symbol matching the requested JSON schema. Make sure you return an entry for every input symbol in: {symbols}.
                """
                response = await self._client.aio.models.generate_content(
                    model=settings.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        cached_content=cache_name,
                        response_mime_type="application/json",
                        response_schema=BatchCorporateHighlightsSchema,
                        max_output_tokens=1024,
                        temperature=0.1,  # strict & fast
                    ),
                )
            else:
                prompt = f"""
                You are a financial news and corporate highlights analyst. Given the transcript/data context for the following stock symbols, extract the corporate transcript insights (management guidance, operating margin performance, and main risk factors) for each symbol.
                
                CONTEXTS FOR ALL SYMBOLS:
                {contexts_prompt}
                
                Generate highlights for each symbol matching the requested JSON schema. Make sure you return an entry for every input symbol in: {symbols}.
                """
                logger.info(f"[RAGBatch] Calling Gemini for RAG batch content generation on {len(symbols)} symbols")
                response = await self._client.aio.models.generate_content(
                    model=settings.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=QA_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        response_schema=BatchCorporateHighlightsSchema,
                        max_output_tokens=1024,
                        temperature=0.1,  # strict & fast
                    ),
                )
            result = json.loads(response.text)
            highlights_ai = result.get("highlights", [])

            # Map results to symbols
            highlights_map = {}
            for item in highlights_ai:
                highlights_map[item["symbol"].upper()] = item["highlight"]

            # Ensure every requested symbol has an answer
            final_highlights = {}
            for sym in symbols:
                sym_upper = sym.upper()
                final_highlights[sym_upper] = highlights_map.get(
                    sym_upper, 
                    "No transcript insights available for this stock currently."
                )
            return final_highlights

        except Exception as exc:
            logger.exception("[RAGBatch] Failed batch corporate highlights generation")
            return {sym: "I could not generate transcript observations due to an internal error." for sym in symbols}


# Module singleton
corrective_rag = CorrectiveRAGService()
