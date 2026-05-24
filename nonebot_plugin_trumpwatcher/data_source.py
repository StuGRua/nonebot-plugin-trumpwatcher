from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .config import config

BEIJING_TZ = timezone(timedelta(hours=8))
REPOST_PREFIX = "RT @"


@dataclass(slots=True, frozen=True)
class TruthPost:
    post_id: str
    created_at: datetime
    content: str
    url: str
    media: tuple[str, ...]


def _normalize_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_created_at(value: str) -> datetime:
    return _normalize_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _parse_post(payload: dict[str, Any]) -> TruthPost | None:
    post_id = str(payload.get("id", "")).strip()
    created_at_raw = payload.get("created_at")
    url = str(payload.get("url", "")).strip()
    content = str(payload.get("content", "")).strip()
    if not post_id or not isinstance(created_at_raw, str) or not url:
        return None
    try:
        created_at = _parse_created_at(created_at_raw)
    except ValueError:
        return None
    media: list[str] = []
    media_raw = payload.get("media")
    if isinstance(media_raw, list):
        media.extend(
            item.strip() for item in media_raw if isinstance(item, str) and item.strip()
        )
    return TruthPost(
        post_id=post_id,
        created_at=created_at,
        content=content,
        url=url,
        media=tuple(media),
    )


async def fetch_archive_posts(limit: int | None = None) -> list[TruthPost]:
    async with httpx.AsyncClient(timeout=config.trumpwatcher_timeout) as client:
        resp = await client.get(config.trumpwatcher_source_url)
        resp.raise_for_status()
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ValueError("CNN archive JSON 解析失败") from exc
    if not isinstance(payload, list):
        raise ValueError("CNN archive JSON 格式错误：根节点不是数组")
    if limit is not None:
        payload = payload[:limit]
    posts: list[TruthPost] = []
    for item in payload:
        if isinstance(item, dict) and (parsed := _parse_post(item)):
            posts.append(parsed)
    return posts


def filter_new_posts(
    posts: Sequence[TruthPost],
    archived_ids: set[str],
    latest_archived: datetime | None,
    *,
    skip_empty: bool = False,
) -> list[TruthPost]:
    latest_utc = _normalize_utc(latest_archived) if latest_archived else None
    filtered: list[TruthPost] = []
    seen: set[str] = set()
    for post in posts:
        if post.post_id in archived_ids or post.post_id in seen:
            continue
        seen.add(post.post_id)
        if post.content.startswith(REPOST_PREFIX):
            continue
        if latest_utc and post.created_at <= latest_utc:
            continue
        if skip_empty and not post.content.strip() and not post.media:
            continue
        filtered.append(post)
    return filtered


def format_post_message(post: TruthPost) -> str:
    lines = [post.content or "(无正文)"]
    if post.media:
        lines.append("\n".join(post.media))
    beijing_time = post.created_at.astimezone(BEIJING_TZ).strftime("%m-%d %H:%M")
    lines.append(f"🕐 {beijing_time}  🔗 {post.url}")
    return "\n".join(lines)
