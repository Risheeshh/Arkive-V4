from sqlalchemy.orm import Session
from app.models.bookmark import Bookmark, BookmarkStatus
from app.models.tag import Tag
from app.models.content import Content
from app.schemas.bookmark import BookmarkCreate, BookmarkUpdate
from app.schemas.tag import TagCreate
import uuid
import trafilatura
from html.parser import HTMLParser
from urllib.request import Request, urlopen
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sync_playwright = None
import logging
import json
import re
from urllib.parse import urljoin, urlparse
from app.core.queue import queue
from app.core.config import settings
from datetime import datetime
from rq import Retry

logger = logging.getLogger(__name__)

GENRES = [
    "Artificial Intelligence", "Business", "Career", "Design", "Development",
    "Education", "Finance", "Health", "Lifestyle", "Marketing", "News",
    "Photography", "Productivity", "Science", "Security", "Travel", "Writing",
]

def _fallback_genres(title: str, body: str) -> list[str]:
    text = f"{title} {body}".lower()
    matches = {
        "Artificial Intelligence": ("ai", "machine learning", "llm", "neural"),
        "Development": ("code", "developer", "python", "javascript", "api"),
        "Design": ("design", "typography", "figma", "ux", "ui"),
        "Business": ("business", "startup", "company", "strategy"),
        "Productivity": ("productivity", "focus", "workflow", "habit"),
        "Science": ("science", "research", "experiment"),
        "Security": ("security", "privacy", "encryption", "vulnerability"),
        "Finance": ("finance", "investing", "market", "money"),
        "Health": ("health", "fitness", "wellness", "medical"),
        "Travel": ("travel", "destination", "flight", "hotel"),
        "Writing": ("writing", "author", "story", "journal"),
        "Education": ("learn", "education", "course", "tutorial"),
    }
    found = [genre for genre, keywords in matches.items() if any(keyword in text for keyword in keywords)]
    return found[:3] or ["News"]

def categorize_content(title: str, body: str) -> list[str]:
    """Classify content into the fixed genre vocabulary, with a local fallback."""
    if not settings.OPENAI_API_KEY:
        return _fallback_genres(title, body)
    try:
        from urllib.request import Request, urlopen
        payload = json.dumps({
            "model": settings.OPENAI_MODEL,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": f"Return only a JSON array using these genres: {', '.join(GENRES)}."},
                {"role": "user", "content": f"Title: {title}\nContent: {body[:6000]}"},
            ],
        }).encode()
        request = Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode())
        values = json.loads(result["choices"][0]["message"]["content"])
        return [value for value in values if value in GENRES][:3] or _fallback_genres(title, body)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        logger.exception("OpenAI genre categorization failed; using local classification")
        return _fallback_genres(title, body)

def get_bookmark(db: Session, bookmark_id: uuid.UUID, user_id: uuid.UUID) -> Bookmark | None:
    return db.query(Bookmark).filter(Bookmark.id == bookmark_id, Bookmark.user_id == user_id).first()

def get_bookmarks(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[Bookmark]:
    return db.query(Bookmark).filter(Bookmark.user_id == user_id).offset(skip).limit(limit).all()

def create_bookmark(db: Session, bookmark: BookmarkCreate, user_id: uuid.UUID) -> Bookmark:
    db_bookmark = Bookmark(
        title=bookmark.title,
        url=str(bookmark.url),
        description=bookmark.description,
        user_id=user_id,
        status=BookmarkStatus.UNREAD
    )
    db.add(db_bookmark)
    db.commit()
    db.refresh(db_bookmark)
    
    # Enqueue the processing job with retry policy
    queue.enqueue(
        "app.worker.process_bookmark_job",
        str(db_bookmark.id),
        retry=Retry(max=3, interval=[10, 30, 60])
    )
    
    return db_bookmark

def update_bookmark(db: Session, bookmark_id: uuid.UUID, user_id: uuid.UUID, bookmark_update: BookmarkUpdate) -> Bookmark | None:
    db_bookmark = get_bookmark(db, bookmark_id, user_id)
    if not db_bookmark:
        return None
    update_data = bookmark_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "url" and value is not None:
            value = str(value)
        if field == "status" and value is not None:
            value = BookmarkStatus(value)
        setattr(db_bookmark, field, value)
    db.commit()
    db.refresh(db_bookmark)
    return db_bookmark

def delete_bookmark(db: Session, bookmark_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    db_bookmark = get_bookmark(db, bookmark_id, user_id)
    if not db_bookmark:
        return False
    db.delete(db_bookmark)
    db.commit()
    return True

def get_or_create_tags(db: Session, tag_names: list[str], user_id: uuid.UUID) -> list[Tag]:
    tags = []
    for name in tag_names:
        tag = db.query(Tag).filter(Tag.name == name, Tag.user_id == user_id).first()
        if not tag:
            tag = Tag(name=name, user_id=user_id)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags

def add_tags_to_bookmark(db: Session, bookmark: Bookmark, tag_names: list[str], user_id: uuid.UUID):
    tags = get_or_create_tags(db, tag_names, user_id)
    bookmark.tags = tags
    db.commit()
    db.refresh(bookmark)

def remove_tag_from_bookmark(db: Session, bookmark: Bookmark, tag_id: uuid.UUID):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if tag in bookmark.tags:
        bookmark.tags.remove(tag)
        db.commit()
        db.refresh(bookmark)

def parse_date(date_str: str | None) -> datetime | None:
    """Parse date string from trafilatura (ISO 8601) to datetime."""
    if not date_str:
        return None
    try:
        # Remove timezone info if present for simplicity, or handle it
        # Python's fromisoformat supports timezone in 3.11+, but we'll strip for compatibility
        if 'T' in date_str:
            # Split on '+' or '-' to remove timezone, but careful with negative timezone
            # We'll just try to parse with fromisoformat and if it fails, try without timezone
            try:
                return datetime.fromisoformat(date_str)
            except ValueError:
                # Remove timezone part
                if '+' in date_str:
                    date_str = date_str.split('+')[0]
                elif date_str.count('-') > 2:  # more than date separators
                    # This is a naive approach; better to use dateutil but we avoid extra dep
                    pass
                return datetime.fromisoformat(date_str)
        else:
            return datetime.fromisoformat(date_str)
    except Exception as e:
        logger.warning(f"Failed to parse date '{date_str}': {e}")
        return None

def extract_with_trafilatura(url: str) -> dict | None:
    """Extract content using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            result = trafilatura.extract(downloaded, include_comments=False, include_tables=False, output_format='json')
            if result:
                import json
                data = json.loads(result)
                return {
                    "title": data.get("title"),
                    "body": data.get("text"),
                    "author": data.get("author"),
                    "published_at": parse_date(data.get("date"))
                }
    except Exception as e:
        logger.warning(f"Trafilatura extraction failed for {url}: {e}")
    return None

def extract_with_playwright(url: str) -> dict | None:
    """Extract content with an optional browser or a lightweight HTTP fallback."""
    if sync_playwright is None:
        return extract_with_http(url)
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Get the main content - this is a simple heuristic
            content = page.evaluate("""() => {
                // Try to find the main article content
                const article = document.querySelector('article') || document.querySelector('main') || document.body;
                return article.innerText;
            }""")
            title = page.title()
            return {
                "title": title,
                "body": content,
                "author": None,
                "published_at": None
            }
    except Exception as e:
        logger.warning(f"Playwright extraction failed for {url}: {e}")
    finally:
        if browser:
            browser.close()
    return None


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.text: list[str] = []
        self._in_title = False
        self._ignored = 0
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attributes = dict(attrs)
            key = attributes.get("property") or attributes.get("name")
            value = attributes.get("content")
            if key and value:
                self.meta[key] = value
        if tag == "title":
            self._in_title = True
        elif tag in {"script", "style", "noscript"}:
            self._ignored += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in {"script", "style", "noscript"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._ignored and data.strip():
            self.text.append(data.strip())


def extract_with_http(url: str) -> dict | None:
    """Extract readable text from pages without requiring a browser runtime."""
    try:
        request = Request(url, headers={"User-Agent": "Arkive/1.0"})
        with urlopen(request, timeout=30) as response:
            html = response.read().decode(response.headers.get_content_charset() or "utf-8", "replace")
        parser = _TextParser()
        parser.feed(html)
        body = "\n".join(parser.text)
        if body:
            metadata = dict(parser.meta)
            host = urlparse(url).hostname or ""
            return {
                "title": parser.title.strip() or None,
                "body": body,
                "author": None,
                "published_at": None,
                "site_name": metadata.get("og:site_name") or host.replace("www.", ""),
                "image_url": urljoin(url, metadata["og:image"]) if metadata.get("og:image") else None,
                "description": metadata.get("description") or metadata.get("og:description"),
                "logo_url": urljoin(url, "/favicon.ico"),
            }
    except Exception as e:
        logger.warning(f"HTTP extraction failed for {url}: {e}")
    return None

def clean_text(text: str) -> str:
    """Clean and normalize extracted text."""
    if not text:
        return ""
    # Remove excessive whitespace
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)

def process_bookmark(db: Session, bookmark_id: uuid.UUID):
    """Process a bookmark: extract content and update status."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bookmark:
        logger.error(f"Bookmark {bookmark_id} not found")
        return False

    # Idempotency: if already processed (has content), skip
    if bookmark.content:
        logger.info(f"Bookmark {bookmark_id} already has content, skipping")
        return True

    try:
        # Try trafilatura first
        extracted = extract_with_trafilatura(bookmark.url)
        
        # Fallback to Playwright if trafilatura returns empty content
        if not extracted or not extracted.get("body"):
            logger.info(f"Trafilatura returned empty for {bookmark.url}, trying Playwright")
            extracted = extract_with_playwright(bookmark.url)
        
        if not extracted or not extracted.get("body"):
            raise ValueError("Both trafilatura and Playwright failed to extract content")

        # Clean the extracted text
        cleaned_body = clean_text(extracted["body"])
        cleaned_title = clean_text(extracted["title"]) if extracted["title"] else bookmark.title
        genres = categorize_content(cleaned_title, cleaned_body)

        # Create Content row
        content = Content(
            bookmark_id=bookmark.id,
            user_id=bookmark.user_id,
            title=cleaned_title,
            body=cleaned_body,
            raw_text=cleaned_body,
            author=extracted.get("author"),
            published_at=extracted.get("published_at")
        )
        db.add(content)
        bookmark.site_name = extracted.get("site_name") or (urlparse(bookmark.url).hostname or "").replace("www.", "")
        bookmark.logo_url = extracted.get("logo_url")
        bookmark.image_url = extracted.get("image_url")
        bookmark.excerpt = extracted.get("description") or cleaned_body[:240]
        bookmark.genres = genres
        
        # Update bookmark status to read
        bookmark.status = BookmarkStatus.READ
        bookmark.error_message = None
        
        db.commit()
        logger.info(f"Successfully processed bookmark {bookmark_id}")
        return True
        
    except Exception as e:
        # Update bookmark status to failed and store error message
        bookmark.status = BookmarkStatus.FAILED
        bookmark.error_message = str(e)
        db.commit()
        logger.error(f"Failed to process bookmark {bookmark_id}: {e}")
        raise
