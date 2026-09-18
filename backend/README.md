# Cognitive Accessibility Simplifier for Government Documents - Backend

## Overview

This is the FastAPI backend for the Cognitive Accessibility Simplifier project. The system processes complex government documents and converts them into simple, structured, cognitively accessible information using AI and NLP.

## Problem Statement

Government circulars, legal notices, welfare-scheme guidelines, and other official documents are often written in complex legal or administrative language. This makes them difficult to understand for:

- People with low literacy
- People with cognitive disabilities
- Elderly users
- People unfamiliar with legal/administrative terminology
- Users who prefer regional languages

Our backend solves this by providing APIs that:
1. Extract text from various document formats
2. Preprocess and clean the text
3. Simplify language using LLMs
4. Extract structured information (eligibility, deadlines, procedures, etc.)
5. Validate critical information is preserved
6. Analyze readability
7. Translate to regional languages
8. Generate audio narration

## Architecture

```
INPUT (PDF/URL/Text)
    ↓
DOCUMENT VALIDATION
    ↓
TEXT EXTRACTION / OCR
    ↓
NLP PREPROCESSING
    ↓
DOCUMENT ANALYSIS
    ↓
LLM SIMPLIFICATION
    ↓
STRUCTURED INFORMATION EXTRACTION
    ↓
CRITICAL INFORMATION VALIDATION
    ↓
READABILITY ANALYSIS
    ↓
ACCESSIBILITY FORMATTING
    ↓
STRUCTURED JSON RESPONSE
```

## Technology Stack

- **Backend Framework**: FastAPI + Uvicorn
- **AI/NLP**: Transformers, spaCy
- **LLM Integration**: OpenAI/Anthropic/HuggingFace (configurable)
- **Document Processing**: PyMuPDF, pdfplumber, Tesseract OCR
- **Readability Metrics**: textstat
- **Database**: PostgreSQL/MongoDB (planned for later phases)
- **Testing**: pytest
- **Language**: Python 3.9+

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── __init__.py
│   │
│   ├── api/
│   │   ├── routes/
│   │   │   ├── health.py       # Health check endpoint
│   │   │   ├── documents.py    # Document upload/extraction (Milestone 2)
│   │   │   ├── simplification.py # LLM simplification (Milestone 5)
│   │   │   ├── translation.py  # Translation service (Milestone 9)
│   │   │   └── audio.py        # TTS service (Milestone 10)
│   │   └── __init__.py
│   │
│   ├── core/
│   │   ├── config.py           # Pydantic settings from environment
│   │   ├── logging.py          # Structured logging setup
│   │   ├── security.py         # Input validation and SSRF protection
│   │   └── __init__.py
│   │
│   ├── schemas/                # Pydantic models for request/response (Milestone 2+)
│   │   ├── document.py
│   │   ├── simplification.py
│   │   ├── translation.py
│   │   └── audio.py
│   │
│   ├── services/               # Business logic and AI/NLP processing (Milestone 2+)
│   │   ├── document_service.py
│   │   ├── pdf_service.py
│   │   ├── ocr_service.py
│   │   ├── webpage_service.py
│   │   ├── nlp_service.py
│   │   ├── llm_service.py
│   │   ├── extraction_service.py
│   │   ├── validation_service.py
│   │   ├── readability_service.py
│   │   ├── translation_service.py
│   │   └── tts_service.py
│   │
│   ├── utils/                  # Helper utilities (Milestone 2+)
│   │   ├── file_utils.py
│   │   └── text_utils.py
│   │
│   └── db/                     # Database models (FUTURE - Milestone 11)
│       ├── database.py
│       └── models.py
│
├── tests/                      # Unit and integration tests (Milestone 2+)
│   ├── test_health.py
│   ├── test_documents.py
│   ├── test_simplification.py
│   └── test_readability.py
│
├── uploads/                    # Temporary storage for uploaded documents
├── generated/                  # Generated outputs (audio, etc.)
├── .env.example               # Environment variables template
├── .env                       # Local environment (DO NOT COMMIT)
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── postman/
    └── Cognitive-Accessibility-Simplifier.postman_collection.json
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git

### Step 1: Clone/Navigate to Project

```bash
cd backend
```

### Step 2: Create Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Setup Environment Variables

```bash
# Copy example to .env
cp .env.example .env

# Edit .env with your configuration
# Set LLM_API_KEY and other required variables
```

### Step 5: Create Necessary Directories

```bash
mkdir -p uploads generated
```

## Running the Backend

### Development Mode

```bash
# Option 1: Using Python directly
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at `http://localhost:8000`

### Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### MILESTONE 1 (Current)

#### Health Check
```
GET /api/health
```

Returns the status of the API.

**Response:**
```json
{
  "status": "ok",
  "service": "Cognitive Accessibility Simplifier",
  "version": "1.0.0",
  "timestamp": "2026-09-18T13:39:43.580Z",
  "environment": "development"
}
```

### MILESTONE 2 (Next)

- `POST /api/documents/extract` - Extract text from uploaded PDF/document
- `POST /api/documents/url` - Extract text from government webpage

### MILESTONE 5+

- `POST /api/documents/simplify` - Extract + Simplify + Analyze + Validate
- `POST /api/translate` - Translate simplified text
- `POST /api/tts` - Generate audio from text

## Testing with Postman

### Import Postman Collection

1. Open Postman
2. Click "Import" (top left)
3. Select the file: `postman/Cognitive-Accessibility-Simplifier.postman_collection.json`
4. All endpoints will be available

### Test Health Endpoint

1. In Postman, select the "Health Check" request
2. Click "Send"
3. You should see a 200 response with the health status

## Testing with Python

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_health.py -v

# Run with coverage
pytest --cov=app tests/
```

## Configuration

Configuration is managed through environment variables in `.env`. See `.env.example` for all available options.

Key settings:
- `ENVIRONMENT`: development/production
- `PORT`: API port (default 8000)
- `MAX_FILE_SIZE_MB`: Max upload size (default 10 MB)
- `LLM_PROVIDER`: Which LLM to use (openai/anthropic/huggingface)
- `LLM_API_KEY`: API key for selected LLM

## Development Phases

**MILESTONE 1 (COMPLETE)**: Project Foundation
- FastAPI setup
- Configuration
- Logging
- Health endpoint
- Basic error handling

**MILESTONE 2**: Document Ingestion
- PDF text extraction
- URL webpage extraction
- File validation
- Language detection

**MILESTONE 3**: OCR
- Tesseract OCR setup
- Scanned document processing

**MILESTONE 4**: NLP Preprocessing
- Text cleaning
- Sentence segmentation
- Tokenization

**MILESTONE 5**: LLM Simplification
- LLM integration
- Prompt engineering
- Iterative simplification

**MILESTONE 6**: Information Extraction
- Structured data extraction
- Key information identification

**MILESTONE 7**: Critical Information Validation
- Fact checking
- Important value preservation

**MILESTONE 8**: Readability Analysis
- Grade level calculation
- Readability metrics

**MILESTONE 9**: Translation
- Multilingual support
- Regional language translation

**MILESTONE 10**: Text-to-Speech
- Audio generation
- Multilingual audio support

**MILESTONE 11**: Database & History
- User management
- Processing history
- Results storage

**MILESTONE 12**: Testing & Documentation
- Comprehensive testing
- Security review
- Performance optimization

## Known Limitations

- MILESTONE 1 only implements health endpoint
- No document processing yet (MILESTONE 2+)
- No LLM integration yet (MILESTONE 5+)
- No database support yet (MILESTONE 11+)
- No authentication yet (planned)

## Error Handling

All errors follow a consistent format:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

## Security

- Input validation on all requests
- File type and size validation
- SSRF protection for URL requests
- No sensitive data logged
- Environment variables for secrets
- CORS configured

## Production Considerations

For production deployment:
1. Set `ENVIRONMENT=production` and `DEBUG=false`
2. Configure `CORS_ORIGINS` appropriately
3. Use proper LLM API keys
4. Set up monitoring and alerting
5. Use a proper ASGI server (Gunicorn with Uvicorn workers)
6. Deploy behind a reverse proxy (Nginx)
7. Configure rate limiting
8. Set up proper logging and centralized log aggregation
9. Use environment-specific configurations

Example production command:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Support

For issues or questions, refer to the project documentation or contact the development team.

## License

This project is developed as an academic mini project at CSE 7th Semester.
