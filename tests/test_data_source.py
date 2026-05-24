from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from nonebot_plugin_trumpwatcher.data_source import (
    TruthPost,
    filter_new_posts,
    format_post_message,
)


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


class TestFilterNewPosts:
    def test_skip_empty_enabled(self):
        posts = [
            make_post("1", content="valid"),
            make_post("2", content="   "),                       # whitespace only, no media → skip
            make_post("3", content=""),                          # empty, no media → skip
            make_post("4", content="", media=("https://img/1.jpg",)),  # empty but has media → keep
        ]
        result = filter_new_posts(posts, set(), None, skip_empty=True)
        ids = {p.post_id for p in result}
        assert ids == {"1", "4"}

    def test_skip_empty_image_only_post_passes(self):
        """纯图推文（无正文有图片）应放行"""
        posts = [
            make_post("img1", content="", media=("https://img/a.jpg",)),
            make_post("img2", content="", media=("https://img/b.jpg", "https://img/c.jpg")),
        ]
        result = filter_new_posts(posts, set(), None, skip_empty=True)
        assert len(result) == 2

    def test_skip_empty_disabled(self):
        posts = [
            make_post("1", content="valid"),
            make_post("2", content="   "),
        ]
        result = filter_new_posts(posts, set(), None, skip_empty=False)
        assert len(result) == 2

    def test_skip_empty_default_disabled_keeps_all(self):
        posts = [
            make_post("1", content="valid"),
            make_post("2", content=""),
        ]
        result = filter_new_posts(posts, set(), None, skip_empty=False)
        assert len(result) == 2

    def test_filters_archived_ids(self):
        posts = [make_post("1"), make_post("2")]
        result = filter_new_posts(posts, {"1"}, None)
        assert len(result) == 1
        assert result[0].post_id == "2"

    def test_filters_reposts(self):
        posts = [
            make_post("1", content="RT @someone: hello"),
            make_post("2", content="original"),
        ]
        result = filter_new_posts(posts, set(), None)
        assert len(result) == 1
        assert result[0].post_id == "2"

    def test_filters_by_timestamp(self):
        t1 = datetime(2025, 5, 25, 6, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2025, 5, 25, 7, 0, 0, tzinfo=timezone.utc)
        posts = [
            make_post("1", created_at=t1),
            make_post("2", created_at=t2),
        ]
        result = filter_new_posts(posts, set(), t2)
        assert len(result) == 0

    def test_deduplicates_within_batch(self):
        posts = [
            make_post("1"),
            make_post("1"),
        ]
        result = filter_new_posts(posts, set(), None)
        assert len(result) == 1

    def test_skip_empty_with_repost_and_archive_combined(self):
        """Combined: skip (empty+no-media) + filter RT + filter archived + keep image-only."""
        t = datetime(2025, 5, 25, 6, 0, 0, tzinfo=timezone.utc)
        posts = [
            make_post("1", content="valid new"),
            make_post("2", content=""),                                          # empty, no media → skip
            make_post("3", content="RT @someone: repost"),
            make_post("4", content="   "),                                       # whitespace, no media → skip
            make_post("5", content="another valid"),
            make_post("6", content="", media=("https://img/x.png",)),            # empty but has media → keep
        ]
        result = filter_new_posts(posts, set(), None, skip_empty=True)
        ids = {p.post_id for p in result}
        assert ids == {"1", "5", "6"}


class TestFormatPostMessage:
    def test_no_verbose_prefix(self):
        post = make_post(content="Hello world")
        result = format_post_message(post)
        assert "特朗普Truth Social新动态" not in result
        assert "发布时间" not in result

    def test_includes_content(self):
        post = make_post(content="Hello world")
        result = format_post_message(post)
        assert "Hello world" in result

    def test_includes_url(self):
        post = make_post(url="https://truthsocial.com/test")
        result = format_post_message(post)
        assert "https://truthsocial.com/test" in result

    def test_includes_media_urls(self):
        post = make_post(
            content="test",
            media=("https://img.example.com/1.jpg", "https://img.example.com/2.jpg"),
        )
        result = format_post_message(post)
        assert "https://img.example.com/1.jpg" in result
        assert "https://img.example.com/2.jpg" in result

    def test_empty_content_shows_placeholder(self):
        post = make_post(content="")
        result = format_post_message(post)
        assert "(无正文)" in result

    def test_beijing_time_format(self):
        post = make_post(
            created_at=datetime(2025, 5, 25, 6, 30, 0, tzinfo=timezone.utc)
        )
        result = format_post_message(post)
        assert "05-25 14:30" in result
