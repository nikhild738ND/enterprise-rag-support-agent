# Enterprise RAG Support Agent (Simple Local Version)

This project builds the exact support-copilot workflow you asked for, but replaces PostgreSQL + pgvector with:

- **SQLite** for documents, chunks, traces, prompts, outputs, feedback, tickets, accounts, orders, and eval results
- **FAISS** for vector search

That makes the project much easier to run, explain, and demo in an interview.

## 1. What this system does

The app supports:

- parsing **PDF / HTML / Markdown** files
- chunking and embedding support documents
- storing chunks in SQLite and FAISS
- answering questions in two modes:
  - **simple RAG**: retrieve top chunks, then answer
  - **agentic RAG**: a LangChain agent uses tools to retrieve docs, query SQL, and call ticket/order lookup tools
- returning answers with citations
- collecting user feedback
- running an eval set with **200+ labeled Q&A pairs**
- reporting retrieval hit rate, answer correctness, citation correctness, hallucination rate, and p95 latency
- generating a Matplotlib dashboard
- storing traces, prompts, outputs, and feedback in SQL
- running a load test and failure analysis

## 2. Why this architecture is good for interviews

This design is strong because it separates the system into the same components a production RAG app needs:

1. **Ingestion layer**: parse files, clean text, chunk documents
2. **Retrieval layer**: embed chunks and run semantic search
3. **Reasoning layer**:
   - simple RAG for low-latency doc questions
   - agentic RAG for multi-step questions that need docs + SQL + API
4. **Observability layer**: traces, prompts, tool calls, outputs, latency, cost
5. **Evaluation layer**: labeled dataset, automated metrics, dashboard, failure analysis

From a data science view, this matters because you are not only building a model app. You are building a **measurable decision system**.

## 3. Project structure

```text
enterprise_rag_support_agent/
├── .env.example
├── requirements.txt
├── run_app.py
├── README.md
├── app/
│   ├── api.py
│   ├── config.py
│   ├── db.py
│   ├── dashboard.py
│   ├── evals.py
│   ├── ingestion.py
│   ├── llm.py
│   ├── metrics.py
│   ├── parsing.py
│   ├── rag.py
│   ├── schemas.py
│   └── vector_store.py
├── scripts/
│   ├── failure_analysis.py
│   ├── load_test.py
│   └── make_demo_assets.py
└── data/
    ├── artifacts/
    ├── db/
    ├── eval/
    └── source_docs/
```

## 4. Step-by-step setup in VS Code

### Step 1: Create a virtual environment

```python
python -m venv .venv
```

### Step 2: Point VS Code to the virtual environment

In VS Code:

- open the Command Palette
- choose `Python: Select Interpreter`
- select the interpreter inside `.venv`

### Step 3: Install packages

```python
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 4: Create `.env`

Copy `.env.example` to `.env` and add your API key.

Minimum required fields:

```text
OPENAI_API_KEY=your_key_here
LLM_MODEL=openai:gpt-4.1-mini
```

### Step 5: Generate demo documents, structured data, and the eval set

```python
python scripts/make_demo_assets.py
```

This script does three things:

- writes support docs to `data/source_docs/`
- seeds SQLite tables for accounts, tickets, and orders
- creates `data/eval/eval_set.csv` with more than 200 labeled rows

### Step 6: Run the API

```python
python run_app.py
```

Then open:

```text
http://127.0.0.1:8000/docs
```

Use the Swagger UI to test every endpoint without writing shell commands.

## 5. Ingest the documents

Call `POST /ingest` with a body like this:

```json
{
  "paths": [
    "data/source_docs/product_plans.md",
    "data/source_docs/billing_faq.md",
    "data/source_docs/refund_policy.md",
    "data/source_docs/security_policy.html",
    "data/source_docs/data_retention.html",
    "data/source_docs/password_reset.md",
    "data/source_docs/sev1_runbook.md",
    "data/source_docs/rate_limit_runbook.md",
    "data/source_docs/sso_faq.md",
    "data/source_docs/integrations_faq.html",
    "data/source_docs/order_support.md"
  ]
}
```

### What `/ingest` is doing

- `parsing.py` reads each file
- HTML is converted to plain text with BeautifulSoup
- Markdown is converted to HTML and then to text
- PDFs are read with `pypdf`
- `ingestion.py` splits each document into overlapping chunks
- chunks are written to SQLite
- `vector_store.py` rebuilds the FAISS index from all chunks

## 6. Ask questions

### Simple RAG example

`POST /ask`

```json
{
  "question": "What is the refund window for the first annual purchase?",
  "mode": "simple",
  "top_k": 4
}
```

### Agentic RAG example

```json
{
  "question": "Can account A-1002 use SCIM provisioning?",
  "mode": "agentic",
  "top_k": 4
}
```

### What each mode is doing

#### Simple RAG

1. search FAISS for top chunks
2. send question + evidence to the LLM
3. force JSON output with `answer`, `citations`, and `confidence`
4. save trace to SQLite

Use this when the question is mostly document-based.

#### Agentic RAG

1. create a LangChain agent
2. give it tools:
   - `retrieve_support_docs`
   - `get_sql_schema`
   - `run_sql_query`
   - `lookup_ticket_status`
   - `lookup_order_status`
3. let the agent decide which tools to call
4. collect the tool evidence
5. run one final grounding pass to produce the answer with citations
6. save the full trace

Use this when the question needs **reasoning across multiple data sources**.

## 7. Feedback collection

Use `POST /feedback`:

```json
{
  "trace_id": "paste-trace-id-here",
  "thumb": "down",
  "issue_tags": ["hallucinated", "wrong citation"],
  "comment": "It cited the wrong policy doc"
}
```

### Why feedback matters

This is not only a UI feature. It creates a labeled error stream for:

- failure analysis
- prompt tuning
- retrieval tuning
- building future human preference datasets

## 8. Run the evaluation

Call `POST /eval`:

```json
{
  "eval_path": "data/eval/eval_set.csv",
  "modes": ["simple", "agentic"],
  "limit": null
}
```

### What `/eval` computes

For every row in the labeled eval set, the code stores:

- retrieval hit rate
- answer correctness
- citation correctness
- hallucination flag
- grounding score
- latency
- cost
- failure category

### Metric definitions

These definitions are intentionally simple and interview-friendly.

- **retrieval hit rate**: did the retrieved evidence overlap with the gold source list?
- **answer correctness**: token-level F1 plus ID/number consistency checks
- **citation correctness**: did the predicted citations match the gold sources?
- **hallucination rate**: groundedness too low or citations wrong, while the answer still sounds confident
- **p95 latency**: 95th percentile response time

This is a good first-pass evaluation stack because it is transparent and easy to explain. In a more advanced version, you could replace some heuristics with an LLM judge.

## 9. Build the dashboard

The `/eval` endpoint automatically creates a Matplotlib dashboard PNG in `data/artifacts/`.

The dashboard includes:

- retrieval hit rate
- answer correctness
- citation correctness
- grounding score
- p95 latency
- cost per answer
- failure categories

## 10. Load testing

With the server running, execute:

```python
python scripts/load_test.py
```

This script sends concurrent requests to `/ask` for both simple and agentic modes and prints average latency and p95 latency.

## 11. Failure analysis

After an eval run, execute:

```python
python scripts/failure_analysis.py
```

This writes:

- a CSV of failed eval rows
- a text summary of failure categories

Both files go to `data/artifacts/`.

## 12. What each code file is doing

### `app/config.py`
Central configuration. Paths, model name, chunk size, overlap, and cost assumptions live here.

### `app/db.py`
Creates the SQLite schema and gives helper functions for reads/writes. This file is the persistence layer.

### `app/parsing.py`
Turns PDF/HTML/Markdown into clean plain text and extracts `DOC_ID` and `TITLE` metadata.

### `app/ingestion.py`
Uses a recursive text splitter to create overlapping chunks and writes them to SQL. Then it rebuilds FAISS.

### `app/vector_store.py`
Creates sentence embeddings with `sentence-transformers`, stores them in a FAISS index, and retrieves top-k chunks.

### `app/llm.py`
Wraps the chat model. It also handles JSON parsing, token accounting, and cost estimation.

### `app/rag.py`
This is the core reasoning layer.

- `ask_simple()` runs classic retrieve-then-read RAG
- `ask_agentic()` runs a LangChain tool-using agent and then a final grounded synthesis step

### `app/metrics.py`
Holds all evaluation logic. This keeps metrics separate from model code.

### `app/evals.py`
Reads the eval CSV, runs both modes, scores predictions, saves rows, and triggers dashboard creation.

### `app/dashboard.py`
Builds the Matplotlib dashboard.

### `app/api.py`
FastAPI app with the required endpoints:

- `/ingest`
- `/ask`
- `/feedback`
- `/eval`
- `/documents`

### `scripts/make_demo_assets.py`
Creates the whole demo dataset so the project is usable immediately.

### `scripts/load_test.py`
Measures concurrent latency under a small load.

### `scripts/failure_analysis.py`
Explains where the system failed and writes out the bad rows.

## 13. How to explain the simple-vs-agentic comparison in an interview

Use this exact framing:

- **simple RAG** is faster, cheaper, and easier to control
- **agentic RAG** is better when the question needs planning or multiple data sources
- if the workload is mostly policy lookup, use simple RAG by default
- if the workload is account-specific or needs ticket/order context, route to agentic RAG

That framing shows system design maturity.

## 14. Clear limitations you can say out loud in an interview

This project is intentionally local and simple.

Current limitations:

- FAISS is rebuilt after each ingest rather than updated incrementally
- evaluation uses transparent heuristics instead of a judge model
- API tools are simulated against local SQLite-backed data instead of external production services
- no authentication layer is included

These are good limitations to mention because they show honesty and product thinking.

## 15. Best upgrade path after this version

If you want to make this closer to production later, upgrade in this order:

1. add auth and tenant isolation
2. add incremental indexing
3. add a judge model for evals
4. add reranking for retrieval
5. add human review queues for low-confidence answers
6. switch SQLite to Postgres only when scale forces it

---

This project is intentionally crisp, local, easy to explain, and strong enough for a portfolio demo.
