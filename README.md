# Cognitive Accessibility Simplifier for Government Documents

## Overview
An AI-powered backend system designed to simplify complex government documents by extracting text from various sources and preparing it for further processing (NLP, LLM simplification, translation, etc.).

## Problem Statement
Government documents are often complex, lengthy, and difficult for citizens to understand. This creates barriers to accessing important information and services. The system aims to simplify this process by providing automated text extraction and preparation for downstream simplification tasks.

## Proposed Solution
A modular FastAPI backend that handles:
- Document upload processing (PDF, images, text files)
- Webpage content extraction from government URLs
- OCR for scanned documents
- Text preprocessing and cleaning
- Metadata extraction and document tracking

## Main Features Implemented
- **Document Upload Endpoint**: Extract text from PDF, TXT, and image files (JPG, JPEG, PNG)
- **URL Extraction Endpoint**: Fetch and extract text from government webpage URLs
- **OCR Processing**: Extract text from scanned documents using Tesseract OCR
- **File Validation**: Security checks for file types, sizes, and malicious content
- **URL Security**: SSRF protection and validation for safe URLs
- **Text Processing**: Text cleaning, language detection, truncation, and word counting
- **Health Monitoring**: Health check endpoint for service status
- **Automatic Document ID Generation**: Unique identifiers for processed documents

## System Architecture
```
Input
↓
Document Validation
↓
Text Extraction / OCR
↓
NLP Preprocessing (Text Cleaning)
↓
Language Detection
↓
Metadata Extraction
↓
Document Tracking
↓
Output (Prepared for LLM Simplification)
```

### Component Status
- **Implemented**: Document validation, text extraction (PDF, images, text), OCR, webpage scraping, text preprocessing, language detection
- **Planned**: NLP preprocessing (beyond cleaning), LLM simplification, structured information extraction, critical information validation, readability analysis, translation, text-to-speech

## Technology Stack
- **Framework**: FastAPI 0.115.0
- **ASGI Server**: Uvicorn 0.32.0
- **Data Validation**: Pydantic 2.9.0
- **Environment**: Python-dotenv 1.0.0
- **HTTP Client**: HTTPX 0.27.0, Requests 2.32.3
- **File Handling**: Python-multipart 0.0.6
- **PDF Processing**: PyPDF 4.0.1
- **OCR**: Pytesseract 0.3.10, Pillow 11.1.0
- **Web Scraping**: BeautifulSoup4 4.12.2
- **Testing**: Pytest 8.3.3, Pytest-asyncio 0.24.0

## Project Structure
```
MiniProject_CSE7102/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/          # API endpoints (health, documents)
│   │   ├── core/                # Configuration, logging, security
│   │   ├── services/            # Business logic (document, OCR, PDF, webpage, image)
│   │   ├── schemas/             # Pydantic models
│   │   └── utils/               # Utility functions (text, file, OCR)
│   ├── tests/                   # Test suite
│   ├── postman/                 # API collection
│   └── requirements.txt         # Dependencies
└── README.md
└── PROJECT-STATUS.md
```

## Backend API
### Implemented Endpoints
- `GET /api/health` - Health check service status
- `POST /api/documents/extract` - Extract text from uploaded document (PDF, TXT, DOCX, JPG, JPEG, PNG)
- `POST /api/documents/url` - Extract text from government webpage URL
- `GET /` - Root endpoint (redirects to API documentation)
- `GET /docs` - Swagger UI API documentation
- `GET /redoc` - ReDoc API documentation

### Planned Endpoints
- NLP preprocessing endpoints
- LLM simplification endpoints
- Translation endpoints
- Text-to-speech endpoints

## Supported Input Formats
- **Documents**: PDF (.pdf), Text (.txt), Word (.docx, .doc)
- **Images**: JPEG (.jpg, .jpeg), PNG (.png)
- **Websites**: HTTP/HTTPS government URLs

## Installation
1. Clone the repository
2. Navigate to the backend directory: `cd backend`
3. Install dependencies: `pip install -r requirements.txt`
4. Configure environment variables (see `.env.example` or config.py)
5. Ensure Tesseract OCR is installed on your system

## Environment Configuration
Key environment variables (set in `.env` or config):
- `APP_NAME`: Application name (default: "Cognitive Accessibility Simplifier")
- `VERSION`: API version (default: "1.0.0")
- `ENVIRONMENT`: Deployment environment (development/production)
- `HOST`: Server host (default: "0.0.0.0")
- `PORT`: Server port (default: 8000)
- `DEBUG`: Enable debug mode (boolean)
- `MAX_FILE_SIZE_MB`: Maximum upload file size (default: 10)
- `UPLOAD_DIRECTORY`: Temporary upload directory
- `DOCUMENT_ID_PREFIX`: Prefix for generated document IDs (default: "doc")
- `CORS_ORIGINS`: Allowed CORS origins (list)

## Running the Backend
```bash
cd backend
python -m uvicorn app.main:app --reload
```
Or for production:
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Running Tests
```bash
cd backend
python -m pytest tests/ -v
```

## API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI Schema: http://localhost:8000/openapi.json

## Development Status
See [PROJECT-STATUS.md](PROJECT-STATUS.md) for detailed milestone progress and current implementation status.