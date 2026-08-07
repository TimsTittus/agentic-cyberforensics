# AgentBruce — Agentic Cyberforensics Investigation Operating System

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Next.js](https://img.shields.io/badge/Next.js-16%2B-black.svg)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.0-008CC1.svg)](https://neo4j.com/)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.8-dc2626.svg)](https://qdrant.tech/)

**AgentBruce** is an autonomous, multi-agent cyberforensics operating system engineered to ingest, process, correlate, and analyze multi-modal digital evidence (chat exports, images, audio, and metadata) at scale. It combines heavy asynchronous ML extraction with a **LangGraph** multi-agent state machine, **Neo4j** knowledge graph relationship tracking, **Qdrant** 384-dimensional vector semantic search, and a **Next.js 16** glassmorphism investigator command center.

---

## 🏛️ System Architecture

```
                                  +-------------------------------------------------+
                                  |   Next.js 16 Investigator Command Center        |
                                  |   (Glassmorphism UI, D3/Force Graph, WebSockets) |
                                  +-----------------------+-------------------------+
                                                          |
                                           HTTPS / WSS    | API Gateway
                                                          v
                                  +-------------------------------------------------+
                                  |              FastAPI Gateway (v1)               |
                                  +------------+--------------------+---------------+
                                               |                    |
                         Evidence Upload       |                    | WebSocket & Search
                         (SHA-256 Hashed)      v                    v
                                  +------------+----+      +--------+---------------+
                                  |  PostgreSQL DB  |      |   LangGraph Multi-Agent|
                                  | (Cases & Evid)  |      |   State Machine Core   |
                                  +-----------------+      +--------+---------------+
                                                                    |
                                  +-----------------+               | Parallel & Sequential
                                  |   Redis Queue   |               | Agent Execution
                                  +--------+--------+               v
                                           |               +--------+---------------+
                                           v               |  Specialized AI Agents |
                                  +--------+--------+      |  (Grooming, Vision,    |
                                  | Celery Workers  |----->|   OSINT, Synthetic,    |
                                  | (YOLO, OCR, WSP)|      |   Timeline, Risk)      |
                                  +-----------------+      +--------+---------------+
                                                                    |
                                                                    v
                                                     +--------------+--------------+
                                                     |                             |
                                                     v                             v
                                          +----------+----------+       +----------+----------+
                                          |   Neo4j Graph DB    |       |   Qdrant Vector DB   |
                                          | (Suspects, Victims, |       | (384d all-MiniLM-    |
                                          |  Accounts, Locations|       |  L6-v2 Embeddings)   |
                                          +---------------------+       +---------------------+
```

---

## 🌟 Key Features

- **Multi-Agent LangGraph Orchestration**: Executes 8 specialized agents in parallel and sequential topology:
  1. `Gateway`: Validates initial payload & metadata.
  2. `Grooming Agent`: Evaluates chat logs for 5 grooming stages (*Trust*, *Isolation*, *Secrecy*, *Sexualization*, *Coercion*).
  3. `Multimedia Agent`: Fuses YOLOv8 object detections with EasyOCR location strings.
  4. `Synthetic Media Agent`: Analyzes image metadata and pixel variance to calculate deepfake probability.
  5. `OSINT Agent`: Performs asynchronous 5s-timeout external breach lookups across suspect emails/IPs.
  6. `Timeline Agent`: Sorts all cross-evidence events chronologically.
  7. `Fusion Agent`: Upserts 384d vector embeddings into Qdrant and merges Cypher nodes into Neo4j.
  8. `Risk Assessor`: Computes numerical threat matrix scores (0–100) and risk levels (*Critical*, *High*, *Medium*, *Low*).
- **Interactive Knowledge Graph**: Renders suspect-to-victim communication networks, IP locations, and account ownership interactively using `react-force-graph-2d`.
- **Vector Evidence Explorer**: Natural language semantic search powered by Qdrant vector similarity.
- **Real-Time Execution WebSockets**: Streams live agent state transitions to the UI via persistent WebSocket sockets.
- **AI Case Summary & Lead Report Generator**: Synthesizes graph topology and vector hits into printable lead reports.
- **Chain-of-Custody Integrity**: Streaming 64 KB chunked SHA-256 cryptographic hashing rejects duplicate evidence.

---

## 📁 Repository Structure

```
agentic-cyberforensics/
├── backend/
│   ├── app/
│   │   ├── api/v1/            # FastAPI API routers (cases, graph, search, report, ws, health, ingestion)
│   │   ├── agents/            # LangGraph orchestrator state machine & 8 specialized agents
│   │   ├── core/              # Database connection managers (Postgres, Neo4j, Qdrant, Redis) & config
│   │   ├── models/            # SQLAlchemy schemas & Pydantic models
│   │   └── workers/           # Celery background tasks & ML extractors (YOLO, EasyOCR, Whisper)
│   ├── tests/                 # Comprehensive Pytest test suite (29 tests)
│   ├── Dockerfile             # Multi-stage Python 3.12 build
│   └── requirements.txt       # Dependencies (langgraph, fastapi, sentence-transformers, neo4j, qdrant-client)
├── frontend/
│   ├── src/
│   │   ├── app/               # Next.js 16 App Router (page.tsx, layout.tsx, globals.css)
│   │   ├── components/        # GraphExplorer, LiveExecution, UI primitives (card, badge, input)
│   │   └── lib/               # API clients, mock fallbacks, and utility helpers
│   ├── package.json           # Next.js, TailwindCSS, lucide-react, react-force-graph-2d dependencies
│   └── tsconfig.json          # TypeScript configuration
├── docker-compose.yml         # Full multi-container orchestration stack
├── .env.example               # Environment variables template
└── README.md                  # Project documentation
```

---

## 🚀 Quickstart & Setup Guide

### Option A: Complete Docker Compose Setup (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/TimsTittus/agentic-cyberforensics.git
   cd agentic-cyberforensics
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   ```

3. **Launch the entire stack**:
   ```bash
   docker-compose up -d --build
   ```

4. **Access Applications**:
   - **Investigator Command Center**: `http://localhost:3000`
   - **FastAPI Documentation**: `http://localhost:8000/docs`
   - **Neo4j Browser**: `http://localhost:7474`
   - **Qdrant Dashboard**: `http://localhost:6333/dashboard`

---

### Option B: Local Development Setup

#### Prerequisites
- **Python**: 3.12+
- **Node.js**: 20+ (with `npm` or `bun`)
- **Datastores**: PostgreSQL, Neo4j, Qdrant, Redis (can be run via Docker)

#### 1. Start Infrastructure Services via Docker
```bash
docker-compose up -d postgres neo4j qdrant redis
```

#### 2. Backend Setup
```bash
cd backend

# Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 3. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
Open `http://localhost:3000` in your web browser.

---

## 🧪 Verification & Testing

### Running Backend Unit & Integration Tests
The backend test suite verifies all ML extractors, LangGraph agent routing, Neo4j/Qdrant fusion, WebSockets streaming, and AI report generation:

```bash
cd backend
python3 -m pytest tests/ -v
```

Expected Output:
```
============================== 29 passed in 30.12s ==============================
```

### Verifying Frontend TypeScript Compilation & Production Build
```bash
cd frontend
npm run build
```

---

## 📡 API Reference Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/v1/health` | `GET` | System operational health & database connectivity check |
| `/api/v1/cases` | `GET` / `POST` | List open cases or create a new investigation case |
| `/api/v1/evidence/upload` | `POST` | Stream multipart evidence file with SHA-256 hashing |
| `/api/v1/graph` | `GET` | Fetch Neo4j entity nodes and edges for force graph visualization |
| `/api/v1/search` | `POST` / `GET` | Qdrant vector semantic search (384d all-MiniLM-L6-v2) |
| `/api/v1/report/generate` | `POST` | Generate executive AI case lead report |
| `/api/v1/ws/investigation/{case_id}` | `WS` | Real-time WebSocket streaming of LangGraph state events |

---

## 🛡️ Chain of Custody & Security

- **Cryptographic Integrity**: All ingested evidence files are hashed using streaming SHA-256 before storage (`storage/evidence/{case_id}/{sha256}.bin`). Duplicate uploads are rejected automatically.
- **Role-Based Access Control**: JWT tokens secure API endpoints, with configurable expiration windows.
- **Fail-Safe Fallbacks**: Database managers degrade gracefully into non-blocking simulation modes if connectivity is lost during offline field operations.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.