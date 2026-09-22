# Cognitive Accessibility Simplifier for Government Documents

## Overview
An AI-powered backend system designed to simplify complex government documents for citizens. The system extracts text from various sources (PDFs, images, web pages), preprocesses it, simplifies it using LLMs, translates to regional languages, generates speech, and validates fact preservation throughout the pipeline.

## Problem Statement
Government documents are often complex, lengthy, and difficult for citizens to understand. This creates barriers to accessing important information and services. The system aims to simplify this process by providing automated text extraction, NLP preprocessing, LLM-based simplification, structured information extraction, fact validation, readability analysis, translation, and text-to-speech in a single pipeline.

## Proposed Solution
A modular FastAPI backend that handles:

- Document upload processing (PDF, images, text files)
- Webpage content extraction from government URLs
- OCR for scanned documents
- NLP preprocessing and linguistic analysis
- LLM-based text simplification with fact preservation
- Structured information extraction (deadlines, eligibility, amounts, etc.)
- Cross-document fact validation across original, simplified, and structured text
- Readability analysis (Flesch Reading Ease, Flesch-Kincaid Grade Level)
- Translation between English and Kannada (NLLB model)
- Text-to-speech in English and Kannada (Edge TTS)
- Document processing history tracking (PostgreSQL)

## System Architecture
```
Input
  ↓
Document Validation (file type, size, path traversal)
  ↓
Text Extraction / OCR (PDF, images, URLs)
  ↓
NLP Preprocessing (tokenization, NER, POS, key phrases)
  ↓
Language Detection (English / Kannada)
  ↓
LLM Simplification (Gemini / OpenAI / Mock provider)
  ↓
Structured Information Extraction (dates, money, ages, etc.)
  ↓
Fact Validation (cross-document consistency check)
  ↓
Readability Analysis (Flesch metrics comparison)
  ↓
Translation (English ↔ Kannada, NLLB model)
  ↓
Text-to-Speech (Edge TTS, en-US-AriaNeural / kn-IN-GaganNeural)
  ↓
Document History Tracking (PostgreSQL)
  ↓
Output (simplified, accessible content)
```

## Milestone Status
- **M1 - Foundation**: Health endpoint, configuration, logging, security utilities ✓
- **M2 - Document Ingestion**: PDF/text/image extraction, URL extraction with SSRF protection ✓
- **M3 - OCR**: Tesseract OCR integration, image enhancement, EXIF rotation ✓
- **M4 - NLP Preprocessing**: spaCy integration, NER, POS tagging, key phrase extraction ✓
- **M5 - LLM Simplification**: Gemini/OpenAI/Mock providers, fact preservation validation ✓
- **M6 - Structured Information Extraction**: 14 categories (dates, money, ages, documents, contact, etc.) ✓
- **M7 - Advanced Fact Validation**: Cross-document validation across 12 fact types ✓
- **M8 - Readability Analysis**: Flesch Reading Ease, Flesch-Kincaid Grade Level ✓
- **M9 - Translation**: NLLB model, English ↔ Kannada ✓
- **M10 - Text-to-Speech**: Edge TTS, English and Kannada voices ✓
- **M11 - Database / History**: PostgreSQL, SQLAlchemy, paginated history API ✓
- **M12 - Final Testing, Security, Performance & Documentation**: Complete ✓

## Technology Stack
- **Framework**: FastAPI 0.115.0
- **ASGI Server**: Uvicorn 0.32.0
- **Data Validation**: Pydantic 2.9.0, pydantic-settings
- **Environment**: python-dotenv 1.0.0
- **HTTP Client**: HTTPX 0.27.0, Requests 2.32.3
- **File Handling**: Python-multipart 0.0.6
- **PDF Processing**: PyPDF 4.0.1
- **OCR**: Pytesseract 0.3.10, Pillow 11.1.0
- **Web Scraping**: BeautifulSoup4 4.12.2
- **NLP**: spaCy 3.7.x, scikit-learn (TF-IDF)
- **Translation**: Transformers, torch, sentencepiece (NLLB-200 model)
- **TTS**: edge-tts
- **Database**: SQLAlchemy 2.x, psycopg[binary] (PostgreSQL)
- **Testing**: pytest 8.3.3, pytest-asyncio 0.24.0, pytest-cov

## Project Structure
```
MiniProject_CSE7102/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       ├── documents.py
│   │   │       ├── simplification.py
│   │   │       ├── extraction.py
│   │   │       ├── validation.py
│   │   │       ├── readability.py
│   │   │       ├── translation.py
│   │   │       └── tts.py
│   │   │       └── history.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── database.py
│   │   │   └── models.py
│   │   ├── schemas/
│   │   │   ├── document.py
│   │   │   ├── nlp.py
│   │   │   ├── simplification.py
│   │   │   ├── extraction.py
│   │   │   ├── validation.py
│   │   │   ├── readability.py
│   │   │   ├── translation.py
│   │   │   ├── tts.py
│   │   │   └── history.py
│   │   ├── services/
│   │   │   ├── document_service.py
│   │   │   ├── pdf_service.py
│   │   │   ├── webpage_service.py
│   │   │   ├── ocr_service.py
│   │   │   ├── image_service.py
│   │   │   ├── nlp_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── extraction_service.py
│   │   │   ├── advanced_validation_service.py
│   │   │   ├── readability_service.py
│   │   │   ├── translation_service.py
│   │   │   ├── tts_service.py
│   │   │   └── history_service.py
│   │   └── utils/
│   │       ├── file_utils.py
│   │       ├── ocr_utils.py
│   │       └── text_utils.py
│   ├── tests/
│   │   ├── test_health.py
│   │   ├── test_documents.py
│   │   ├── test_ocr.py
│   │   ├── test_nlp.py
│   │   ├── test_simplification.py
│   │   ├── test_extraction.py
│   │   ├── test_validation.py
│   │   ├── test_readability.py
│   │   ├── test_translation.py
│   │   ├── test_tts.py
│   │   └── test_history.py
│   ├── postman/
│   │   └── Cognitive-Accessibility-Simplifier.postman_collection.json
│   ├── .env.example
│   ├── .gitignore
│   └── requirements.txt
└── README.md
└── PROJECT-STATUS.md
```

## Backend API

### Implemented Endpoints (16 total)

#### Health & Status
- `GET /` - Root endpoint (service info, docs links)
- `GET /api/health` - Health check service status

#### Document Ingestion (M2)
- `POST /api/documents/extract` - Extract text from uploaded PDF/image/TXT
- `POST /api/documents/url` - Extract text from government webpage URL

#### NLP Preprocessing (M4)
- `POST /api/documents/preprocess` - Linguistic analysis (sentences, entities, POS, key phrases)

#### LLM Simplification (M5)
- `POST /api/documents/simplify` - Simplify text using LLM (Gemini/OpenAI/Mock)
- `POST /api/documents/simplify/validate` - Validate fact preservation (query param or JSON)

#### Structured Information Extraction (M6)
- `POST /api/documents/extract-info` - Extract structured data (14 categories)

#### Advanced Fact Validation (M7)
- `POST /api/documents/validate` - Cross-document validation (12 fact types)

#### Readability Analysis (M8)
- `POST /api/documents/readability` - Flesch Reading Ease and Grade Level comparison

#### Translation (M9)
- `POST /api/translate` - Translate text between English and Kannada
- `POST /api/translate/batch` - Batch translate multiple texts

#### Text-to-Speech (M10)
- `POST /api/tts` - Generate speech audio from text
- `GET /api/media/audio/{filename}` - Serve generated audio file

#### History (M11)
- `GET /api/history` - List document processing history (paginated)
- `GET /api/history/{document_id}` - Get history for a specific document

### Documentation
- `GET /docs` - Swagger UI
- `GET /openapi.json` - OpenAPI schema
- `GET /redoc` - ReDoc

## Supported Input Formats
- **Documents**: PDF (.pdf), Text (.txt), Word (.docx, .doc)
- **Images**: JPEG (.jpg, .jpeg), PNG (.png)
- **Websites**: HTTP/HTTPS URLs

## Supported Languages
- **English** (`en`): Full support for all features
- **Kannada** (`kn`): Full support for translation and TTS

## Security Features
- **File Upload Validation**: Extension whitelist (pdf, txt, docx, doc, jpg, jpeg, png), size limit (default 10MB), empty file detection, filename sanitization
- **SSRF Protection**: URL validation blocks `file://` scheme, non-HTTP schemes, localhost, loopback, RFC 1918 private IP ranges (10.x, 172.16-31.x, 192.168.x), and link-local addresses (including AWS metadata 169.254.169.254)
- **Path Traversal Prevention**: Filename sanitization strips `../`, `..\\`, and dangerous characters
- **Error Response Masking**: Database credentials and internal connection strings are never exposed in error responses
- **Secrets Management**: API keys loaded from `.env` file (gitignored); never hardcoded in source

## Testing
```bash
cd backend
python -m pytest tests/ -v
```
- **Total Tests**: 337 (335 original + 2 new SSRF security tests)
- **Passing**: 337
- **Failing**: 0
- **Test Coverage**: 70% across all modules

**Live API Testing (M12 Verification):**
8 of 16 endpoints verified with live HTTP requests:
- `GET /api/health` ✓
- `POST /api/translate` (en→kn) ✓
- `POST /api/tts` (English) ✓
- `GET /api/history` ✓
- `POST /api/documents/simplify` ✓ (returns 429 - quota exhausted)
- `POST /api/documents/extract-info` ✓
- `POST /api/documents/validate` ✓
- `POST /api/documents/readability` ✓

Remaining 8 endpoints implemented but not live-tested in M12:
- `GET /` (root), `POST /api/documents/extract`, `POST /api/documents/preprocess`, `POST /api/documents/simplify/validate`, `POST /api/documents/url`, `GET /api/history/{document_id}`, `GET /api/media/audio/{filename}`, `POST /api/translate/batch`

Run with coverage:
```bash
python -m pytest tests/ --cov=app --cov-report=term-missing
```

## Installation
1. Clone the repository
2. Navigate to the backend directory: `cd backend`
3. Install dependencies: `pip install -r requirements.txt`
4. Configure environment variables: copy `.env.example` to `.env` and fill in values
5. Ensure Tesseract OCR is installed on your system (for M3 OCR features)
6. Ensure PostgreSQL is running (for M11 history tracking; app starts without it)

## Environment Configuration
Key environment variables (set in `.env`):
- `APP_NAME`: Application name
- `VERSION`: API version
- `ENVIRONMENT`: Deployment environment (development/production)
- `DEBUG`: Enable debug mode (boolean)
- `HOST` / `PORT`: Server host and port
- `MAX_FILE_SIZE_MB`: Maximum upload file size (default: 10)
- `CORS_ORIGINS`: Allowed CORS origins (JSON list)
- `LLM_PROVIDER`: Provider for simplification (gemini, openai, anthropic, mock)
- `LLM_API_KEY`: API key for the chosen LLM provider
- `DATABASE_URL`: PostgreSQL connection string
- `USE_DATABASE`: Enable/disable database history tracking (default: true)
- `TRANSLATION_PROVIDER`: Translation model provider (nllb)
- `TTS_PROVIDER`: TTS provider (google)
- `LOG_LEVEL`: Logging level (default: INFO)

## Running the Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Or for production:
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json
- Postman Collection: `backend/postman/Cognitive-Accessibility-Simplifier.postman_collection.json`
