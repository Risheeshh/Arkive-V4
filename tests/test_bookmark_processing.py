from unittest.mock import patch, MagicMock
import pytest
from sqlalchemy.orm import Session

from app.models.bookmark import Bookmark, BookmarkStatus
from app.models.content import Content
from app.models.user import User
from app.services.bookmark_service import (
    create_bookmark,
    process_bookmark,
    extract_with_trafilatura,
    extract_with_playwright,
)
from app.schemas.bookmark import BookmarkCreate
from app.core import queue as queue_module


def test_create_bookmark_enqueues_job(db_session: Session, test_user: User):
    """Test that creating a bookmark enqueues a processing job."""
    bookmark_data = BookmarkCreate(
        title="Test Bookmark",
        url="https://example.com",
        description="A test bookmark"
    )
    
    # Create bookmark
    bookmark = create_bookmark(db_session, bookmark_data, test_user.id)
    
    # Check that a job was enqueued
    jobs = queue_module.queue.jobs
    assert len(jobs) == 1
    job = jobs[0]
    assert job.func_name == "app.worker.process_bookmark_job"
    assert job.args[0] == str(bookmark.id)
    # Check retry policy
    assert job.retry is not None


def test_process_bookmark_successful_trafilatura(db_session: Session, test_user: User):
    """Test successful processing with trafilatura extraction."""
    # Create a bookmark directly in DB (bypassing enqueue)
    bookmark = Bookmark(
        title="Test",
        url="https://example.com/article",
        user_id=test_user.id,
        status=BookmarkStatus.UNREAD
    )
    db_session.add(bookmark)
    db_session.commit()
    db_session.refresh(bookmark)
    
    # Mock trafilatura extraction
    with patch("app.services.bookmark_service.extract_with_trafilatura") as mock_extract:
        mock_extract.return_value = {
            "title": "Extracted Title",
            "body": "Extracted article body content.",
            "author": "John Doe",
            "published_at": "2024-01-01T12:00:00"
        }
        
        # Process the bookmark
        process_bookmark(db_session, bookmark.id)
    
    # Refresh bookmark
    db_session.refresh(bookmark)
    
    # Check status changed to READ
    assert bookmark.status == BookmarkStatus.READ
    assert bookmark.error_message is None
    
    # Check Content row created
    content = db_session.query(Content).filter(Content.bookmark_id == bookmark.id).first()
    assert content is not None
    assert content.title == "Extracted Title"
    assert content.body == "Extracted article body content."
    assert content.author == "John Doe"
    assert content.published_at is not None


def test_process_bookmark_playwright_fallback(db_session: Session, test_user: User):
    """Test Playwright fallback when trafilatura returns empty content."""
    bookmark = Bookmark(
        title="Test",
        url="https://example.com/article",
        user_id=test_user.id,
        status=BookmarkStatus.UNREAD
    )
    db_session.add(bookmark)
    db_session.commit()
    db_session.refresh(bookmark)
    
    # Mock trafilatura to return empty, Playwright to return content
    with patch("app.services.bookmark_service.extract_with_trafilatura") as mock_trafilatura, \
         patch("app.services.bookmark_service.extract_with_playwright") as mock_playwright:
        
        mock_trafilatura.return_value = None
        mock_playwright.return_value = {
            "title": "Playwright Title",
            "body": "Playwright extracted content.",
            "author": None,
            "published_at": None
        }
        
        process_bookmark(db_session, bookmark.id)
    
    db_session.refresh(bookmark)
    assert bookmark.status == BookmarkStatus.READ
    
    content = db_session.query(Content).filter(Content.bookmark_id == bookmark.id).first()
    assert content is not None
    assert content.title == "Playwright Title"
    assert content.body == "Playwright extracted content."


def test_process_bookmark_failed_extraction(db_session: Session, test_user: User):
    """Test failed extraction sets status to FAILED and stores error message."""
    bookmark = Bookmark(
        title="Test",
        url="https://example.com/article",
        user_id=test_user.id,
        status=BookmarkStatus.UNREAD
    )
    db_session.add(bookmark)
    db_session.commit()
    db_session.refresh(bookmark)
    
    # Mock both extractors to fail
    with patch("app.services.bookmark_service.extract_with_trafilatura") as mock_trafilatura, \
         patch("app.services.bookmark_service.extract_with_playwright") as mock_playwright:
        
        mock_trafilatura.return_value = None
        mock_playwright.return_value = None
        
        with pytest.raises(ValueError):
            process_bookmark(db_session, bookmark.id)
    
    db_session.refresh(bookmark)
    assert bookmark.status == BookmarkStatus.FAILED
    assert bookmark.error_message is not None
    assert "Both trafilatura and Playwright failed" in bookmark.error_message
    
    # No Content row should be created
    content = db_session.query(Content).filter(Content.bookmark_id == bookmark.id).first()
    assert content is None


def test_process_bookmark_idempotency(db_session: Session, test_user: User):
    """Test that processing the same bookmark twice does not create duplicate Content rows."""
    bookmark = Bookmark(
        title="Test",
        url="https://example.com/article",
        user_id=test_user.id,
        status=BookmarkStatus.UNREAD
    )
    db_session.add(bookmark)
    db_session.commit()
    db_session.refresh(bookmark)
    
    with patch("app.services.bookmark_service.extract_with_trafilatura") as mock_extract:
        mock_extract.return_value = {
            "title": "Extracted Title",
            "body": "Extracted article body content.",
            "author": "John Doe",
            "published_at": "2024-01-01T12:00:00"
        }
        
        # Process first time
        process_bookmark(db_session, bookmark.id)
        # Process second time
        process_bookmark(db_session, bookmark.id)
    
    db_session.refresh(bookmark)
    assert bookmark.status == BookmarkStatus.READ
    
    # Only one Content row should exist
    contents = db_session.query(Content).filter(Content.bookmark_id == bookmark.id).all()
    assert len(contents) == 1


def test_extract_with_trafilatura_success():
    """Test trafilatura extraction function directly."""
    with patch("trafilatura.fetch_url") as mock_fetch, \
         patch("trafilatura.extract") as mock_extract:
        
        mock_fetch.return_value = "<html>...</html>"
        mock_extract.return_value = '{"title": "Test", "text": "Body", "author": "Author", "date": "2024-01-01T12:00:00"}'
        
        result = extract_with_trafilatura("https://example.com")
        
        assert result is not None
        assert result["title"] == "Test"
        assert result["body"] == "Body"
        assert result["author"] == "Author"
        assert result["published_at"] is not None


def test_extract_with_trafilatura_failure():
    """Test trafilatura extraction failure returns None."""
    with patch("trafilatura.fetch_url") as mock_fetch:
        mock_fetch.return_value = None
        
        result = extract_with_trafilatura("https://example.com")
        assert result is None


def test_extract_with_playwright_success():
    """Test Playwright extraction function directly."""
    with patch("app.services.bookmark_service.sync_playwright") as mock_playwright:
        mock_browser = MagicMock()
        mock_page = MagicMock()
        mock_page.title.return_value = "Page Title"
        mock_page.evaluate.return_value = "Page content"
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__enter__.return_value.chromium.launch.return_value = mock_browser
        
        result = extract_with_playwright("https://example.com")
        
        assert result is not None
        assert result["title"] == "Page Title"
        assert result["body"] == "Page content"
        assert result["author"] is None
        assert result["published_at"] is None


def test_extract_with_playwright_failure():
    """Test Playwright extraction failure returns None."""
    with patch("app.services.bookmark_service.sync_playwright") as mock_playwright:
        mock_playwright.return_value.__enter__.side_effect = Exception("Browser error")
        
        result = extract_with_playwright("https://example.com")
        assert result is None


# Fixture for test_user
@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        is_active="active"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
