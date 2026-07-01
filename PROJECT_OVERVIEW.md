# NiftyMind Project Overview

For the user-facing application journey and expected product usage, see [USER_USAGE_GUIDE.md](USER_USAGE_GUIDE.md).

## Purpose (Post-Pivot)

NiftyMind has pivoted from a features-centric F&O Option Chain analytics platform into a comprehensive **AI-Powered Portfolio Intelligence Platform** aimed at helping retail investors understand:
1. **Portfolio Risk & Allocation** (structural risks).
2. **Company Fundamentals** (using earnings call transcript RAG).
3. **Behavioral Investing Patterns** (guardrails against bad habits like overtrading, concentration, or FOMO).

At a high level, the project is intended to help users understand market structure, portfolio metrics, and behavioral biases without giving direct buy, sell, or hold recommendations (ensuring SEBI compliance).

Our core architectural vision takes the user through a unified flow:
$$\text{Portfolio Ingestion (CSV/Excel/Manual)} \rightarrow \text{Risk Engine} \rightarrow \text{Corporate RAG} \rightarrow \text{Behavioral Analysis} \rightarrow \text{AI Portfolio Summary}$$

---

## Core Pillars of the Platform

We have implemented the following backend modules to deliver this end-to-end journey:

### Module 1: Portfolio Ingestion & Management
- **Description**: Users can create/delete portfolios, manually add/sell positions, or upload standard broker files (CSV or Excel `.xlsx` templates) to batch-import holdings.
- **Implementation**: Powered by raw `asyncpg` SQL transactions for high performance and `openpyxl` for binary Excel sheet parsing. Includes a robust scanning algorithm that dynamically auto-detects the header row and maps synonyms (ignoring broker metadata/summaries at the top).
- **Core Files**: 
  - [portfolios.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/api/routes/portfolios.py)
  - [portfolio.py (CRUD)](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/db/crud/portfolio.py)

### Module 2: Risk Engine
- **Description**: Groups holdings by sector, calculates individual stock concentration, and translates the Herfindahl-Hirschman Index (HHI) into a simple 0–100 **Diversification Score**.
- **Implementation**: Utilizes Neo4j query mappings to look up company sectors and calculates portfolio concentration metrics dynamically.
- **Core Files**:
  - [risk.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/api/routes/risk.py)

### Module 3: Corporate Intelligence RAG
- **Description**: Connects user questions to transcript chunks stored in Pinecone using a custom query filter to restrict searches exclusively to the stocks present in the user's active portfolio.
- **Implementation**: Uses Gemini embedding models, Pinecone namespaces/metadata filters, and a corrective RAG flow (vector retrieval $\rightarrow$ confidence scoring $\rightarrow$ graph fallback on low confidence).
- **Core Files**:
  - [rag.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/api/routes/rag.py)
  - [corrective_rag.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/rag/corrective_rag.py)

### Module 4: Behavioral Guardrails
- **Description**: Analyzes user transaction history and holdings to flag emotional behaviors:
  - **FOMO** (buying back into a symbol within 24 hours of selling it).
  - **Revenge Trading** (escalating trade size/value after a recent losing sale).
  - **Overtrading** (more than 5 transactions in a 30-minute window).
  - **Excessive Concentration** (greater than 30% weight in a single symbol).
- **Implementation**: Stateful machine tracking using **LangGraph** with SQLite checkpointing and a rules-based behavioral analyzer.
- **Core Files**:
  - [behavior.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/api/routes/behavior.py)
  - [behavior_analyzer.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/services/behavior_analyzer.py)

### Module 5: AI Portfolio Advisor
- **Description**: The orchestrator that gathers holdings, HHI risk metrics, active behavioral warnings, and corporate transcript highlights, and uses Gemini to compile a SEBI-compliant narrative of structural and fundamental observations.
- **Core Files**:
  - [advisor.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/api/routes/advisor.py)

### Module 6: AI News Watchdog & Stop Loss Advisor
- **Description**: Automatically aggregates Google News RSS items for user holdings and uses Gemini to analyze sentiment (positive/negative/neutral), impact level (high/medium/low), and expected price effects. Suggests compliance-friendly stop-losses, expected quarterly targets (Q1-Q4), and issues Danger Zone alerts.
- **Core Files**:
  - [news.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/api/routes/news.py)
  - [news_aggregator.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/services/news_aggregator.py)
  - [news_sentiment_service.py](file:///c:/Users/harsh/Downloads/Cooking/GenAi/NiftyMind/backend/app/services/news_sentiment_service.py)

*Note: The legacy F&O engine (option chain parsers, PCR calculations, max pain, and market feed simulator) was preserved but modularized under `backend/app/analytics/fno/` to keep the root directories clean.*

---

## Tech Stack

### Backend
- **FastAPI**: Main HTTP web framework.
- **SQLAlchemy (Async ORM)**: For PostgreSQL-backed user registration and session management.
- **asyncpg**: High-performance raw PostgreSQL client for fast portfolio CRUD queries.
- **LangGraph**: Stateful machine flow for trade tracking and behavioral logging.
- **Pinecone**: Vector database for corporate earnings call transcripts.
- **Neo4j**: Graph database for company, sector, and competitor relationship queries.
- **Google Gemini**: Large language model for generating RAG responses and SEBI-compliant advisor narratives.

### Frontend
- **React, Vite, TypeScript**: Premium, fast frontend SPA.
- **Vanilla CSS**: Beautiful glassmorphism, responsive grids, and harmony-color themes.

---

## Repository Structure

```text
NiftyMind/
  README.md
  PROJECT_OVERVIEW.md
  USER_USAGE_GUIDE.md
  backend/
    main.py
    requirements.txt
    app/
      api/routes/       # Router endpoints (portfolios, risk, behavior, advisor, RAG)
      auth/             # Authentication dependencies
      db/               # session.py, base.py, and database CRUD operations
      rag/              # Corrective RAG services and vector store integrations
      graph/            # Neo4j client and schemas
      services/         # Behavioral analyzer
      analytics/fno/    # Modularized legacy Option Chain codes
  frontend/
    package.json
    src/
      components/       # Reusable UI (Card, RiskGauge, GuardrailAlerts)
      pages/            # Dashboard, PortfolioView, AuthPage
      lib/api.ts        # Fetch client supporting JSON and FormData uploads
```

---

## Data Storage

| Module/Area | Storage Layer |
| --- | --- |
| Users & Auth | PostgreSQL |
| Portfolios & Holdings | PostgreSQL |
| Portfolio Transactions | PostgreSQL |
| Trader LangGraph state | SQLite via LangGraph checkpointing |
| Transcript vectors | Pinecone |
| Corporate sectors/relationships | Neo4j |
| Market events | In-memory dictionary |
