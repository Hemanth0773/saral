# Cognitive Accessibility Simplifier for Government Documents

## Overview
An AI-powered system designed to simplify complex government documents for citizens. The system provides a complete pipeline for document processing: text extraction from PDFs, images, and web pages, OCR for scanned documents, NLP preprocessing, LLM-based text simplification with fact preservation, structured information extraction, cross-document fact validation, readability analysis, translation to regional languages, and text-to-speech generation.

## Problem Statement
Government documents are often complex, lengthy, and difficult for citizens to understand. This creates barriers to accessing important information and services. The system aims to bridge this gap by providing automated text extraction, NLP preprocessing, LLM-based simplification, structured information extraction, fact validation, readability analysis, translation, and text-to-speech in a single pipeline.

## Proposed Solution
A modular architecture with a React frontend and FastAPI backend:

- **Frontend**: React 19 single-page application with responsive UI for document processing
- **Backend**: FastAPI backend handling document processing, NLP, LLM simplification, translation, and TTS
- **Document upload processing** (PDF, images, text files)
- **Webpage content extraction** from government URLs (SSRF-protected)
- **OCR for scanned documents** (Tesseract)
- **NLP preprocessing** and linguistic analysis (spaCy)
- **LLM-based text simplification** with fact preservation validation (Gemini / OpenAI / Groq / OpenRouter / Mock)
- **Structured information extraction** (deadlines, eligibility, amounts, etc.)
- **Cross-document fact validation** across original, simplified, and structured text
- **Readability analysis** (Flesch Reading Ease, Flesch-Kincaid Grade Level)
- **Translation** between English and Kannada (NLLB-200 model)
- **Text-to-speech** in English and Kannada (edge-tts / Microsoft Edge TTS)
- **Document processing history tracking** (PostgreSQL)

## System Architecture

![System Architecture](docs/system-architecture.svg)

```
                        ┌─────────────────────────────────┐
                        │   React Frontend (Client)        │
                        │   React 19 | Vite | Tailwind    │
                        └──────────────┬──────────────────┘
                                       │  HTTP/HTTPS REST/JSON
                        ┌──────────────▼──────────────────┐
                        │   FastAPI API Gateway (Server)  │
                        │   FastAPI | Uvicorn | OpenAPI   │
                        └──────────────┬──────────────────┘
                                       │  Internal calls
                   ┌───────────────────┼──────────────────────────────────┐
                   │                   │                                  │
        ┌──────────▼────────┐  ┌───────▼────────┐  ┌──────────────────┐  ┌───────────────┐
        │  LLM Simplification│  │ Fact Extraction│  │ Translation        │  │ TTS Service  │
        │  Gemini/OpenAI     │  │ spaCy NER      │  │ NLLB-200           │  │ edge-tts      │
        │  Groq/OpenRouter   │  │ pattern match  │  │ transformers       │  │ Microsoft     │
        └───────────────────┘  └───────┬────────┘  └────────┬───────────┘  └───────┬──────┘
                                       │                    │                       │
                                       │          ┌─────────▼──────────┐            │
                                       │          │ Fact Validation     │            │
                                       │          │ Cross-doc deter-    │            │
                                       │          │ minimistic check     │            │
                                       │          └────────────────────┘            │
                                       │                                           │
                        ┌──────────────▼──────────────────┐     ┌────────────────▼────────┐
                        │   Document Processing Services   │     │   File Storage            │
                        │   PDF, Web, OCR, Image           │     │   uploads/ + generated/  │
                        └──────────────┬──────────────────┘     └─────────────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │   PostgreSQL Database            │
                        │   document_history table (18 cols)│
                        │   SQLAlchemy 2.x | psycopg 3.x   │
                        └──────────────┬──────────────────┘
                                       │
                        ┌──────────────▼──────────────────┐
                        │   External API Services          │
                        │   Hugging Face (model weights)   │
                        │   Microsoft Edge TTS (voices)    │
                        │   Tesseract OCR engine           │
                        └──────────────────────────────────┘
```

**Pipeline flow:**
```
Input → Document Validation (file type, size, path traversal)
  ↓
Text Extraction / OCR (PDF, images, URLs)
  ↓
NLP Preprocessing (tokenization, NER, POS, key phrases)
  ↓
LLM Simplification (Gemini/OpenAI/Groq/OpenRouter/Mock)
  ↓
Structured Information Extraction (dates, money, ages, etc.)
  ↓
Fact Validation (cross-document consistency check)
  ↓
Readability Analysis (Flesch metrics comparison)
  ↓
Translation (English ↔ Kannada, NLLB model)
  ↓
Text-to-Speech (edge-tts, en-US-AriaNeural / kn-IN-GaganNeural)
  ↓
Document History Tracking (PostgreSQL)
  ↓
Output (simplified, accessible content)
```

## Milestone Status
- **M1 - Foundation**: Health endpoint, configuration, logging, security utilities
- **M2 - Document Ingestion**: PDF/text/image extraction, URL extraction with SSRF protection
- **M3 - OCR**: Tesseract OCR integration, image enhancement, EXIF rotation
- **M4 - NLP Preprocessing**: spaCy integration, NER, POS tagging, key phrase extraction
- **M5 - LLM Simplification**: Gemini/OpenAI/Groq/OpenRouter/Mock providers, fact preservation validation
- **M6 - Structured Information Extraction**: 14 categories (dates, money, ages, documents, contact, etc.)
- **M7 - Advanced Fact Validation**: Cross-document validation across 12 fact types
- **M8 - Readability Analysis**: Flesch Reading Ease, Flesch-Kincaid Grade Level
- **M9 - Translation**: NLLB-200 model, English ↔ Kannada
- **M10 - Text-to-Speech**: edge-tts (Microsoft Edge TTS), English and Kannada voices
- **M11 - Database / History**: PostgreSQL, SQLAlchemy, paginated history API
- **M12 - Final Testing, Security, Performance & Documentation**: Complete

## Technology Stack

### Backend (Python 3.11+)
- **Framework**: FastAPI 0.115.0
- **ASGI Server**: Uvicorn 0.32.0
- **Data Validation**: Pydantic 2.9.0, pydantic-settings 2.5.0
- **Environment**: python-dotenv 1.0.0
- **HTTP Client**: HTTPX 0.27.0, Requests 2.32.3
- **File Handling**: python-multipart 0.0.6
- **PDF Processing**: PyPDF 4.0.1
- **OCR**: Pytesseract 0.3.10, Pillow 11.1.0
- **Web Scraping**: BeautifulSoup4 4.12.2
- **NLP**: spaCy 3.8.16
- **Translation**: Transformers 4.49.0, torch 2.5.0, sentencepiece 0.2.0 (NLLB-200 model)
- **TTS**: edge-tts 7.2.8
- **Database**: SQLAlchemy 2.0.36, psycopg[binary] 3.2.13 (PostgreSQL)
- **Testing**: pytest 8.3.3, pytest-asyncio 0.24.0, pytest-cov

### Frontend (React 19+)
- **Framework**: React 19.2.8 + React DOM
- **Build Tool**: Vite 8.3.0
- **Language**: TypeScript 6.0.2
- **Styling**: Tailwind CSS 3.4.19, PostCSS 8.5.28, Autoprefixer 10.6.1
- **Linting**: Oxlint 1.81.0

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
│   │   │       ├── tts.py
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
│   │   │   ├── validation_service.py
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
├── docs/
│   ├── system-architecture.svg
│   └── system-architecture.png
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── index.css
│   │   └── App.css
│   ├── public/
│   │   ├── favicon.svg
│   │   ├── hero-illustration.svg
│   │   └── icons.svg
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.cjs
│   ├── tsconfig.json
│   └── postcss.config.cjs
├── README.md
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
- `POST /api/documents/simplify` - Simplify text using LLM (Gemini/OpenAI/Groq/OpenRouter/Mock)
- `POST /api/documents/simplify/validate` - Validate fact preservation

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

## Frontend
The React frontend provides a responsive single-page application for interacting with the backend API.

### Frontend Features
- Document upload and text extraction interface
- Text simplification with before/after comparison
- Translation between English and Kannada
- Text-to-speech audio playback
- Responsive design with Tailwind CSS

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Frontend Build
```bash
cd frontend
npm run build
```

### Frontend Linting
```bash
cd frontend
npm run lint
```

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
- **Total Tests**: 338
- **Passing**: 338
- **Failing**: 0
- **Test Coverage**: ~70% across all modules

**Live API Testing (M12 Verification):**
8 of 16 endpoints verified with live HTTP requests:
- `GET /api/health` ✓
- `POST /api/translate` (en→kn) ✓
- `POST /api/tts` (English) ✓
- `GET /api/history` ✓
- `POST /api/documents/simplify` ✓ (returns 429 - quota exhausted, error handling works)
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

### Backend
1. Clone the repository
2. Navigate to the backend directory: `cd backend`
3. Install dependencies: `pip install -r requirements.txt`
4. Download spaCy English model: `python -m spacy download en_core_web_sm`
5. Configure environment variables: copy `.env.example` to `.env` and fill in values
6. Ensure Tesseract OCR is installed on your system (for M3 OCR features)
7. Ensure PostgreSQL is running (for M11 history tracking; app starts without it)

### Frontend
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Configure API URL if needed (edit `src/services/api.ts`)

## Environment Configuration
Key environment variables (set in `.env`):
- `APP_NAME`: Application name
- `VERSION`: API version
- `ENVIRONMENT`: Deployment environment (development/production)
- `DEBUG`: Enable debug mode (boolean)
- `HOST` / `PORT`: Server host and port
- `MAX_FILE_SIZE_MB`: Maximum upload file size (default: 10)
- `CORS_ORIGINS`: Allowed CORS origins (JSON list)
- `LLM_PROVIDER`: Provider for simplification (gemini, openai, groq, openrouter, mock, auto)
- `LLM_API_KEY`: API key for the chosen LLM provider (backward compatibility)
- `LLM_MODEL`: Default LLM model (default: gpt-3.5-turbo)
- `GEMINI_API_KEY`: Google Gemini API key
- `GEMINI_MODEL`: Gemini model name (default: gemini-pro)
- `GROQ_API_KEY`: Groq API key
- `GROQ_MODEL`: Groq model name
- `OPENROUTER_API_KEY`: OpenRouter API key
- `OPENROUTER_MODEL`: OpenRouter model name
- `DATABASE_URL`: PostgreSQL connection string
- `USE_DATABASE`: Enable/disable database history tracking (default: true)
- `TRANSLATION_PROVIDER`: Translation model provider (nllb)
- `TRANSLATION_API_KEY`: Translation service API key (if required)
- `TTS_PROVIDER`: TTS provider (google)
- `TTS_API_KEY`: TTS service API key (if required)
- `LOG_LEVEL`: Logging level (default: INFO)

## Running the Application

### Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Or for production:
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

### Frontend Build for Production
```bash
cd frontend
npm run build
```

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json
- Postman Collection: `backend/postman/Cognitive-Accessibility-Simplifier.postman_collection.json`
