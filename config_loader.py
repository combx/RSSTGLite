import json
import os
from typing import List, Union
from pydantic import BaseModel, HttpUrl, Field, validator

class FeedConfig(BaseModel):
    name: str = Field(..., description="Human-readable name for the feed")
    url: HttpUrl = Field(..., description="URL of the RSS/Atom feed")
    target_chat_id: Union[int, str] = Field(..., description="Target Telegram chat ID (integer) or username (string)")
    telegram_token: Union[str, None] = Field(default=None, description="Optional: specific bot token for this feed")
    check_interval: int = Field(default=600, ge=60, description="Check interval in seconds (min 60)")
    message_template: str = Field(
        default="📢 **{title}**\n\n{link}",
        description="Template for the message. Variables: {title}, {link}, {published}, {author}"
    )

    @validator('url', pre=True)
    def validate_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

class AppConfig(BaseModel):
    telegram_token: str = Field(..., description="Telegram Bot API Token")
    database_path: str = Field(default="data/feedbot.db", description="Path to SQLite database file")
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    feeds: List[FeedConfig] = Field(default_factory=list, description="List of feeds to monitor")

    @classmethod
    def load(cls, path: str = "config.json") -> "AppConfig":
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(**data)
