# Bruce
"Agent Bruce" is an intelligent system that can collect, analyze, correlate, reason and assist investigators in making decisions from large volumes of digital evidence.

### **AgentBruce: System Architecture & Implementation Blueprint**
PP
This architectural blueprint outlines a production-ready, error-resistant implementation framework for the AgentBruce Agentic Investigation Operating System.

## **Technical Architecture Overview**

The system architecture decouples heavy computational machine learning inference from the real-time agentic reasoning layer to prevent blocking I/O and handle high-throughput evidence extraction.

\[Evidence Ingestion\] ──\> \[FastAPI Gateway\] ──\> \[Redis Queue\] ──\> \[Celery Workers\]  
                                                                     │  
  ┌──────────────────────────────────────────────────────────────────┘  
  ▼  
\[Processing Layer (YOLO, Whisper, OCR)\] ──\> \[Structured Artifacts\]  
                                                   │  
  ┌────────────────────────────────────────────────┘  
  ▼  
\[LangGraph Orchestrator\] \<──\> \[Vector DB: Qdrant\] & \[Graph DB: Neo4j\]  
  │ (Executes 7 Specialized Agents \+ OSINT Agent)  
  ▼  
\[Next.js Investigator Command Center via WebSockets\]

### **Data Flow Execution Sequence**

1. **Ingestion**: Raw evidence files are uploaded via a Next.js frontend to secured AWS S3/MinIO buckets via presigned URLs through the FastAPI gateway.  
2. **Asynchronous Processing**: Ingestion triggers a Celery task. Heavy ML models (YOLOv8, Whisper, CLIP) extract raw text, entities, face vectors, and metadata.  
3. **Database Insertion**: Extracted entities are loaded as structural nodes in Neo4j, and text embeddings are indexed in Qdrant.  
4. **Agentic Pipeline (LangGraph)**: The Intelligence Fusion Agent instantiates state evaluation, parallel-routing queries to specialized sub-agents (including the OSINT Agent) to evaluate threat level, timeline, and relationships.  
5. **Real-time Push**: Results are streamed via WebSockets back to the Next.js Command Center interface.

## **Directory Structure**

agentbruce/  
├── backend/  
│   ├── app/  
│   │   ├── \_\_init\_\_.py  
│   │   ├── main.py                 \# FastAPI Application entry point  
│   │   ├── core/  
│   │   │   ├── config.py           \# Environment and security configurations  
│   │   │   ├── database.py         \# Neo4j, Qdrant, and PostgreSQL initializers  
│   │   │   └── security.py         \# JWT verification & RBAC definitions  
│   │   ├── workers/  
│   │   │   ├── tasks.py            \# Celery tasks for heavy ML processing  
│   │   │   └── pipeline.py         \# OCR, Face Analysis, and Object Detection wrappers  
│   │   ├── agents/  
│   │   │   ├── state.py            \# LangGraph shared state definitions  
│   │   │   ├── graph.py            \# LangGraph state machine routing configuration  
│   │   │   └── specialized/  
│   │   │       ├── grooming.py     \# Grooming Detection Agent logic  
│   │   │       ├── victim\_risk.py  \# Victim Risk Assessment Agent logic  
│   │   │       ├── multimedia.py   \# Multimedia Intelligence Agent logic  
│   │   │       ├── synthetic.py    \# Synthetic Media Detection Agent logic  
│   │   │       ├── timeline.py     \# Timeline Reconstruction Agent logic  
│   │   │       ├── osint.py        \# OSINT Aggregator Agent logic  
│   │   │       └── fusion.py       \# Intelligence Fusion Core Agent logic  
│   │   ├── api/  
│   │   │   └── v1/  
│   │   │       ├── evidence.py     \# Upload & processing status endpoints  
│   │   │       ├── cases.py        \# Case management CRUD operations  
│   │   │       └── intelligence.py \# Live streaming analysis graph data  
│   │   └── models/  
│   │       └── schemas.py          \# Pydantic data models  
│   ├── Dockerfile  
│   └── requirements.txt  
├── frontend/  
│   ├── src/  
│   │   ├── components/  
│   │   │   ├── ui/                 \# shadcn/ui base elements  
│   │   │   ├── dashboard/          \# Case Overview & Metrics components  
│   │   │   ├── graph/              \# Neo4j interactive D3 graph rendering  
│   │   │   └── timeline/           \# Interactive event sequence view  
│   │   ├── hooks/  
│   │   ├── pages/  
│   │   └── lib/  
│   │       └── api.ts              \# WebSocket and Axios clients  
│   ├── package.json  
│   └── tailwind.config.js  
└── docker-compose.yml
