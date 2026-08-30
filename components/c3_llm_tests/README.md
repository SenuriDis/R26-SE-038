# R26-SE-038 — LLM-Based Test Generation & Code Review Component

**IT4010 Research Project — 2026 Jan**  
**Student:** Harrish Shermon (IT22177964)  
**Specialization:** Software Engineering  
**Research Group:** CEAI — Centre of Excellence for AI

---

## Overview

This is Component 3 of a four-component automated software testing system.
It receives high-risk Python code segments from an ML-based defect predictor
(Component 2), automatically generates pytest test cases for them, validates
and repairs those tests, and performs a semantic code quality review.

### The Three-Agent Architecture
High-Risk Segments (from Component 2)
↓
RAG Indexer (ChromaDB)
↓
┌─────────────────────────────────┐
│  Agent 1 — Test Generation      │  GPT-4o / LLaMA 3.3 70b
│  Agent 2 — Validation & Repair  │  DeepSeek-Coder / LLaMA 3.3 70b
│  Agent 3 — Code Review          │  GPT-4o / LLaMA 3.3 70b
└─────────────────────────────────┘
↓
Validated Tests + Review Report
(passed to Component 4)

---

## Project Structure
r26-se-038/
├── src/
│   ├── agents/
│   │   ├── agent1_test_generation.py
│   │   ├── agent2_test_validation.py
│   │   └── agent3_code_review.py
│   ├── rag/
│   │   ├── indexer.py
│   │   └── retriever.py
│   ├── models/
│   │   └── schemas.py
│   ├── pipeline/
│   │   └── pipeline.py
│   └── utils/
│       ├── ast_utils.py
│       └── output_writer.py
├── api/
│   └── main.py
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── api/
├── config/
│   └── settings.py
├── data/
│   └── chroma_db/
├── outputs/
├── main.py
└── requirements.txt

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone <repo-url>
cd <repo-folder>
```

### 2. Create and activate virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install Python dependencies

pip install -r requirements.txt


### 4. Set up environment variables

copy .env.example .env       # Windows
cp .env.example .env         # Mac/Linux


Edit `.env` and add your API key:
GROQ_API_KEY=your-groq-api-key-here
Get a free Groq API key at: https://console.groq.com

### 5. Install frontend dependencies

cd frontend
npm install
cd ..




## Running the System

### Start the backend (Terminal 1)

python main.py

API runs at: http://127.0.0.1:8000

### Start the frontend (Terminal 2)

cd frontend
npm run dev

Frontend runs at: http://localhost:5173

---

## Running the Demo Scripts

### Sample project demo
python run_demo.py


### Real repository demo (requests library)
python run_requests_demo.py




## Performance Targets

| Metric | Target |
|--------|--------|
| Test Syntactic Validity Rate | > 80% |
| Code Coverage | > 65% |
| Code Review False Positive Rate | < 25% |
| Developer Usefulness Rating | > 3.5 / 5.0 |

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| LLM (Agent 1 & 3) | Groq — LLaMA 3.3 70b |
| LLM (Agent 2) | Groq — LLaMA 3.3 70b / DeepSeek-Coder |
| RAG Pipeline | LlamaIndex + ChromaDB |
| Embeddings | BAAI/bge-small-en-v1.5 (local) |
| Static Analysis | Pylint + Python AST |
| Backend API | FastAPI |
| Frontend | React + Vite |
| Test Framework | pytest + coverage.py |

---

## SDG Alignment

- **SDG 8** — Decent Work and Economic Growth: Reduces manual testing effort
- **SDG 9** — Industry, Innovation and Infrastructure: Strengthens software quality