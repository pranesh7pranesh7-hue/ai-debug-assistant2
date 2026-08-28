# BugSense AI — LLM-Based Automated Code Debugging Assistant

**BugSense AI** is a production-grade, end-to-end AI-powered Bug Detection and Autonomous Debugging Assistant. It analyzes Python source code, detects bugs using static analysis and AST heuristics, prioritizes them by severity, explains root causes in plain English, generates unified diff patches, and runs an agentic AI loop to apply and verify fixes in an isolated sandbox.

---

## 🏛️ System Architecture

```
                                  +-----------------------+
                                  |   Vanilla JS Web UI   |
                                  |  (HTML5 / CSS3 / ES6) |
                                  +-----------+-----------+
                                              | REST APIs + JWT
                                              v
+-----------------------------------------------------------------------------------------+
|                                    FastAPI Backend                                      |
|                                                                                         |
|  +-------------------+    +--------------------+    +--------------------------------+  |
|  |   Code Upload     | -> |  Static Analysis   | -> |         Bug Detection          |  |
|  | (.py / raw / zip) |    | (AST/Pylint/Bandit)|    | (Deduper & AST Pattern Rules)  |  |
|  +-------------------+    +--------------------+    +---------------+----------------+  |
|                                                                     |                   |
|  +-------------------+    +--------------------+                    v                   |
|  |  Fix Verification | <- | Agentic Debug Loop | <- +--------------------------------+  |
|  | (Pytest / Sandbox)|    | (Plan/Act/Observe) |    |    Severity & AI Explainer     |  |
|  +---------+---------+    +--------------------+    |   (0-100 Score / Plain English)|  |
|            |                                        +--------------------------------+  |
|            v                                                                            |
|  +-------------------+    +--------------------+    +--------------------------------+  |
|  | Report Generation |    |  LLM Abstraction   |    |       PostgreSQL / SQLite      |  |
|  | (JSON & HTML/PDF) |    | (Claude/GPT/Gemini)|    |      (SQLAlchemy + Alembic)    |  |
|  +-------------------+    +--------------------+    +--------------------------------+  |
+-----------------------------------------------------------------------------------------+
```

---

## 🔄 How the Agentic Debugging Loop Works

The agentic debugging loop implements a deterministic state machine:

```
    [ START ]
        |
        v
    +---------+
    |  PLAN   |  <-- LLM analyzes bug context, root cause, and previous failures
    +----+----+
         |
         v
    +---------+
    |   ACT   |  <-- Generates & applies unified diff patch to isolated sandbox copy
    +----+----+
         |
         v
    +---------+
    | OBSERVE |  <-- Executes AST/static analyzer + test suite in sandbox subprocess
    +----+----+
         |
         v
    +---------+
    | VERIFY  |  <-- Did the target bug disappear without introducing regressions?
    +----+----+
       /     \
    [Pass]  [Fail]
      |        |
      |        v
      |    +---------+
      |    |  RETRY  | -- (Under Max Attempts? e.g. 3) --> Loops back to PLAN with feedback
      |    +----+----+
      |        | (Exhausted attempts)
      v        v
  [ Verified ] [ Marked for Manual Review ]
```

---

## 🚀 Quickstart & Setup

### Method 1: Running with Docker Compose (Recommended)

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Configure your `ANTHROPIC_API_KEY` (or OpenAI/Gemini/Ollama settings) in `.env`.
3. Start the entire stack:
   ```bash
   docker-compose up --build
   ```
4. Access the applications:
   - **Frontend UI**: [http://localhost:3000](http://localhost:3000)
   - **FastAPI Backend & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Method 2: Running Locally Without Docker

1. **Prerequisites**: Python 3.11+.
2. **Install Backend Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   ```bash
   cp ../.env.example .env
   ```
   *(Note: SQLite works out-of-the-box by setting `DATABASE_URL=sqlite:///./bugsense.db` in `.env`)*
4. **Initialize DB Migrations & Seed Demo Data**:
   ```bash
   python -m app.seed_demo
   ```
5. **Start Backend Server**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
6. **Serve Frontend**:
   ```bash
   # In a separate terminal:
   cd ../frontend
   python -m http.server 3000
   ```
7. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Running Tests

Execute the backend test suite with `pytest`:
```bash
cd backend
pytest -v
```

---

## 📚 API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register new user account |
| `POST` | `/api/auth/login` | Login and acquire JWT access token |
| `POST` | `/api/upload` | Upload `.py` file, `.zip` project, or raw code string |
| `POST` | `/api/analysis/{submission_id}/run` | Execute full static analysis + bug detection pipeline |
| `GET` | `/api/analysis/{submission_id}/status` | Check analysis status |
| `GET` | `/api/bugs/{submission_id}` | Retrieve all detected bugs and AI explanations |
| `POST` | `/api/fixes/{bug_id}/generate` | Generate AI patch and unified diff |
| `POST` | `/api/agentic/{submission_id}/start` | Launch autonomous agentic fix loop |
| `GET` | `/api/agentic/{submission_id}/status` | Poll agentic loop progress and state |
| `GET` | `/api/reports/{submission_id}` | Fetch JSON structured report |
| `GET` | `/api/reports/{submission_id}/pdf` | Download printable/PDF summary report |
| `GET` | `/api/health` | Service health check |
