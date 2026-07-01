# NiftyMind User Usage Guide

## Purpose

This document explains NiftyMind from the user's perspective: what the application is for, who uses it, and how a user would move through the product once the frontend is built around the existing backend capabilities.

For the technical architecture and backend flow, see [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md).

## Who NiftyMind Is For

NiftyMind is intended for traders, market learners, analysts, and financial research users who want to understand Indian market structure using data-assisted insights.

The application is not designed to tell users what to buy or sell. Instead, it helps users interpret market data, identify behavioral risks, ask questions about company transcripts, and explore structured corporate action information.

## Core User Value

From the user's point of view, NiftyMind provides five major experiences:

1. Understand option-chain structure.
2. Receive plain-English market observations.
3. Track simulated trading behavior and detect emotional trading patterns.
4. Ask questions about earnings transcripts and company commentary.
5. Explore company metrics, dividends, buybacks, and relationships through a knowledge graph.

## Expected User Journey

## 1. User Opens The Application

The user lands on the NiftyMind web application.

The current frontend only checks whether the backend is online, but the intended product experience would start with a dashboard that shows:

- market feed status
- active trading session status
- latest option-chain summary
- recent guardrail alerts
- RAG/graph query entry points

## 2. User Registers Or Logs In

The user creates an account or logs in.

Expected user actions:

- enter email
- enter password
- optionally enter full name
- submit registration or login form

Backend flow:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- backend returns access and refresh tokens
- frontend stores tokens securely for authenticated requests

Why this matters:

- trader sessions are user-owned
- RAG namespaces are intended to be user-scoped
- protected APIs require authentication

## 3. User Views The Main Dashboard

After login, the user should see a dashboard focused on market understanding and self-monitoring.

Typical dashboard sections:

- NIFTY market feed panel
- option-chain metrics panel
- AI narrative panel
- active trader session panel
- behavioral guardrail alerts
- transcript question box
- graph/company search box

The dashboard should present observations, not trading instructions.

Example user-facing language:

- "OI data suggests call concentration near 24500."
- "PCR is currently in a neutral range."
- "A high-severity behavior flag was detected in this session."
- "Transcript context found from TCS Q3 FY2025."

## 4. User Explores Option-Chain Analytics

The user can upload or stream an option-chain snapshot.

Expected user actions:

- choose underlying, such as NIFTY
- provide option-chain snapshot data
- run parse, stream, or analysis flow

Backend endpoints:

- `POST /api/v1/option-chain/parse`
- `POST /api/v1/option-chain/stream`
- `POST /api/v1/option-chain/analyse`

What the user receives:

- total call open interest
- total put open interest
- put-call ratio
- PCR signal
- max pain strike
- top call OI strikes
- top put OI strikes
- market sentiment label
- delta report when previous data exists
- OI spike alerts
- AI-generated plain-English narrative

Example usage:

1. User submits a NIFTY option-chain snapshot.
2. App shows PCR, max pain, and OI concentration.
3. User submits a later snapshot.
4. App compares the new snapshot with the previous one.
5. App highlights any major OI buildup or unwinding.
6. App generates a neutral market narrative.

## 5. User Watches Real-Time Market Feed

The user can connect to a live or simulated feed.

Current backend route:

- `WS /ws/feed`

Expected user experience:

- app opens a WebSocket connection
- user sees periodic market updates
- option-chain metrics refresh automatically
- AI narrative updates as new snapshots arrive
- spike alerts are shown when detected

Current implementation:

- backend generates synthetic NIFTY snapshots
- snapshots are processed through the OI tracker
- processed updates are broadcast over WebSocket

Future production usage:

- replace synthetic feed with real market data provider
- retain the same processing and display pattern

## 6. User Creates A Trader Session

The user starts a session to track simulated trading behavior.

Backend endpoint:

- `POST /api/v1/sessions`

Expected user actions:

- click "New Session"
- optionally name the session
- begin logging simulated trades

What the app creates:

- a unique session ID
- user ownership record in the database
- LangGraph-backed session state

The session is used to monitor behavior, not to place real trades.

## 7. User Logs Trades

The user adds trades into the active session.

Backend endpoint:

- `POST /api/v1/sessions/{session_id}/trades`

Expected user inputs:

- symbol
- direction: LONG or SHORT
- entry price
- quantity
- optional notes

The app updates:

- total trades
- open trades
- open trade IDs
- session status
- behavior analysis

Example:

```text
Symbol: NIFTY
Direction: LONG
Entry Price: 24520
Quantity: 50
Notes: Breakout attempt
```

## 8. User Closes Trades

The user closes an open simulated trade.

Backend endpoint:

- `POST /api/v1/sessions/{session_id}/trades/close`

Expected user inputs:

- trade ID
- exit price

The app calculates:

- PnL
- total session PnL
- consecutive wins
- consecutive losses
- updated behavioral state

## 9. User Receives Behavioral Guardrail Alerts

The behavioral guardrail system watches the session for risky patterns.

Session WebSocket route:

- `WS /ws/session/{session_id}`

Detected patterns:

- FOMO after a loss
- revenge trading after consecutive losses
- overtrading within a short window
- unusually large position sizing

Expected user experience:

- user keeps the session page open
- frontend connects to session WebSocket
- backend sends live alerts when behavior flags appear
- app displays a visible alert with severity and explanation

Example alert:

```text
REVENGE TRADING DETECTED:
3 consecutive losses detected. Consider a cooling-off period before the next trade.
```

The alert should be framed as risk awareness, not as a command.

## 10. User Recovers Previous Sessions

The user can list and recover sessions.

Backend endpoints:

- `GET /api/v1/sessions`
- `GET /api/v1/sessions/{session_id}/recover`

Expected user experience:

- user opens session history
- app shows previous active sessions
- user selects a session
- app restores the session summary and state

This allows continuity after refresh or restart, depending on available persisted state.

## 11. User Ingests Company Transcripts

The user can ingest transcript files for later question answering.

Backend endpoint:

- `POST /api/v1/rag/ingest`

Expected user actions:

- choose transcript directory or use default
- trigger ingestion

Backend flow:

1. Load text files from the transcript directory.
2. Extract metadata such as company, quarter, and date.
3. Split transcripts into chunks.
4. Generate Gemini embeddings.
5. Store vectors in Pinecone.

Expected user result:

- number of documents loaded
- number of chunks ingested
- vector store status

## 12. User Searches Transcript Context

The user asks a retrieval question over transcripts.

Backend endpoint:

- `POST /api/v1/rag/query`

Expected user inputs:

- question
- top K results
- optional company filter

Expected user output:

- relevant transcript chunks
- company
- quarter
- source file
- chunk ID
- vector store stats

Example questions:

- "What did TCS say about margins?"
- "Summarize HDFC Bank asset quality commentary."
- "What was Infosys management's revenue outlook?"

## 13. User Asks A Full RAG Question

The user asks a natural language question and expects a concise answer.

Backend endpoint:

- `POST /api/v1/rag/ask`

Expected flow:

1. Retrieve relevant transcript chunks from Pinecone.
2. Compute retrieval confidence.
3. If confidence is high, answer from vector context.
4. If confidence is medium or low, use Neo4j graph fallback or hybrid context.
5. Gemini generates a concise answer using only retrieved context.

Expected user output:

- answer
- confidence score
- retrieval method
- sources
- graph facts, when used
- vector chunks, when used

The answer should remain factual, contextual, and non-advisory.

## 14. User Explores Company And Corporate Action Graph

The user can inspect structured company data.

Backend endpoints:

- `POST /api/v1/graph/ingest`
- `GET /api/v1/graph/company/{ticker}`
- `GET /api/v1/graph/actions`
- `GET /api/v1/graph/metrics`
- `GET /api/v1/graph/competitors/{ticker}`
- `POST /api/v1/graph/query`
- `GET /api/v1/graph/stats`

Expected user actions:

- search for a company ticker
- filter corporate actions
- compare financial metrics
- inspect competitor relationships
- ask a simple natural language graph question

Example questions:

- "Show dividends."
- "Which companies have buybacks?"
- "Show IT companies."
- "Show banking metrics."

Current graph data is static sample data, so production usage would require a richer ingestion pipeline.

## 15. User Receives Webhook-Based Market Events

The app can accept market events from external systems.

Backend endpoints:

- `POST /api/v1/events`
- `GET /api/v1/events`
- `POST /api/v1/webhooks/events`
- `POST /api/v1/webhook/market-event`

Expected usage:

- external monitoring system sends market event
- backend acknowledges the event
- future frontend could show event stream or alert timeline

Current limitation:

- event storage is in memory, so events reset when the server restarts.

## User Roles

## Trader

Uses:

- option-chain analytics
- real-time market feed
- trader sessions
- guardrail alerts

Goal:

- understand market structure and personal trading behavior.

## Analyst

Uses:

- transcript RAG
- graph queries
- corporate actions
- financial metrics

Goal:

- research companies and extract factual context.

## Learner

Uses:

- AI market narratives
- RAG answers
- option-chain explanations
- behavior alerts

Goal:

- learn how market signals and trading patterns are interpreted.

## Example End-To-End Scenario

1. User logs in.
2. User opens the dashboard.
3. User connects to the NIFTY market feed.
4. App displays PCR, max pain, OI concentration, and AI narrative.
5. User creates a trading session.
6. User logs a simulated trade.
7. User closes the trade at a loss.
8. User quickly opens another larger trade.
9. Guardrail system detects possible FOMO or revenge sizing.
10. App sends a WebSocket alert.
11. User asks, "What did TCS say about margins in Q3?"
12. RAG retrieves transcript chunks and generates a sourced answer.
13. User checks graph data for TCS dividends or buybacks.

This is the intended combined workflow: market context, behavior awareness, and company research in one application.

## What The Frontend Should Eventually Provide

To make the existing backend usable, the frontend should add:

- authentication screens
- protected dashboard layout
- option-chain upload/input screen
- real-time market feed panel
- AI narrative display
- session creation and session history
- trade entry and trade close forms
- guardrail alert panel
- transcript ingestion screen
- RAG question interface
- graph explorer
- event timeline

## Product Boundary

NiftyMind should consistently avoid:

- direct buy/sell/hold recommendations
- guaranteed predictions
- certainty about future price movement
- personalized financial advice

It should consistently provide:

- factual market observations
- educational explanations
- risk-awareness cues
- transparent sources for RAG answers
- neutral language around trading behavior

## Related Documentation

- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md): technical architecture, backend modules, storage, and current gaps.
- `USER_USAGE_GUIDE.md`: user journey, application usage, and expected product experience.
