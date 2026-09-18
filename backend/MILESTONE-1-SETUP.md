# MILESTONE 1: Project Foundation - Setup Guide

## What Was Built

This is **MILESTONE 1** of the backend - the complete project foundation and infrastructure.

### Files Created

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── health.py       # Health check endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic settings from environment
│   │   ├── logging.py          # Structured logging
│   │   └── security.py         # Input validation & SSRF protection
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_health.py          # Health endpoint tests
├── postman/
│   └── Cognitive-Accessibility-Simplifier.postman_collection.json
├── uploads/                    # Directory for uploaded documents (created on first run)
├── generated/                  # Directory for generated outputs
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
└── README.md                  # Full documentation
```

### Architecture Overview

**Why this structure?**

1. **app/main.py** - Single entry point for the FastAPI application
2. **app/core/** - Cross-cutting concerns (config, logging, security)
3. **app/api/routes/** - HTTP endpoints (will grow in future milestones)
4. **app/schemas/** - Request/response validation (will be added in Milestone 2)
5. **app/services/** - Business logic & AI/NLP (will be added in Milestone 2+)
6. **tests/** - Unit and integration tests (will grow with each milestone)

This structure is:
- **Modular**: Each component has a single responsibility
- **Testable**: Services can be tested independently
- **Scalable**: Easy to add new endpoints and features
- **Maintainable**: Clear separation of concerns
- **Professional**: Follows FastAPI best practices

---

## MILESTONE 1 SETUP INSTRUCTIONS

### Step 1: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**What gets installed:**
- FastAPI 0.104.1 - The web framework
- Uvicorn 0.24.0 - ASGI server
- Pydantic 2.5.0 - Data validation
- pytest 7.4.3 - Testing framework
- And other utilities (see requirements.txt)

### Step 2: Create Environment File

```bash
# Copy the example
cp .env.example .env
```

The `.env` file is created with default values. You can modify it locally but DO NOT commit it to git.

### Step 3: Create Upload/Generated Directories

These are created automatically on first run, but you can create them manually:

```bash
mkdir -p uploads generated
```

### Step 4: Verify Installation

```bash
# Check Python version (should be 3.9+)
python --version

# Check installed packages
pip list | grep -E "fastapi|uvicorn|pydantic|pytest"
```

---

## RUNNING THE BACKEND

### Start the Development Server

```bash
# From the backend directory
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
2026-09-18 13:40:00 | INFO     | app.main | Starting Cognitive Accessibility Simplifier v1.0.0
2026-09-18 13:40:00 | INFO     | app.main | Environment: development
2026-09-18 13:40:00 | INFO     | Uvicorn running on http://0.0.0.0:8000
```

### Access the API

1. **Health Check**: http://localhost:8000/api/health
2. **Swagger UI**: http://localhost:8000/docs
3. **ReDoc**: http://localhost:8000/redoc

Open any of these in your browser to verify it's working.

---

## TESTING WITH POSTMAN

### Option 1: Import Postman Collection

1. Open Postman
2. Click **Import** (top left)
3. Click **Upload Files**
4. Navigate to: `backend/postman/Cognitive-Accessibility-Simplifier.postman_collection.json`
5. Click **Import**

All endpoints will be available in the left sidebar.

### Option 2: Manual Test

1. Open Postman
2. Create a new GET request
3. URL: `http://localhost:8000/api/health`
4. Click **Send**

You should see:
```json
{
  "status": "ok",
  "service": "Cognitive Accessibility Simplifier",
  "version": "1.0.0",
  "timestamp": "2026-09-18T13:40:23.680Z",
  "environment": "development"
}
```

---

## TESTING WITH PYTEST

### Run All Tests

```bash
pytest
```

### Run Specific Test

```bash
pytest tests/test_health.py -v
```

### Run with Coverage

```bash
pytest --cov=app tests/
```

Expected output:
```
tests/test_health.py::test_health_check PASSED
tests/test_health.py::test_root_endpoint PASSED

====== 2 passed in 0.05s ======
```

---

## TESTING WITH CURL (Alternative to Postman)

If you don't have Postman, use curl:

```bash
# Health check
curl http://localhost:8000/api/health

# Should return:
# {"status":"ok","service":"Cognitive Accessibility Simplifier","version":"1.0.0","timestamp":"2026-09-18T13:40:23.680Z","environment":"development"}
```

---

## FILE EXPLANATIONS

### app/main.py
- Entry point for the FastAPI application
- Configures middleware (CORS)
- Registers routes
- Sets up lifespan events (startup/shutdown)
- NOT where you add business logic

### app/core/config.py
- **Why**: Configuration should be centralized and environment-driven
- **How**: Uses Pydantic Settings to load from .env
- **What**: All configuration values in one place (no hardcoding)
- **Example**: `settings.MAX_FILE_SIZE_MB`, `settings.LLM_API_KEY`

### app/core/logging.py
- **Why**: Structured, consistent logging across the app
- **How**: Configures Python's logging module
- **What**: Every module can do: `logger = get_logger(__name__)`
- **Example**: Logs include timestamp, level, module name, message

### app/core/security.py
- **Why**: Security checks should be centralized
- **How**: Functions for validating files, URLs, etc.
- **What**: Prevents attacks like SSRF, file traversal, malicious uploads
- **Example**: `validate_file_upload()` checks file type and size

### app/api/routes/health.py
- **Why**: Endpoints should be organized by feature
- **How**: Each route file is independent
- **What**: `/api/health` endpoint using Pydantic model for response
- **Example**: Response is validated by `HealthResponse` model

### tests/test_health.py
- **Why**: Tests ensure endpoints work and validate responses
- **How**: Uses FastAPI's TestClient to test without running a server
- **What**: Tests for happy path and edge cases
- **Example**: `test_health_check()` verifies response has correct fields

---

## HOW FILES COMMUNICATE

```
REQUEST
  ↓
FastAPI (main.py)
  ↓
Route Handler (health.py)
  ↓
Pydantic Schema (HealthResponse)
  ↓
RESPONSE (JSON)
```

For future endpoints:

```
REQUEST (file upload)
  ↓
FastAPI (main.py)
  ↓
Route Handler (documents.py)
  ↓
Security Validation (security.py)
  ↓
Service Layer (document_service.py)
  ↓
AI/NLP Processing
  ↓
Pydantic Response Model
  ↓
RESPONSE (JSON)
```

---

## NEXT MILESTONE (MILESTONE 2)

When you're ready to proceed, MILESTONE 2 will add:

- **Schemas**: Pydantic models for document requests/responses
- **PDF Text Extraction**: Using PyMuPDF and pdfplumber
- **URL Extraction**: Using BeautifulSoup
- **Endpoints**:
  - `POST /api/documents/extract` - Extract text from PDF
  - `POST /api/documents/url` - Extract text from webpage
- **Tests**: Tests for document extraction

The same modular structure will continue. We'll add a new `app/services/pdf_service.py` and `app/schemas/document.py`, for example.

---

## TROUBLESHOOTING

### Issue: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: `Address already in use` on port 8000

**Solution**: Change port or kill existing process
```bash
# Option 1: Use different port
uvicorn app.main:app --reload --port 8001

# Option 2: Find and kill existing process
# On Windows: netstat -ano | findstr :8000
# On macOS/Linux: lsof -i :8000
```

### Issue: Tests fail with `ModuleNotFoundError`

**Solution**: Make sure you're running pytest from the backend directory
```bash
cd backend
pytest
```

### Issue: `.env` file not being read

**Solution**: Verify the file exists and is named exactly `.env`
```bash
ls -la .env
```

---

## PRODUCTION CONSIDERATIONS

For production deployment (not needed for college project now):

1. Set `ENVIRONMENT=production` in `.env`
2. Set `DEBUG=false`
3. Use a production ASGI server (Gunicorn)
4. Deploy behind a reverse proxy (Nginx)
5. Configure proper CORS origins
6. Use environment-specific API keys
7. Set up monitoring and centralized logging

Example production startup:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## NEXT STEPS

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Create `.env` file: `cp .env.example .env`
3. ✅ Start server: `python -m uvicorn app.main:app --reload`
4. ✅ Test health endpoint: `curl http://localhost:8000/api/health`
5. ✅ Test with Postman or Swagger UI

Once MILESTONE 1 is working, we'll move to **MILESTONE 2: Document Ingestion** which will add PDF extraction and URL webpage extraction.

---

## Questions?

Refer to:
- FastAPI docs: https://fastapi.tiangolo.com/
- Pydantic docs: https://docs.pydantic.dev/
- Uvicorn docs: https://www.uvicorn.org/
