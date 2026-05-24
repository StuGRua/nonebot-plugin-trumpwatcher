from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Any

import httpx
from nonebot import logger

from .config import config
from .data_source import TruthPost

_SYSTEM_PROMPT = (
    '你是新闻编辑助手。请把用户提供的特朗普 Truth Social 动态翻译成简体中文，'
    '然后严格按以下格式输出（必须包含“标题：”和“概要：”两个标签）：\n\n'
    '标题：<一句简洁标题，概括动态核心内容，不超过30字>\n'
    '概要：<翻译原文并给出最多3条要点总结>\n\n'
    '输出要简洁、客观，不要编造信息。'
)

_TITLE_PATTERN = re.compile(r"标题[：:][ \t]*(.+?)(?:\n|$)")
_SUMMARY_PATTERN = re.compile(r"概要[：:]\s*(.+)", re.DOTALL)
_MAX_RETRIES = 3


@dataclass(slots=True)
class AISummaryResult:
    title: str
    summary: str


class _MultimodalNotSupportedError(Exception):
    pass


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _looks_like_multimodal_unsupported(text: str) -> bool:
    lowered = text.lower()
    keywords = ("multimodal", "image", "vision", "图片", "图像", "不支持")
    return any(keyword in lowered for keyword in keywords)


def _collect_image_urls(media: tuple[str, ...]) -> list[str]:
    if not config.trumpwatcher_ai_multimodal_enabled:
        return []
    max_images = config.trumpwatcher_ai_multimodal_max_images
    if max_images <= 0:
        return []
    image_urls = [item for item in media if _looks_like_url(item)]
    return image_urls[:max_images]


def _build_user_content(source_text: str, image_urls: list[str]) -> str | list[dict[str, Any]]:
    if not image_urls:
        return source_text
    content: list[dict[str, Any]] = [{"type": "text", "text": source_text}]
    content.extend(
        {"type": "image_url", "image_url": {"url": image_url}} for image_url in image_urls
    )
    return content


def _extract_content(payload: dict[str, Any]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content.strip() or None
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                parts.append(text.strip())
        return "\n".join(parts).strip() or None
    return None


def _parse_title_summary(text: str) -> AISummaryResult | None:
    title_match = _TITLE_PATTERN.search(text)
    summary_match = _SUMMARY_PATTERN.search(text)
    if not title_match or not summary_match:
        return None
    title = title_match.group(1).strip()
    summary = summary_match.group(1).strip()
    if not title or not summary:
        return None
    return AISummaryResult(title=title, summary=summary)


async def _request_summary(source_text: str, image_urls: list[str]) -> str | None:
    api_key = config.trumpwatcher_ai_api_key.strip()
    if not api_key:
        return None

    url = f"{config.trumpwatcher_ai_api_base.rstrip('/')}/chat/completions"
    payload = {
        "model": config.trumpwatcher_ai_model,
        "temperature": config.trumpwatcher_ai_temperature,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_content(source_text, image_urls)},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=config.trumpwatcher_ai_timeout) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        response_text = exc.response.text if exc.response is not None else ""
        if image_urls and _looks_like_multimodal_unsupported(response_text):
            raise _MultimodalNotSupportedError from exc
        raise
    return _extract_content(resp.json())


async def summarize_post(post: TruthPost) -> AISummaryResult | None:
    api_key = config.trumpwatcher_ai_api_key.strip()
    if not api_key:
        return None

    source_text = post.content.strip()
    if not source_text:
        return None

    source_text = source_text[: config.trumpwatcher_ai_max_chars]
    image_urls = _collect_image_urls(post.media)

    async def _attempt() -> AISummaryResult | None:
        try:
            raw = await _request_summary(source_text, image_urls)
        except _MultimodalNotSupportedError:
            logger.warning("当前模型不支持图片输入，已降级为纯文本总结")
            try:
                raw = await _request_summary(source_text, [])
            except Exception:
                logger.exception("AI 文本总结请求失败")
                return None
        except Exception:
            logger.exception("AI 翻译总结请求失败")
            return None
        if not raw:
            return None
        return _parse_title_summary(raw)

    for attempt in range(_MAX_RETRIES):
        result = await _attempt()
        if result is not None:
            return result
        if attempt < _MAX_RETRIES - 1:
            logger.warning(f"AI 输出解析失败，正在重试 ({attempt + 2}/{_MAX_RETRIES})")

    logger.warning(f"AI 输出解析失败已达 {_MAX_RETRIES} 次，降级为时间戳标题")
    from datetime import timezone, timedelta

    beijing_time = post.created_at.astimezone(timezone(timedelta(hours=8))).strftime("%m-%d %H:%M")
    return AISummaryResult(title=beijing_time, summary=source_text)
