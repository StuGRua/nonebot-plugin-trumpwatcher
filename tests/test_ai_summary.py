from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from nonebot_plugin_trumpwatcher.ai_summary import (
    AISummaryResult,
    _looks_like_url,
    _parse_title_summary,
    _collect_image_urls,
    _MultimodalNotSupportedError,
)


class TestParseTitleSummary:
    def test_valid_chinese_labels(self):
        text = "标题：特朗普发表重要演讲\n概要：特朗普在海湖庄园发表了关于经济政策的重要演讲。"
        result = _parse_title_summary(text)
        assert result is not None
        assert result.title == "特朗普发表重要演讲"
        assert "经济政策" in result.summary

    def test_valid_english_colon(self):
        text = "标题: Short title\n概要: A detailed summary of the post."
        result = _parse_title_summary(text)
        assert result is not None
        assert result.title == "Short title"
        assert result.summary == "A detailed summary of the post."

    def test_multiline_summary(self):
        text = "标题：多行概要测试\n概要：第一行\n第二行\n第三行"
        result = _parse_title_summary(text)
        assert result is not None
        assert result.title == "多行概要测试"
        assert "第一行" in result.summary
        assert "第二行" in result.summary

    def test_missing_title_returns_none(self):
        text = "概要：只有概要没有标题"
        result = _parse_title_summary(text)
        assert result is None

    def test_missing_summary_returns_none(self):
        text = "标题：只有标题没有概要"
        result = _parse_title_summary(text)
        assert result is None

    def test_empty_title_returns_none(self):
        text = "标题： \n概要：有概要"
        result = _parse_title_summary(text)
        assert result is None

    def test_empty_summary_returns_none(self):
        text = "标题：有标题\n概要： "
        result = _parse_title_summary(text)
        assert result is None

    def test_no_labels_returns_none(self):
        text = "这是一段没有任何标签的文本"
        result = _parse_title_summary(text)
        assert result is None

    def test_title_contains_newline_separator(self):
        text = "标题：特朗普新政\n概要：详情如下。"
        result = _parse_title_summary(text)
        assert result is not None
        assert result.title == "特朗普新政"
        assert result.summary == "详情如下。"

    def test_title_strips_whitespace(self):
        text = "标题：  有空格标题  \n概要：  有空格概要  "
        result = _parse_title_summary(text)
        assert result is not None
        assert result.title == "有空格标题"
        assert result.summary == "有空格概要"

    def test_labels_not_at_line_start_still_match(self):
        text = "前面有些内容 标题：测试标题\n更多内容 概要：测试概要详情"
        result = _parse_title_summary(text)
        assert result is not None
        assert result.title == "测试标题"
        assert result.summary == "测试概要详情"

    def test_empty_string(self):
        result = _parse_title_summary("")
        assert result is None

    def test_title_without_summary_body(self):
        text = "标题：只有标题\n概要："
        result = _parse_title_summary(text)
        assert result is None


class TestAISummaryResult:
    def test_create_and_access(self):
        r = AISummaryResult(title="T", summary="S")
        assert r.title == "T"
        assert r.summary == "S"

    def test_slots_no_dict(self):
        r = AISummaryResult(title="T", summary="S")
        with pytest.raises(AttributeError):
            r.__dict__


class TestLooksLikeUrl:
    def test_http_url(self):
        assert _looks_like_url("http://example.com/image.jpg")

    def test_https_url(self):
        assert _looks_like_url("https://example.com/image.jpg")

    def test_non_url_string(self):
        assert not _looks_like_url("not_a_url")

    def test_empty_string(self):
        assert not _looks_like_url("")

    def test_ftp_not_recognized(self):
        assert not _looks_like_url("ftp://example.com/file")

    def test_no_scheme(self):
        assert not _looks_like_url("example.com/image.jpg")


class TestCollectImageUrls:
    def test_collects_image_urls(self, monkeypatch):
        monkeypatch.setattr(
            "nonebot_plugin_trumpwatcher.ai_summary.config.trumpwatcher_ai_multimodal_enabled",
            True,
        )
        monkeypatch.setattr(
            "nonebot_plugin_trumpwatcher.ai_summary.config.trumpwatcher_ai_multimodal_max_images",
            3,
        )
        urls = _collect_image_urls(
            ("https://example.com/1.jpg", "not_a_url", "https://example.com/2.png")
        )
        assert len(urls) == 2
        assert urls[0] == "https://example.com/1.jpg"

    def test_respects_max_images(self, monkeypatch):
        monkeypatch.setattr(
            "nonebot_plugin_trumpwatcher.ai_summary.config.trumpwatcher_ai_multimodal_enabled",
            True,
        )
        monkeypatch.setattr(
            "nonebot_plugin_trumpwatcher.ai_summary.config.trumpwatcher_ai_multimodal_max_images",
            1,
        )
        urls = _collect_image_urls(
            ("https://example.com/1.jpg", "https://example.com/2.jpg")
        )
        assert len(urls) == 1

    def test_disabled_returns_empty(self, monkeypatch):
        monkeypatch.setattr(
            "nonebot_plugin_trumpwatcher.ai_summary.config.trumpwatcher_ai_multimodal_enabled",
            False,
        )
        urls = _collect_image_urls(("https://example.com/1.jpg",))
        assert urls == []

    def test_zero_max_returns_empty(self, monkeypatch):
        monkeypatch.setattr(
            "nonebot_plugin_trumpwatcher.ai_summary.config.trumpwatcher_ai_multimodal_enabled",
            True,
        )
        monkeypatch.setattr(
            "nonebot_plugin_trumpwatcher.ai_summary.config.trumpwatcher_ai_multimodal_max_images",
            0,
        )
        urls = _collect_image_urls(("https://example.com/1.jpg",))
        assert urls == []


class TestMultimodalNotSupportedError:
    def test_is_exception(self):
        err = _MultimodalNotSupportedError("test")
        assert isinstance(err, Exception)

    def test_can_catch_separately(self):
        try:
            raise _MultimodalNotSupportedError("not supported")
        except _MultimodalNotSupportedError:
            pass
        except Exception:
            pytest.fail("Should have been caught by _MultimodalNotSupportedError")
