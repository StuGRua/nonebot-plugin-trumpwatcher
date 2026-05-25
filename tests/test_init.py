from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nonebot_plugin_trumpwatcher.__init__ import (
    _fetch_and_forward,
    _normalize_utc,
    _render_post_content,
)
from nonebot_plugin_trumpwatcher.data_source import TruthPost


def make_post(
    post_id: str = "123",
    created_at: datetime | None = None,
    content: str = "test content",
    url: str = "https://truthsocial.com/@realDonaldTrump/123",
    media: tuple[str, ...] = (),
) -> TruthPost:
    if created_at is None:
        created_at = datetime(2025, 5, 25, 6, 0, 0, tzinfo=timezone.utc)
    return TruthPost(
        post_id=post_id,
        created_at=created_at,
        content=content,
        url=url,
        media=media,
    )


# ── _normalize_utc ──────────────────────────────────────────────

class TestNormalizeUtc:
    def test_none_returns_none(self):
        assert _normalize_utc(None) is None

    def test_naive_becomes_utc(self):
        naive = datetime(2025, 5, 25, 12, 0, 0)
        result = _normalize_utc(naive)
        assert result.tzinfo == timezone.utc
        assert result.hour == 12

    def test_aware_converted_to_utc(self):
        est = timezone(timedelta(hours=-5))
        aware = datetime(2025, 5, 25, 7, 0, 0, tzinfo=est)
        result = _normalize_utc(aware)
        assert result.tzinfo == timezone.utc
        assert result.hour == 12

    def test_already_utc_unchanged(self):
        utc_dt = datetime(2025, 5, 25, 8, 0, 0, tzinfo=timezone.utc)
        result = _normalize_utc(utc_dt)
        assert result == utc_dt


# ── _render_post_content ────────────────────────────────────────

@pytest.mark.asyncio
async def test_render_without_ai():
    post = make_post(content="Hello world")
    result = await _render_post_content(post, index=0)
    assert "Hello world" in result
    assert "https://truthsocial.com/@realDonaldTrump/123" in result


@pytest.mark.asyncio
async def test_render_with_ai_summary():
    from nonebot_plugin_trumpwatcher import ai_summary

    post = make_post(content="Some long content about policies")
    fake_result = ai_summary.AISummaryResult(title="AI-title", summary="AI-summary")

    # Patch summarize_post in __init__'s namespace (where _render_post_content looks it up)
    with patch("nonebot_plugin_trumpwatcher.__init__.summarize_post",
               AsyncMock(return_value=fake_result)):
        with patch("nonebot_plugin_trumpwatcher.__init__.config") as mock_cfg:
            mock_cfg.trumpwatcher_ai_summary_enabled = True
            mock_cfg.trumpwatcher_ai_summary_max_posts = 5
            result = await _render_post_content(post, index=0)

    assert "AI-title" in result
    assert "AI-summary" in result
    assert "Some long content" in result


@pytest.mark.asyncio
async def test_render_ai_respects_max_posts():
    from nonebot_plugin_trumpwatcher import ai_summary

    post = make_post(content="Content")
    fake_result = ai_summary.AISummaryResult(title="Title", summary="Summary")

    with patch("nonebot_plugin_trumpwatcher.__init__.summarize_post",
               AsyncMock(return_value=fake_result)):
        result = await _render_post_content(post, index=3)

    assert "Title" not in result


# ── _fetch_and_forward ──────────────────────────────────────────

INIT_MOD = "nonebot_plugin_trumpwatcher.__init__"


def _make_result_mock(values: list):
    """Build a mock that mimics SQLAlchemy Result: .scalars().all() → values."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


@pytest.mark.asyncio
async def test_fetch_and_forward_builds_nodes():
    """Core: verifies nodes are built from new posts — catches async_generator bugs."""
    posts = [
        make_post("1", content="First post"),
        make_post("2", content="Second post"),
    ]

    bot = MagicMock()
    bot.call_api = AsyncMock()

    session = MagicMock()
    session.execute = AsyncMock(side_effect=[
        _make_result_mock([]),          # archived_ids
        _make_result_mock([111, 222]),  # group_ids
    ])
    session.scalar = AsyncMock(return_value=None)
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    with (
        patch(f"{INIT_MOD}.fetch_archive_posts", AsyncMock(return_value=posts)),
        patch(f"{INIT_MOD}.filter_new_posts", return_value=posts),
    ):
        result = await _fetch_and_forward(bot, session)

    assert "新增 2 条" in result
    assert "推送 2/2 个群" in result
    assert bot.call_api.call_count == 2
    for call_args in bot.call_api.call_args_list:
        messages = call_args.kwargs["messages"]
        assert len(messages) == 3  # 1 title + 2 posts


@pytest.mark.asyncio
async def test_fetch_and_forward_no_new_posts():
    bot = MagicMock()
    bot.call_api = AsyncMock()
    session = MagicMock()
    session.execute = AsyncMock(return_value=_make_result_mock([]))
    session.scalar = AsyncMock(return_value=None)

    with (
        patch(f"{INIT_MOD}.fetch_archive_posts", AsyncMock(return_value=[make_post("x")])),
        patch(f"{INIT_MOD}.filter_new_posts", return_value=[]),
    ):
        result = await _fetch_and_forward(bot, session)

    assert "暂无新的特朗普社媒动态" in result
    bot.call_api.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_and_forward_no_subscribers():
    post = make_post("1", content="Test")
    bot = MagicMock()
    bot.call_api = AsyncMock()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[
        _make_result_mock([]),  # archived_ids
        _make_result_mock([]),  # group_ids
    ])
    session.scalar = AsyncMock(return_value=None)
    session.add_all = MagicMock()
    session.commit = AsyncMock()

    with (
        patch(f"{INIT_MOD}.fetch_archive_posts", AsyncMock(return_value=[post])),
        patch(f"{INIT_MOD}.filter_new_posts", return_value=[post]),
    ):
        result = await _fetch_and_forward(bot, session)

    assert "当前无订阅群" in result
    bot.call_api.assert_not_called()
