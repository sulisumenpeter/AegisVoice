# AegisVoice Backend

Phase 1 implementation: Secure Backend Foundation.

## Requirements
* Python 3.9+
* SQLite for local development (production targets PostgreSQL)

## Setup
1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up the environment file:
   ```bash
   cp ../.env.example .env
   ```
4. Run database migrations:
   ```bash
   alembic upgrade head
   ```
5. Run the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Testing
Run the automated test suite with `pytest`:
```bash
pytest
```
The test suite validates the deterministic State Machine, Idempotency, Schema validation, and Audit log hash-chaining.
