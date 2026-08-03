import React, { useState, useEffect } from "react";
import { api, ApiError } from "../lib/api";
import Card from "../components/Card";
import { 
  Search, 
  Settings, 
  Upload, 
  CheckCircle, 
  AlertCircle, 
  ChevronDown, 
  ChevronUp, 
  Cpu, 
  Sparkles
} from "lucide-react";

interface Source {
  company: string;
  quarter: string;
  source: string;
  chunk_id: string;
  score: number;
}

interface VectorChunk {
  content: string;
  company: string;
  quarter: string;
  source: string;
  chunk_id: string;
  score: number;
}

interface RAGResponse {
  question: string;
  answer: string;
  confidence: number;
  retrieval_method: string;
  sources: Source[];
  graph_facts: any[];
  vector_chunks: VectorChunk[];
  graph_results_count: number;
  is_fallback: boolean;
  generated_by: string;
}

interface VectorStats {
  status: string;
  backend: string;
  index: string;
  total_vectors: number;
  namespace: string;
  namespace_vectors: number;
  dimension: number;
}

export const RagView: React.FC = () => {
  // Query Form States
  const [question, setQuestion] = useState("");
  const [filterCompany, setFilterCompany] = useState("");
  const [topK, setTopK] = useState(4);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.75);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Lists and Data loaded dynamically
  const [userTickers, setUserTickers] = useState<string[]>([]);
  const [vectorStats, setVectorStats] = useState<VectorStats | null>(null);

  // Execution UI States
  const [loading, setLoading] = useState(false);
  const [loadStep, setLoadStep] = useState(0); // 0: Vector db, 1: Confidence analysis, 2: Graph query, 3: Gemini Synthesis
  const [queryError, setQueryError] = useState<string | null>(null);
  const [ragResult, setRagResult] = useState<RAGResponse | null>(null);

  // Ingestion States
  const [ingestPath, setIngestPath] = useState("data/transcripts");
  const [ingesting, setIngesting] = useState(false);
  const [ingestStatus, setIngestStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Accordion Toggles
  const [sourcesExpanded, setSourcesExpanded] = useState(false);
  const [contextExpanded, setContextExpanded] = useState(false);

  const [presetQuestions, setPresetQuestions] = useState<string[]>([
    "What is the management guidance and margin outlook for TCS?",
    "Summarize operating performance and risk factors for HDFC Bank",
    "Show company metrics, dividends, and competitors",
    "What did TCS say about revenue growth guidance?"
  ]);

  // Fetch unique tickers from user portfolios to pre-populate filters
  const loadPortfolioTickers = async () => {
    try {
      const portfolios = await api.get("/portfolios");
      const allHoldingsData = await Promise.all(
        portfolios.map((p: any) => api.get(`/portfolios/${p.id}`))
      );
      const tickers = new Set<string>();
      allHoldingsData.forEach((res: any) => {
        if (res.holdings) {
          res.holdings.forEach((h: any) => {
            if (h.symbol) tickers.add(h.symbol.toUpperCase());
          });
        }
      });
      setUserTickers(Array.from(tickers).sort());
    } catch (err) {
      console.error("Failed to load user portfolio tickers", err);
    }
  };

  // Fetch Pinecone statistics
  const fetchStats = async () => {
    try {
      const stats = await api.get("/rag/stats");
      setVectorStats(stats);
    } catch (err) {
      console.error("Failed to load vector store stats", err);
    }
  };

  // Fetch dynamic preset RAG questions from backend
  const fetchPresetQuestions = async () => {
    try {
      const res = await api.get("/rag/preset-questions");
      if (res && res.questions) {
        setPresetQuestions(res.questions);
      }
    } catch (err) {
      console.error("Failed to load preset questions", err);
    }
  };

  useEffect(() => {
    loadPortfolioTickers();
    fetchStats();
    fetchPresetQuestions();
  }, []);

  // Multi-step Loading Animation loop
  useEffect(() => {
    let intervalId: any = null;
    if (loading) {
      setLoadStep(0);
      intervalId = setInterval(() => {
        setLoadStep((prev) => (prev < 3 ? prev + 1 : 3));
      }, 1500);
    } else {
      setLoadStep(0);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [loading]);

  const handleQuerySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim().length < 5) {
      setQueryError("Question must be at least 5 characters long.");
      return;
    }

    setQueryError(null);
    setRagResult(null);
    setLoading(true);

    try {
      const payload = {
        question: question.trim(),
        top_k: topK,
        confidence_threshold: confidenceThreshold,
        filter_company: filterCompany || undefined
      };
      
      const response = await api.post("/rag/ask", payload);
      setRagResult(response);
    } catch (err) {
      setQueryError(
        err instanceof ApiError ? err.message : "Failed to run corrective RAG search."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleIngestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIngestStatus(null);
    setIngesting(true);

    try {
      const response = await api.post("/rag/ingest", { directory: ingestPath });
      setIngestStatus({
        type: "success",
        message: response.message || "Transcripts ingested successfully!"
      });
      // Reload stats after ingestion
      fetchStats();
    } catch (err) {
      setIngestStatus({
        type: "error",
        message: err instanceof ApiError ? err.message : "Ingestion failed."
      });
    } finally {
      setIngesting(false);
    }
  };

  const getMethodExplanation = (method: string) => {
    switch (method) {
      case "vector_only":
        return "High confidence semantic match found. Answering strictly using retrieved vector fragments.";
      case "hybrid":
        return "Medium confidence semantic match. Merging semantic vector chunks with structured company knowledge graph.";
      case "graph_fallback":
        return "Low vector similarity score. Falling back strictly to Neo4j knowledge graph metrics & corporate actions.";
      default:
        return "Corrective RAG lookup pipeline routing.";
    }
  };

  return (
    <div className="rag-page-container">
      {/* Page Header */}
      <div className="rag-page-header">
        <h1>Corporate Transcript RAG</h1>
        <p>Query earnings call transcripts using Pinecone hybrid-search and Neo4j graph fallbacks.</p>
      </div>

      <div className="rag-grid-layout">
        {/* Main Panel */}
        <div className="rag-main-panel">
          
          {/* Query Formulation Card */}
          <Card title="Ask Company Transcript Questions">
            <form onSubmit={handleQuerySubmit}>
              <div className="form-group">
                <label>Natural Language Question</label>
                <div style={{ position: "relative" }}>
                  <input 
                    type="text" 
                    placeholder="e.g. What did management say about revenue and margin growth guidance?" 
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    required
                    style={{ paddingRight: "40px" }}
                  />
                  <Search 
                    size={18} 
                    style={{ 
                      position: "absolute", 
                      right: "14px", 
                      top: "14px", 
                      color: "var(--text-secondary)" 
                    }} 
                  />
                </div>
              </div>

              {/* Preset Chips */}
              <div style={{ marginBottom: "20px" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", fontWeight: 500 }}>
                  Suggested Questions:
                </span>
                <div className="preset-chips-container">
                  {presetQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="preset-chip"
                      onClick={() => setQuestion(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {/* Filter Selector & Advanced Settings Trigger */}
              <div style={{ 
                display: "flex", 
                justifyContent: "space-between", 
                alignItems: "center",
                flexWrap: "wrap",
                gap: "16px",
                marginBottom: "15px"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", width: "100%", maxWidth: "320px" }}>
                  <label style={{ margin: 0, whiteSpace: "nowrap" }}>Company Filter:</label>
                  <select 
                    value={filterCompany}
                    onChange={(e) => setFilterCompany(e.target.value)}
                    style={{ padding: "8px 12px", fontSize: "0.85rem" }}
                  >
                    <option value="">All Tickers (No Filter)</option>
                    {userTickers.map((ticker) => (
                      <option key={ticker} value={ticker}>{ticker}</option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  className="advanced-settings-btn"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                >
                  <Settings size={14} />
                  {showAdvanced ? "Hide Advanced Settings" : "Show Advanced Settings"}
                </button>
              </div>

              {/* Advanced Settings Drawer */}
              {showAdvanced && (
                <div className="advanced-settings-drawer">
                  <div className="setting-row">
                    <div className="setting-label">
                      <span>Retrieve Top K Chunks</span>
                      <span className="val">{topK}</span>
                    </div>
                    <input 
                      type="range" 
                      min="1" 
                      max="10" 
                      value={topK}
                      onChange={(e) => setTopK(parseInt(e.target.value))}
                    />
                  </div>
                  <div className="setting-row">
                    <div className="setting-label">
                      <span>Confidence Threshold</span>
                      <span className="val">{(confidenceThreshold * 100).toFixed(0)}%</span>
                    </div>
                    <input 
                      type="range" 
                      min="0" 
                      max="100" 
                      value={confidenceThreshold * 100}
                      onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value) / 100)}
                    />
                  </div>
                </div>
              )}

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading || question.trim().length < 5}
                style={{ width: "100%", marginTop: "10px" }}
              >
                <Sparkles size={16} />
                {loading ? "Searching transcripts..." : "Submit Question"}
              </button>
            </form>
          </Card>

          {/* RAG Loading Animation Panel */}
          {loading && (
            <div className="rag-loader-card animate-fade-in">
              <div className="pulsing-spinner"></div>
              <h3 style={{ margin: "0 0 10px", fontSize: "1.1rem" }}>Executing Corrective RAG Pipeline</h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                {loadStep === 0 && "Querying Pinecone Vector Database namespaces..."}
                {loadStep === 1 && "Assessing context confidence & semantic relevance..."}
                {loadStep === 2 && "Querying Neo4j structured knowledge graph relationships..."}
                {loadStep === 3 && "Synthesizing SEBI-compliant response with Gemini 1.5..."}
              </p>

              {/* Progress Steps Node Visualizer */}
              <div className="rag-steps-tracker">
                <div className="step-node">
                  <div className={`step-dot ${loadStep >= 0 ? (loadStep > 0 ? "completed" : "active") : ""}`}>
                    {loadStep > 0 ? "✓" : "1"}
                  </div>
                  <div className={`step-text ${loadStep === 0 ? "active" : ""}`}>Semantic Vector</div>
                </div>
                <div className="step-node">
                  <div className={`step-dot ${loadStep >= 1 ? (loadStep > 1 ? "completed" : "active") : ""}`}>
                    {loadStep > 1 ? "✓" : "2"}
                  </div>
                  <div className={`step-text ${loadStep === 1 ? "active" : ""}`}>Confidence Evaluation</div>
                </div>
                <div className="step-node">
                  <div className={`step-dot ${loadStep >= 2 ? (loadStep > 2 ? "completed" : "active") : ""}`}>
                    {loadStep > 2 ? "✓" : "3"}
                  </div>
                  <div className={`step-text ${loadStep === 2 ? "active" : ""}`}>Graph Fallback</div>
                </div>
                <div className="step-node">
                  <div className={`step-dot ${loadStep >= 3 ? "active" : ""}`}>
                    4
                  </div>
                  <div className={`step-text ${loadStep === 3 ? "active" : ""}`}>LLM Synthesis</div>
                </div>
              </div>
            </div>
          )}

          {/* Error Message */}
          {queryError && (
            <div style={{
              background: "var(--alert-error-bg)",
              border: "1px solid rgba(239, 68, 68, 0.25)",
              padding: "16px",
              borderRadius: "12px",
              color: "var(--alert-error)",
              display: "flex",
              alignItems: "center",
              gap: "10px"
            }}>
              <AlertCircle size={20} />
              <div>
                <strong style={{ display: "block", fontSize: "0.9rem" }}>Corrective RAG Pipeline Error</strong>
                <span style={{ fontSize: "0.82rem" }}>{queryError}</span>
              </div>
            </div>
          )}

          {/* RAG Query Answer Output Card */}
          {ragResult && !loading && (
            <div className="animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              
              {/* RAG Metrics & Diagnostics */}
              <div className="diagnostics-panel">
                <div className="diagnostic-item">
                  <span className="diag-label">Retrieval Method</span>
                  <span className="diag-value" style={{ color: "var(--secondary-color)" }}>
                    <Cpu size={16} />
                    {ragResult.retrieval_method.replace("_", " ").toUpperCase()}
                  </span>
                </div>
                
                <div className="diagnostic-item">
                  <span className="diag-label">Retrieval Confidence</span>
                  <div className="diag-value">
                    <span>{(ragResult.confidence * 100).toFixed(0)}%</span>
                    <div className="confidence-bar-outer">
                      <div 
                        className="confidence-bar-inner" 
                        style={{ width: `${Math.min(100, Math.max(0, ragResult.confidence * 100))}%` }}
                      ></div>
                    </div>
                  </div>
                </div>

                <div className="diagnostic-item">
                  <span className="diag-label">Model Instance</span>
                  <span className="diag-value" style={{ color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                    {ragResult.generated_by}
                  </span>
                </div>
              </div>

              {/* Diagnostic Routing Explanation Alert */}
              <div style={{
                background: "rgba(20, 184, 166, 0.03)",
                border: "1px solid rgba(20, 184, 166, 0.15)",
                padding: "10px 16px",
                borderRadius: "8px",
                fontSize: "0.8rem",
                color: "var(--text-secondary)",
                marginTop: "-10px"
              }}>
                <strong>Diagnostics Routing Rule</strong>: {getMethodExplanation(ragResult.retrieval_method)}
              </div>

              {/* RAG Answer Card */}
              <Card 
                title="AI Factual Synthesis"
                actions={
                  <span className="badge badge-success" style={{ fontSize: "0.7rem", gap: "4px" }}>
                    <CheckCircle size={10} />
                    SEBI Compliant Observations
                  </span>
                }
              >
                <div style={{
                  lineHeight: "1.65",
                  fontSize: "1.05rem",
                  color: "var(--text-primary)",
                  whiteSpace: "pre-line"
                }}>
                  {ragResult.answer}
                </div>
              </Card>

              {/* Sources Accordion */}
              {ragResult.sources && ragResult.sources.length > 0 && (
                <div className="accordion-wrapper">
                  <button 
                    type="button"
                    className="accordion-trigger"
                    onClick={() => setSourcesExpanded(!sourcesExpanded)}
                  >
                    <span>Sources Cited ({ragResult.sources.length})</span>
                    {sourcesExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                  
                  {sourcesExpanded && (
                    <div className="accordion-content">
                      <div className="sources-grid animate-fade-in">
                        {ragResult.sources.map((src, idx) => (
                          <div key={idx} className="source-badge-card">
                            <span className="source-title">{src.company} ({src.quarter})</span>
                            <span className="source-meta" title={src.source}>File: {src.source.split(/[\\/]/).pop()}</span>
                            <span className="source-meta">Chunk ID: {src.chunk_id}</span>
                            <span className="source-score">Match: {(src.score * 100).toFixed(1)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Context Drawer Accordion */}
              <div className="accordion-wrapper">
                <button 
                  type="button"
                  className="accordion-trigger"
                  onClick={() => setContextExpanded(!contextExpanded)}
                >
                  <span>Raw LLM Context Drawer</span>
                  {contextExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {contextExpanded && (
                  <div className="accordion-content">
                    {/* Vector Chunks Excerpts */}
                    {ragResult.vector_chunks && ragResult.vector_chunks.length > 0 && (
                      <div style={{ marginBottom: "20px" }}>
                        <h4 style={{ color: "#A5B4FC", fontSize: "0.9rem", marginBottom: "10px" }}>
                          Vector Store Transcript Chunks (Pinecone)
                        </h4>
                        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                          {ragResult.vector_chunks.map((chunk, idx) => (
                            <div key={idx} className="context-chunk-item">
                              <div className="chunk-header">
                                <span>{chunk.company} • {chunk.quarter}</span>
                                <span>Similarity Score: {(chunk.score * 100).toFixed(1)}%</span>
                              </div>
                              <p className="chunk-body">{chunk.content}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Graph Facts JSON Excerpts */}
                    {ragResult.graph_facts && ragResult.graph_facts.length > 0 && (
                      <div>
                        <h4 style={{ color: "#A5B4FC", fontSize: "0.9rem", marginBottom: "10px" }}>
                          Structured Neo4j Graph Relationships
                        </h4>
                        <pre style={{
                          background: "#111827",
                          padding: "14px",
                          borderRadius: "8px",
                          overflowX: "auto",
                          fontSize: "0.75rem",
                          border: "1px solid var(--surface-border)",
                          color: "var(--text-secondary)",
                          margin: 0
                        }}>
                          {JSON.stringify(ragResult.graph_facts, null, 2)}
                        </pre>
                      </div>
                    )}

                    {(!ragResult.vector_chunks || ragResult.vector_chunks.length === 0) && 
                     (!ragResult.graph_facts || ragResult.graph_facts.length === 0) && (
                      <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", margin: 0 }}>
                        No context retrieved from Vector store or Neo4j database.
                      </p>
                    )}
                  </div>
                )}
              </div>

            </div>
          )}

        </div>

        {/* Sidebar Options & Stats Panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          
          {/* Vector Store statistics */}
          <Card title="Vector Store Stats">
            {vectorStats ? (
              <div className="stats-list">
                <div className="stat-box-row">
                  <span className="label">Status</span>
                  <span className="value" style={{ color: "var(--alert-success)" }}>
                    {vectorStats.status.toUpperCase()}
                  </span>
                </div>
                <div className="stat-box-row">
                  <span className="label">Engine</span>
                  <span className="value">{vectorStats.backend.toUpperCase()}</span>
                </div>
                <div className="stat-box-row">
                  <span className="label">Pinecone Index</span>
                  <span className="value" style={{ maxWidth: "160px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={vectorStats.index}>
                    {vectorStats.index}
                  </span>
                </div>
                <div className="stat-box-row">
                  <span className="label">User Namespace</span>
                  <span className="value" style={{ fontSize: "0.75rem", color: "var(--primary-color)" }}>
                    {vectorStats.namespace}
                  </span>
                </div>
                <div className="stat-box-row">
                  <span className="label">Namespace Vectors</span>
                  <span className="value">{vectorStats.namespace_vectors} vectors</span>
                </div>
                <div className="stat-box-row">
                  <span className="label">Total Index Vectors</span>
                  <span className="value">{vectorStats.total_vectors} vectors</span>
                </div>
                <div className="stat-box-row">
                  <span className="label">Dimension Size</span>
                  <span className="value">{vectorStats.dimension} d</span>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: "center", color: "var(--text-secondary)", padding: "10px" }}>
                Loading vector stats...
              </div>
            )}
          </Card>

          {/* Transcript Ingestor Control Card */}
          <Card title="Ingest Earnings transcripts">
            <form onSubmit={handleIngestSubmit}>
              <div className="form-group">
                <label>Directory Path</label>
                <input 
                  type="text" 
                  value={ingestPath} 
                  onChange={(e) => setIngestPath(e.target.value)} 
                  required
                />
              </div>

              {ingestStatus && (
                <div style={{
                  background: ingestStatus.type === "success" ? "rgba(16, 185, 129, 0.05)" : "var(--alert-error-bg)",
                  border: ingestStatus.type === "success" 
                    ? "1px solid rgba(16, 185, 129, 0.25)" 
                    : "1px solid rgba(239, 68, 68, 0.25)",
                  padding: "10px 12px",
                  borderRadius: "8px",
                  fontSize: "0.78rem",
                  color: ingestStatus.type === "success" ? "var(--alert-success)" : "var(--alert-error)",
                  marginBottom: "16px"
                }}>
                  {ingestStatus.message}
                </div>
              )}

              <button
                type="submit"
                className="btn btn-secondary"
                disabled={ingesting || !ingestPath.trim()}
                style={{ width: "100%", gap: "6px" }}
              >
                <Upload size={14} className={ingesting ? "animate-spin" : ""} />
                {ingesting ? "Ingesting data..." : "Start Ingestion"}
              </button>
            </form>
          </Card>

        </div>
      </div>
    </div>
  );
};

export default RagView;
