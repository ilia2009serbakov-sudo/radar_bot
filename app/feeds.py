import hashlib
import html
import re
from datetime import datetime, timezone

import aiohttp
import feedparser

from app.topics import classify

FEEDS = [
    ("Habr", "https://habr.com/ru/rss/all/all/?fl=ru"),
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
]


def clean(value: str, limit: int = 420) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(re.sub(r"\s+", " ", value)).strip()
    return value[:limit] + ("…" if len(value) > limit else "")


async def fetch_feed(session: aiohttp.ClientSession, source: str, url: str) -> list[dict]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15),
                               headers={"User-Agent": "RadarBot/1.0 (+Telegram bot)"}) as response:
            response.raise_for_status()
            data = await response.read()
        parsed = feedparser.parse(data)
        result = []
        for entry in parsed.entries[:40]:
            title = clean(entry.get("title", ""), 180)
            link = entry.get("link")
            summary = clean(entry.get("summary", "") or entry.get("description", ""))
            if not title or not link:
                continue
            published = None
            if entry.get("published_parsed"):
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif entry.get("updated_parsed"):
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            topics = classify(f"{title} {summary}")
            if not topics:
                continue
            result.append({
                "item_key": hashlib.sha256(link.encode()).hexdigest(),
                "title": title,
                "summary": summary or "Открыть материал, чтобы узнать подробности.",
                "url": link,
                "source": source,
                "published_at": published,
                "topics": topics,
            })
        return result
    except Exception:
        return []


async def collect_items() -> list[dict]:
    connector = aiohttp.TCPConnector(limit=8)
    async with aiohttp.ClientSession(connector=connector) as session:
        batches = [fetch_feed(session, source, url) for source, url in FEEDS]
        results = []
        for batch in await __import__('asyncio').gather(*batches, return_exceptions=True):
            if isinstance(batch, list):
                results.extend(batch)
        return results
