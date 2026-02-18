import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from datetime import datetime
from time import mktime, time

import aiohttp
import feedparser

from config_loader import AppConfig, FeedConfig
from database import Database
from cleaner import clean_url

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("feedbot")

class FeedBot:
    def __init__(self, config_path: str):
        self.config = AppConfig.load(config_path)
        logger.setLevel(self.config.log_level)
        self.db = Database(self.config.database_path)
        self.lock = asyncio.Lock()
        self.last_published_time = 0.0
        self.running = True

    async def start(self):
        """Main entry point."""
        logger.info("Starting FeedBot...")
        await self.db.init_db()

        tasks = []
        async with aiohttp.ClientSession() as session:
            for feed_config in self.config.feeds:
                task = asyncio.create_task(self.monitor_feed(session, feed_config))
                tasks.append(task)
            
            logger.info(f"Monitored feeds: {len(tasks)}")
            
            # Wait for all tasks to complete (or be cancelled)
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                logger.info("Tasks cancelled. Shutting down.")

    async def monitor_feed(self, session: aiohttp.ClientSession, feed_config: FeedConfig):
        """Monitor a single feed."""
        logger.info(f"Started monitoring: {feed_config.name} ({feed_config.url})")
        
        while self.running:
            try:
                content = await self.fetch_feed(session, str(feed_config.url))
                if content:
                    await self.process_feed(feed_config, content, session)
            except Exception as e:
                logger.error(f"Error monitoring {feed_config.name}: {e}")
            
            # Wait for next check
            await asyncio.sleep(feed_config.check_interval)

    async def fetch_feed(self, session: aiohttp.ClientSession, url: str) -> str:
        """Fetch feed content asynchronously."""
        try:
            async with session.get(url, timeout=30) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    async def process_feed(self, feed_config: FeedConfig, content: str, session: aiohttp.ClientSession):
        """Parse and process feed entries."""
        # Parse feed
        parsed = feedparser.parse(content)
        
        if parsed.bozo:
            logger.warning(f"Feed parsing error for {feed_config.name}: {parsed.bozo_exception}")

        # Iterate entries from oldest to newest
        for entry in reversed(parsed.entries):
            await self.process_entry(feed_config, entry, session)

    async def process_entry(self, feed_config: FeedConfig, entry: any, session: aiohttp.ClientSession):
        """Process a single entry."""
        # Extract ID and URL
        entry_id = getattr(entry, 'id', None) or getattr(entry, 'guid', None) or getattr(entry, 'link', None)
        raw_link = getattr(entry, 'link', '')
        
        if not raw_link:
            return

        cleaned_link = clean_url(raw_link)
        
        # Check if seen
        if await self.db.is_seen(entry_id, cleaned_link):
            return

        # Prepare message
        message = self.format_message(
            feed_config.message_template, 
            entry, 
            cleaned_link, 
            rhash=feed_config.rhash
        )
        
        # Determine token: Use feed-specific if set, else global
        token = feed_config.telegram_token or self.config.telegram_token

        # Send to Telegram with Rate Limiting
        async with self.lock:
            # Check time since last publication
            now = time()
            elapsed = now - self.last_published_time
            if elapsed < self.config.publication_delay:
                wait_time = self.config.publication_delay - elapsed
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

            if await self.send_telegram_message(session, feed_config.target_chat_id, message, token):
                self.last_published_time = time()
                
                # Mark as seen ONLY if sent successfully
                published_parsed = getattr(entry, 'published_parsed', None)
                published_at = datetime.fromtimestamp(mktime(published_parsed)) if published_parsed else datetime.now()
                
                await self.db.add_entry(entry_id, cleaned_link, published_at)
                logger.info(f"Posted new entry from {feed_config.name}: {entry.get('title', 'No Title')}")

    def format_message(self, template: str, entry: any, link: str, rhash: str = None) -> str:
        """Format the message using the template."""
        title = getattr(entry, 'title', 'No Title')
        author = getattr(entry, 'author', 'Unknown')
        
        # Format published date
        published_parsed = getattr(entry, 'published_parsed', None)
        if published_parsed:
            dt = datetime.fromtimestamp(mktime(published_parsed))
            published = dt.strftime('%Y-%m-%d %H:%M')
        else:
            published = datetime.now().strftime('%Y-%m-%d %H:%M')

        # Handle Instant View if rhash is provided
        final_link = link
        if rhash:
            from urllib.parse import quote
            encoded_url = quote(link)
            final_link = f"https://t.me/iv?url={encoded_url}&rhash={rhash}"

        # Create Markdown link
        markdown_link = f"[Link]({final_link})"

        return template.format(
            title=title,
            link=markdown_link,
            author=author,
            published=published
        )

    async def send_telegram_message(self, session: aiohttp.ClientSession, chat_id: str, text: str, token: str) -> bool:
        """Send message to Telegram."""
        if not token:
             logger.error("No Telegram token provided for this feed.")
             return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }
        
        try:
            async with session.post(url, json=payload, timeout=10) as response:
                resp_data = await response.json()
                if not resp_data.get("ok"):
                    logger.error(f"Telegram API Error: {resp_data}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Failed to send to Telegram: {e}")
            return False

async def main():
    bot = FeedBot("config.json")
    
    # Handle graceful shutdown
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Shutdown signal received...")
        bot.running = False
        stop_event.set()
        # Cancel all tasks
        for task in asyncio.all_tasks():
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await bot.start()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.critical(f"Fatal error: {e}")

if __name__ == "__main__":
    try:
        # Use uvloop if available for better performance
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    asyncio.run(main())