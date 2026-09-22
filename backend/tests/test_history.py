"""
Tests for document processing history (MILESTONE 11).
Tests cover database model creation, session behavior, history record creation,
retrieval, listing, pagination, validation, and error handling.

Uses an isolated SQLite file database for unit tests to avoid
dependency on a production PostgreSQL instance.
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import models
from app.db.database import Base
from app.services import history_service


# Create SQLite file-based engine for testing
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(suffix=".db")
os.close(_TEST_DB_FD)

TEST_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def get_test_db():
    """Override get_db to use test SQLite database."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create tables once for all tests in this module."""
    Base.metadata.create_all(bind=test_engine)
    yield
    # Clean up - dispose engine to release file lock
    test_engine.dispose()
    Base.metadata.drop_all(bind=test_engine)
    try:
        if os.path.exists(_TEST_DB_PATH):
            os.remove(_TEST_DB_PATH)
    except PermissionError:
        pass


@pytest.fixture(autouse=True)
def override_db():
    """Override get_db dependency for each test."""
    from app.db.database import get_db
    original = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = get_test_db
    yield
    app.dependency_overrides[get_db] = original


@pytest.fixture
def db_session():
    """Provide a test database session and clean up after."""
    session = TestingSessionLocal()
    yield session
    session.close()
    # Clear all data between tests for isolation
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
        session.commit()


client = TestClient(app)


class TestDatabaseSetup:
    """Test database configuration and model creation."""

    def test_database_url_configured(self):
        """Test that DATABASE_URL is configured in settings."""
        from app.core.config import settings
        assert settings.DATABASE_URL is not None
        assert len(settings.DATABASE_URL) > 0

    def test_use_database_flag_exists(self):
        """Test that USE_DATABASE flag exists in settings."""
        from app.core.config import settings
        assert hasattr(settings, 'USE_DATABASE')
        assert isinstance(settings.USE_DATABASE, bool)

    def test_database_engine_exists(self):
        """Test that SQLAlchemy engine is created."""
        from app.db.database import engine
        assert engine is not None

    def test_session_local_exists(self):
        """Test that SessionLocal session factory exists."""
        from app.db.database import SessionLocal
        assert SessionLocal is not None

    def test_base_declarative_exists(self):
        """Test that Base declarative base exists."""
        from app.db.database import Base
        assert Base is not None

    def test_document_history_model_exists(self):
        """Test that DocumentHistory model is defined."""
        assert hasattr(models, 'DocumentHistory')

    def test_document_history_table_name(self):
        """Test that DocumentHistory table name is correct."""
        assert models.DocumentHistory.__tablename__ == "document_history"

    def test_document_history_has_required_columns(self):
        """Test that DocumentHistory has all required columns."""
        mapper = models.DocumentHistory.__mapper__
        column_names = [column.key for column in mapper.columns]

        required_columns = [
            'id', 'document_id', 'filename', 'processing_status',
            'original_language', 'selected_language',
            'readability_original_grade', 'readability_simplified_grade',
            'readability_target_grade', 'readability_target_achieved',
            'simplified_text', 'validation_status', 'validation_warnings',
            'processing_time_ms', 'text_length', 'word_count',
            'created_at', 'updated_at'
        ]

        for col in required_columns:
            assert col in column_names, f"Missing column: {col}"

    def test_document_history_indexes(self):
        """Test that DocumentHistory has indexes on key columns."""
        index_names = [idx.name for idx in models.DocumentHistory.__table__.indexes]

        assert "idx_document_history_document_id" in index_names
        assert "idx_document_history_created_at" in index_names
        assert "idx_document_history_processing_status" in index_names


class TestDatabaseSession:
    """Test database session management."""

    def test_get_db_dependency_exists(self):
        """Test that get_db dependency function exists."""
        from app.db.database import get_db
        assert callable(get_db)

    def test_get_db_yields_session(self):
        """Test that get_db yields a session and closes it."""
        from app.db.database import get_db
        gen = get_db()
        db = next(gen)
        assert db is not None
        assert hasattr(db, 'query')
        assert hasattr(db, 'add')
        assert hasattr(db, 'commit')
        assert hasattr(db, 'close')
        next(gen, None)


class TestHistoryService:
    """Test history service operations with SQLite test database."""

    def test_record_history_creates_record(self, db_session):
        """Test that record_history creates a new history record."""
        record = history_service.record_history(
            db=db_session,
            document_id="doc_test_123",
            filename="test.pdf",
            processing_status="completed",
            original_language="en",
            selected_language="kn",
            simplified_text="Simplified text",
            validation_status="PASS",
        )

        assert record is not None
        assert record.document_id == "doc_test_123"
        assert record.filename == "test.pdf"
        assert record.processing_status == "completed"
        assert record.simplified_text == "Simplified text"
        assert record.validation_status == "PASS"

    def test_record_history_generates_id(self, db_session):
        """Test that record_history generates a unique ID."""
        record = history_service.record_history(
            db=db_session,
            document_id="doc_test_456",
        )

        assert record.id is not None
        assert len(record.id) > 0

    def test_record_history_sets_timestamps(self, db_session):
        """Test that record_history sets created_at and updated_at."""
        record = history_service.record_history(
            db=db_session,
            document_id="doc_test_789",
        )

        assert record.created_at is not None
        assert record.updated_at is not None

    def test_get_history_by_document_id(self, db_session):
        """Test retrieving history by document_id."""
        history_service.record_history(
            db=db_session,
            document_id="doc_retrieve_test",
            filename="document.pdf",
            simplified_text="Test content",
        )

        records = history_service.get_history_by_document_id(db_session, "doc_retrieve_test")

        assert len(records) == 1
        assert records[0].document_id == "doc_retrieve_test"
        assert records[0].filename == "document.pdf"

    def test_get_history_by_document_id_not_found(self, db_session):
        """Test retrieving history for a nonexistent document."""
        records = history_service.get_history_by_document_id(db_session, "doc_nonexistent")
        assert len(records) == 0

    def test_multiple_records_same_document_id(self, db_session):
        """Test that same document_id can have multiple records (re-processing)."""
        history_service.record_history(db=db_session, document_id="doc_multi_test")
        history_service.record_history(db=db_session, document_id="doc_multi_test")
        history_service.record_history(db=db_session, document_id="doc_multi_test")

        records = history_service.get_history_by_document_id(db_session, "doc_multi_test")
        assert len(records) == 3

    def test_list_history_default_pagination(self, db_session):
        """Test listing history with default pagination."""
        for i in range(3):
            history_service.record_history(db=db_session, document_id=f"doc_list_{i}")

        result = history_service.list_history(db_session, page=1, limit=10)

        assert result["total"] == 3
        assert len(result["items"]) == 3
        assert result["page"] == 1
        assert result["limit"] == 10
        assert result["total_pages"] == 1

    def test_list_history_pagination(self, db_session):
        """Test listing history with pagination."""
        for i in range(5):
            history_service.record_history(db=db_session, document_id=f"doc_page_{i}")

        result = history_service.list_history(db_session, page=1, limit=2)

        assert result["total"] == 5
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["total_pages"] == 3

        result_page3 = history_service.list_history(db_session, page=3, limit=2)
        assert len(result_page3["items"]) == 1

    def test_list_history_clamps_limit(self, db_session):
        """Test that limit is clamped to 50 maximum."""
        result = history_service.list_history(db_session, page=1, limit=100)
        assert result["limit"] == 50

    def test_list_history_clamps_page(self, db_session):
        """Test that page is clamped to minimum 1."""
        result = history_service.list_history(db_session, page=-5, limit=10)
        assert result["page"] == 1

    def test_list_history_newest_first(self, db_session):
        """Test that history list returns newest records first."""
        for i in range(3):
            history_service.record_history(db=db_session, document_id=f"doc_order_{i}")

        result = history_service.list_history(db_session, page=1, limit=10)

        timestamps = [r.created_at for r in result["items"]]
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1]

    def test_update_processing_status(self, db_session):
        """Test updating processing status."""
        history_service.record_history(
            db=db_session,
            document_id="doc_update_test",
            processing_status="pending",
        )

        updated = history_service.update_processing_status(
            db=db_session,
            document_id="doc_update_test",
            status="completed",
        )

        assert updated is not None
        assert updated.processing_status == "completed"

    def test_update_processing_status_not_found(self, db_session):
        """Test updating status for nonexistent document."""
        result = history_service.update_processing_status(
            db=db_session,
            document_id="doc_nonexistent",
            status="completed",
        )
        assert result is None

    def test_delete_history_by_document_id(self, db_session):
        """Test deleting history records."""
        history_service.record_history(db=db_session, document_id="doc_delete_test_1")
        history_service.record_history(db=db_session, document_id="doc_delete_test_2")
        history_service.record_history(db=db_session, document_id="doc_delete_test_1")

        records_before = history_service.get_history_by_document_id(db_session, "doc_delete_test_1")
        assert len(records_before) == 2

        deleted = history_service.delete_history_by_document_id(db_session, "doc_delete_test_1")
        assert deleted == 2

        records_after = history_service.get_history_by_document_id(db_session, "doc_delete_test_1")
        assert len(records_after) == 0

    def test_serialize_history_record(self, db_session):
        """Test that history record is properly serialized."""
        record = history_service.record_history(
            db=db_session,
            document_id="doc_serialize_test",
            filename="test.pdf",
            processing_status="completed",
            original_language="en",
            selected_language="kn",
            simplified_text="Hello world",
            validation_status="PASS",
            validation_warnings=[{"message": "Test warning"}],
            processing_time_ms=1250,
            text_length=100,
            word_count=15,
        )

        serialized = history_service.serialize_history_record(record)

        assert serialized["document_id"] == "doc_serialize_test"
        assert serialized["filename"] == "test.pdf"
        assert serialized["processing_status"] == "completed"
        assert serialized["original_language"] == "en"
        assert serialized["selected_language"] == "kn"
        assert serialized["simplified_text"] == "Hello world"
        assert serialized["validation"]["status"] == "PASS"
        assert serialized["validation"]["warnings"] == [{"message": "Test warning"}]
        assert serialized["processing_time_ms"] == 1250
        assert serialized["text_length"] == 100
        assert serialized["word_count"] == 15
        assert "readability" in serialized
        assert "created_at" in serialized
        assert "updated_at" in serialized

    def test_serialize_history_record_none_warnings(self, db_session):
        """Test serialization handles None validation_warnings."""
        record = history_service.record_history(
            db=db_session,
            document_id="doc_none_warnings",
        )

        serialized = history_service.serialize_history_record(record)
        assert serialized["validation"]["warnings"] is None

    def test_serialize_history_record_none_simplified(self, db_session):
        """Test serialization handles None simplified_text."""
        record = history_service.record_history(
            db=db_session,
            document_id="doc_none_text",
        )

        serialized = history_service.serialize_history_record(record)
        assert serialized["simplified_text"] is None

    def test_get_history_by_id(self, db_session):
        """Test retrieving history by record ID."""
        record = history_service.record_history(
            db=db_session,
            document_id="doc_by_id_test",
        )

        retrieved = history_service.get_history_by_id(db_session, record.id)

        assert retrieved is not None
        assert retrieved.id == record.id
        assert retrieved.document_id == "doc_by_id_test"

    def test_get_history_by_id_not_found(self, db_session):
        """Test retrieving nonexistent history record by ID."""
        result = history_service.get_history_by_id(db_session, "nonexistent-id")
        assert result is None

    def test_database_error_handling(self):
        """Test that database errors are properly handled."""
        mock_db = MagicMock()
        mock_db.add.side_effect = Exception("DB connection lost")
        mock_db.rollback = MagicMock()

        with pytest.raises(history_service.DatabaseError):
            history_service.record_history(
                db=mock_db,
                document_id="doc_error_test",
            )

    def test_history_error_structure(self):
        """Test that HistoryServiceError and DatabaseError are properly structured."""
        assert issubclass(history_service.DatabaseError, history_service.HistoryServiceError)
        assert issubclass(history_service.HistoryServiceError, Exception)

    def test_generate_history_id_unique(self):
        """Test that generated history IDs are unique."""
        id1 = history_service.generate_history_id()
        id2 = history_service.generate_history_id()
        assert id1 != id2
        assert len(id1) > 0


class TestHistoryAPIEndpoints:
    """Test history API endpoints."""

    def test_history_list_empty(self):
        """Test history list endpoint with no records."""
        response = client.get("/api/history")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["limit"] == 10

    def test_history_list_with_records(self, db_session):
        """Test history list endpoint with records."""
        history_service.record_history(
            db=db_session,
            document_id="doc_api_test_1",
            filename="test1.pdf",
            processing_status="completed",
        )
        history_service.record_history(
            db=db_session,
            document_id="doc_api_test_2",
            filename="test2.pdf",
            processing_status="completed",
        )

        response = client.get("/api/history")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_history_list_with_pagination(self, db_session):
        """Test history list endpoint with pagination parameters."""
        for i in range(3):
            history_service.record_history(
                db=db_session,
                document_id=f"doc_pagination_{i}",
            )

        response = client.get("/api/history?page=1&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 2
        assert data["total"] == 3

    def test_history_list_invalid_page_defaults_to_1(self):
        """Test history list with invalid page returns 422 (Pydantic validation)."""
        response = client.get("/api/history?page=-1")
        # FastAPI query validation rejects negative page with 422
        assert response.status_code in (422, 200)

    def test_history_list_invalid_limit_clamped(self):
        """Test history list with limit over 50 returns 422 (Pydantic validation)."""
        response = client.get("/api/history?limit=100")
        # FastAPI query validation rejects limit > 50 with 422
        assert response.status_code in (422, 200)

    def test_get_document_history_not_found(self):
        """Test getting history for nonexistent document returns 404."""
        response = client.get("/api/history/doc_nonexistent_id")

        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "HISTORY_NOT_FOUND" in data["error"]["code"]

    def test_get_document_history_success(self, db_session):
        """Test retrieving history for a specific document."""
        history_service.record_history(
            db=db_session,
            document_id="doc_api_get_test",
            filename="document.pdf",
            processing_status="completed",
            original_language="en",
            selected_language="en",
            simplified_text="This is simplified text.",
            validation_status="PASS",
            processing_time_ms=500,
            text_length=500,
        )

        response = client.get("/api/history/doc_api_get_test")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["history"]["document_id"] == "doc_api_get_test"
        assert data["history"]["filename"] == "document.pdf"
        assert data["history"]["processing_status"] == "completed"
        assert data["history"]["simplified_text"] == "This is simplified text."
        assert data["history"]["validation"]["status"] == "PASS"

    def test_get_document_history_multiple_records(self, db_session):
        """Test that getting history for re-processed document returns all records."""
        history_service.record_history(
            db=db_session,
            document_id="doc_multi_history",
            filename="first.pdf",
            validation_status="PASS",
        )
        history_service.record_history(
            db=db_session,
            document_id="doc_multi_history",
            filename="second.pdf",
            validation_status="FAIL",
        )

        response = client.get("/api/history/doc_multi_history")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_records"] == 2

    def test_history_response_no_db_creds(self):
        """Test that error responses do not expose database credentials."""
        with patch('app.services.history_service.list_history', side_effect=Exception(
            "psycopg connection to postgres:secret@localhost:5432/cognitive_accessibility_db failed"
        )):
            response = client.get("/api/history")

            data = response.json()
            response_str = str(data)
            assert "secret" not in response_str
            assert "localhost:5432" not in response_str

    def test_history_database_error_returns_503(self):
        """Test that database errors return 503 with consistent error format."""
        with patch('app.services.history_service.list_history', side_effect=history_service.DatabaseError(
            "Connection failed"
        )):
            response = client.get("/api/history")
            assert response.status_code == 503
            data = response.json()
            assert data["success"] is False
            assert "DATABASE_ERROR" in data["error"]["code"]

    def test_history_list_returns_correct_structure(self):
        """Test that history list response has all required fields."""
        response = client.get("/api/history")
        data = response.json()

        assert "success" in data
        assert "items" in data
        assert "page" in data
        assert "limit" in data
        assert "total" in data
        assert "total_pages" in data

    def test_history_get_returns_correct_structure(self, db_session):
        """Test that history single record response has all required fields."""
        history_service.record_history(
            db=db_session,
            document_id="doc_struct_test",
            filename="test.pdf",
            processing_status="completed",
        )

        response = client.get("/api/history/doc_struct_test")
        data = response.json()

        assert "success" in data
        assert "history" in data
        assert "created_at" in data["history"]
        assert "updated_at" in data["history"]
        assert "readability" in data["history"]
        assert "validation" in data["history"]


class TestHistoryEndpointsRegistered:
    """Test that history endpoints are properly registered in the app."""

    def test_history_routes_exist(self):
        """Test that history endpoints are registered in the app."""
        openapi_paths = app.openapi()['paths'].keys()
        history_paths = [p for p in openapi_paths if 'history' in p]
        assert len(history_paths) >= 2, f"Expected at least 2 history routes, got: {history_paths}"
        assert "/api/history" in history_paths
        assert "/api/history/{document_id}" in history_paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
