# BugSense AI — Backend Engine

FastAPI-powered asynchronous backend implementing the 12 core modules of BugSense AI.

## Modules Structure

1. **`core/`**: Custom exception hierarchy, error handlers, logging, security (JWT + bcrypt).
2. **`models/`**: SQLAlchemy declarative models (User, CodeSubmission, Bug, Fix, AgenticRun, Report).
3. **`schemas/`**: Pydantic v2 schemas for all requests and responses.
4. **`modules/code_upload/`**: Syntax pre-check, size validator, raw/zip uploader.
5. **`modules/static_analysis/`**: Concrete AST parser, Pylint, Flake8, Bandit, Radon, Aggregator.
6. **`modules/bug_detection/`**: Deep AST pattern detector, deduplicator.
7. **`modules/severity/`**: Baseline rules + LLM hybrid classifier.
8. **`modules/ai_explanation/`**: Plain-English root cause explainer with signature caching.
9. **`modules/fix_recommendation/`**: Patch synthesizer and unified diff generator.
10. **`modules/agentic_debugging/`**: State machine (Plan -> Act -> Observe -> Verify -> Retry) & subprocess sandbox.
11. **`modules/fix_verification/`**: Pytest runner, regression checker, verification evaluator.
12. **`modules/report_generation/`**: Jinja2 HTML and PDF exporter.

## Quickstart

```bash
pip install -r requirements.txt
python -m app.seed_demo
uvicorn app.main:app --reload
```
