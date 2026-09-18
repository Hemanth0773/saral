# QUICK START - MILESTONE 1

**TL;DR: Get the backend running in 3 minutes**

---

## Prerequisites

- Python 3.9+ installed
- Git installed
- Postman (optional, for testing)

---

## Installation (1 minute)

```bash
cd D:/MiniProject_CSE7102/backend

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

---

## Run the Server (30 seconds)

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
2026-09-18 13:41:00 | INFO | app.main | Starting Cognitive Accessibility Simplifier v1.0.0
INFO: Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## Test It (1 minute 30 seconds)

### Option A: Browser
Open: http://localhost:8000/api/health

### Option B: Postman
- Create GET request: `http://localhost:8000/api/health`
- Click Send
- See 200 response

### Option C: Command Line
```bash
curl http://localhost:8000/api/health
```

### Option D: Swagger UI
Open: http://localhost:8000/docs

---

## Expected Response

```json
{
  "status": "ok",
  "service": "Cognitive Accessibility Simplifier",
  "version": "1.0.0",
  "timestamp": "2026-09-18T13:41:24.669Z",
  "environment": "development"
}
```

---

## Run Tests

```bash
pytest tests/ -v
```

Expected: `2 passed`

---

## That's It! ✅

Your backend is running. Next: MILESTONE 2 (Document Ingestion)

---

## Need Help?

- **Setup issues?** → Read `MILESTONE-1-SETUP.md`
- **API documentation?** → Open `http://localhost:8000/docs`
- **Full documentation?** → Read `README.md`
- **Project summary?** → Read `MILESTONE-1-SUMMARY.md`

