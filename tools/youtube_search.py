from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from tavily import TavilyClient
from core.config import YOUTUBE_TRANSCRIPT_LIMIT
from core.security import safe_exception
import os
import re
import time

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def _tavily_search_with_retry(**kwargs):
    last_error = None
    for attempt in range(2):
        try:
            return tavily.search(**kwargs)
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
    raise last_error


def _extract_video_id(url: str) -> str | None:
    """Extract a YouTube video id from common YouTube URL formats."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().replace("www.", "").replace("m.", "")

    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
        return video_id if re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id) else None

    if "youtube.com" in host:
        query_video_id = parse_qs(parsed.query).get("v", [None])[0]
        if query_video_id and re.fullmatch(r"[a-zA-Z0-9_-]{11}", query_video_id):
            return query_video_id

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            video_id = path_parts[1]
            return video_id if re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id) else None

    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([a-zA-Z0-9_-]{11})", url)
    return match.group(1) if match else None


def _fetch_transcript_text(video_id: str) -> str:
    """Fetch transcript text using the installed youtube-transcript-api version."""
    api = YouTubeTranscriptApi()

    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
    else:
        transcript = api.fetch(video_id)

    parts = []
    for item in transcript:
        text = item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
        if text:
            parts.append(text.replace("\n", " "))

    return " ".join(parts)


def search_youtube(query: str, max_results: int = 2) -> list:
    """Find YouTube videos and extract their transcripts."""
    try:
        results = _tavily_search_with_retry(
            query=f"{query} site:youtube.com/watch OR site:youtu.be",
            max_results=max_results * 3
        )
    except Exception as exc:
        print(f"YouTube search skipped: {safe_exception(exc)}")
        return []

    sources = []
    seen_video_ids = set()

    for r in results.get("results", []):
        if len(sources) >= max_results:
            break

        url = r.get("url", "")
        video_id = _extract_video_id(url)
        if not video_id or video_id in seen_video_ids:
            continue

        seen_video_ids.add(video_id)

        try:
            text = _fetch_transcript_text(video_id)
        except Exception as exc:
            print(f"YouTube transcript skipped for {video_id}: {safe_exception(exc)}")
            text = r.get("content", "") or r.get("snippet", "")

        if not text:
            continue

        sources.append({
            "title": r.get("title", "YouTube video"),
            "url": url,
            "content": text[:YOUTUBE_TRANSCRIPT_LIMIT],
            "source_type": "youtube",
            "relevance": 0.7
        })

    return sources
