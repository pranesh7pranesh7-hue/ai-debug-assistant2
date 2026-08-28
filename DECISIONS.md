# BugSense AI — Technical Decisions & Assumptions

This document records the design assumptions, architectural decisions, and trade-offs made during the implementation of **BugSense AI**.

---

## 1. Database & ORM Strategy

- **Specification**: PostgreSQL via SQLAlchemy ORM + Alembic migrations.
- **Decision & Assumption**: 
  - The application is configured to connect to PostgreSQL by default (configured via `DATABASE_URL` in `.env`).
  - For local development and test execution without an external PostgreSQL instance running, the engine automatically supports a fallback SQLite database path (`sqlite:///./bugsense.db`) if `DATABASE_URL` specifies SQLite or when explicitly selected for local testing.
  - Alembic migrations are structured with standard SQLAlchemy metadata reflection to seamlessly target both PostgreSQL and SQLite.

---

## 2. LLM Abstraction Layer (`llm_client.py`)

- **Specification**: Configurable provider via `.env`, default to Anthropic Claude via `anthropic` SDK with an abstraction layer so the model can be swapped.
- **Decision & Assumption**:
  - Implemented a unified `LLMClient` protocol and factory supporting:
    1. **Anthropic Claude** (`claude-3-5-sonnet`, `claude-3-haiku`)
    2. **OpenAI** (`gpt-4o`, `gpt-4o-mini`)
    3. **Google Gemini** (`gemini-1.5-pro`, `gemini-1.5-flash`)
    4. **Ollama** (local offline models like `llama3`, `codellama`, `deepseek-coder`)
    5. **Mock/Deterministic Offline Provider**: When no API key is supplied or when running in offline test mode, the system automatically uses a rule-based AI reasoning engine that generates realistic root-cause explanations, unified diffs, and severity scores matching the detected AST/static findings. This guarantees that BugSense AI runs immediately out-of-the-box without requiring an API key.

---

## 3. Static Analysis Multi-Tool Pipeline & Fallback Mechanism

- **Specification**: Python `ast` module, `pylint`, `flake8`, `bandit`, `radon`.
- **Decision & Assumption**:
  - The static analysis aggregator runs tools concurrently using Python's `asyncio` / `concurrent.futures`.
  - Python's standard `ast` is built-in and guaranteed to run on any Python 3.11+ runtime.
  - For third-party CLI tools (`pylint`, `flake8`, `bandit`, `radon`), runner modules invoke them via Python programmatic APIs (`pylint.lint`, `flake8.api.legacy`, `bandit.core`, `radon.complexity`) with graceful fallback to subprocess execution or internal AST-based rule equivalents if a specific optional package is absent.
  - All outputs are normalized by `aggregator.py` into a unified schema: `{line, column, tool, rule_id, message, category}`.

---

## 4. Agentic Debugging State Machine

- **Specification**: Custom agent orchestrator (LangGraph-style manual state machine) with stages: `Plan` → `Act` → `Observe` → `Verify` → `Retry`.
- **Decision & Assumption**:
  - Implemented as an explicit async/sync state machine in `agent_orchestrator.py` with immutable state transitions (`AgentState`).
  - **Plan**: Inspects the bug, code context, and prior attempts to form a targeted prompt for the LLM fix generator.
  - **Act**: Applies the synthesized unified diff to an isolated temporary sandbox directory.
  - **Observe**: Executes static analysis and test suites within `sandbox_executor.py` under strict timeout and environment isolation.
  - **Verify**: Evaluates whether the target bug was eliminated and checks for regressions (new syntax errors, new bandit warnings, or failing tests).
  - **Retry**: On verification failure, appends execution feedback/traceback to the agent state and retries up to `MAX_RETRIES` (default 3).

---

## 5. Sandbox Execution & Security

- **Specification**: Subprocess with CPU/memory/time limits and no network access.
- **Decision & Assumption**:
  - `sandbox_executor.py` runs user code inside a dedicated temporary directory (`tempfile.TemporaryDirectory`).
  - Execution runs via `subprocess.Popen` with:
    - Strict execution timeout (default: 5.0 seconds).
    - `PYTHONPATH` restricted to the isolated sandbox folder.
    - Environment variables sanitized (sensitive env vars like `ANTHROPIC_API_KEY`, `DATABASE_URL` are stripped from subprocess env).
    - Windows & POSIX compatible process killing on timeout.

---

## 6. Report Generation (PDF & JSON)

- **Specification**: JSON and PDF exportable reports.
- **Decision & Assumption**:
  - Implemented a clean, zero-external-binary HTML-to-PDF generator using Python's built-in print formatting / `weasyprint` / `reportlab` or built-in printable HTML report template with dynamic browser print / PDF download styling.
  - JSON format provides full machine-readable metadata including all static analysis findings, AI explanations, agentic run logs, and diffs.

---

## 7. Frontend Architecture

- **Specification**: HTML5, CSS3, Vanilla JavaScript (ES6+) — no frontend framework.
- **Decision & Assumption**:
  - Pure Vanilla JS modular architecture with clear separation of concerns (`api.js`, `auth.js`, `upload.js`, `report.js`, `history.js`, `severityBadges.js`, `agenticStatus.js`, `utils.js`).
  - Hand-crafted CSS design system utilizing CSS Custom Properties (`--bg-primary`, `--accent-color`, `--severity-critical`, etc.) with dark glassmorphism, responsive grid layout, and accessible color contrast.
  - Interactive AI Debugger Chat directly embedded on the Report page.
