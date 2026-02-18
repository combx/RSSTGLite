import aiosqlite
import hashlib
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    async def init_db(self):
        """Initialize the database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS seen_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT,
                    url_hash TEXT,
                    published_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_entry_id ON seen_entries(entry_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_url_hash ON seen_entries(url_hash)")
            await db.commit()

    def _hash_url(self, url: str) -> str:
        """Create a hash of the URL."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()

    async def is_seen(self, entry_id: str, url: str) -> bool:
        """Check if an entry has already been seen by ID or URL hash."""
        url_hash = self._hash_url(url)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM seen_entries WHERE entry_id = ? OR url_hash = ?",
                (entry_id, url_hash)
            )
            result = await cursor.fetchone()
            return result is not None

    async def add_entry(self, entry_id: str, url: str, published_at: datetime = None):
        """Mark an entry as seen."""
        url_hash = self._hash_url(url)
        if published_at is None:
            published_at = datetime.now()
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO seen_entries (entry_id, url_hash, published_at) VALUES (?, ?, ?)",
                (entry_id, url_hash, published_at)
            )
            await db.commit()
