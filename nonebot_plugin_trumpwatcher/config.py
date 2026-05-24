from pydantic import BaseModel, Field
from nonebot.plugin import get_plugin_config


class Config(BaseModel):
    trumpwatcher_source_url: str = Field(
        default="https://ix.cnn.io/data/truth-social/truth_archive.json"
    )
    trumpwatcher_fetch_limit: int = Field(default=20, ge=1, le=100)
    trumpwatcher_timeout: float = Field(default=20.0, gt=0)
    trumpwatcher_forward_user_id: int = Field(default=10000, ge=1)
    trumpwatcher_forward_nickname: str = Field(default="特朗普观察员")
    trumpwatcher_ai_summary_enabled: bool = Field(default=False)
    trumpwatcher_ai_summary_max_posts: int = Field(default=3, ge=0, le=100)
    trumpwatcher_ai_api_base: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    trumpwatcher_ai_api_key: str = Field(default="")
    trumpwatcher_ai_model: str = Field(default="qwen-plus")
    trumpwatcher_ai_timeout: float = Field(default=20.0, gt=0)
    trumpwatcher_ai_temperature: float = Field(default=0.2, ge=0, le=2)
    trumpwatcher_ai_max_chars: int = Field(default=2000, ge=200, le=20000)
    trumpwatcher_ai_multimodal_enabled: bool = Field(default=True)
    trumpwatcher_ai_multimodal_max_images: int = Field(default=3, ge=0, le=10)
    trumpwatcher_auto_fetch_enabled: bool = Field(default=False)
    trumpwatcher_auto_fetch_cron: str = Field(default="*/10 * * * *")
    trumpwatcher_auto_fetch_timezone: str = Field(default="Asia/Shanghai")
    trumpwatcher_skip_empty_content: bool = Field(default=True)


config = get_plugin_config(Config)
