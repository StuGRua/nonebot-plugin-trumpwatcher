from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from nonebot import get_bots, get_driver, logger, on_command, require
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

require("nonebot_plugin_orm")
from nonebot_plugin_orm import AsyncSession, get_session

try:
    require("nonebot_plugin_apscheduler")
    from apscheduler.jobstores.base import JobLookupError
    from apscheduler.triggers.cron import CronTrigger
    from nonebot_plugin_apscheduler import scheduler
except Exception:
    CronTrigger = None
    JobLookupError = Exception
    scheduler = None

from .ai_summary import AISummaryResult, summarize_post
from .config import Config, config
from .data_source import (
    BEIJING_TZ,
    TruthPost,
    fetch_archive_posts,
    filter_new_posts,
    format_post_message,
)
from .model import NotifyGroup, PostArchive

__plugin_meta__ = PluginMetadata(
    name="特朗普社媒监控",
    description="监控特朗普 Truth Social 动态并推送到订阅群",
    usage=(
        "trump社媒拉取 — 手动拉取最新动态\n"
        "trump社媒订阅 — 订阅本群推送（需管理员）\n"
        "trump社媒取消订阅 — 取消本群推送（需管理员）\n"
        "trump社媒状态 — 查看当前群订阅状态\n"
        "trump社媒订阅列表 — 查看所有订阅群（仅SUPERUSER）"
    ),
    type="application",
    homepage="https://github.com/StuGRua/nonebot-plugin-trumpwatcher",
    config=Config,
    supported_adapters={"~onebot.v11"},
)

fetch_cmd = on_command(
    "trump社媒拉取",
    aliases={"trump", "trump_fetch", "trumpwatcher_fetch"},
    block=True,
    priority=10,
)
subscribe_cmd = on_command(
    "trump社媒订阅",
    aliases={"trump_sub", "trumpwatcher_sub"},
    block=True,
    priority=10,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
)
unsubscribe_cmd = on_command(
    "trump社媒取消订阅",
    aliases={"trump_unsub", "trumpwatcher_unsub"},
    block=True,
    priority=10,
    permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER,
)
status_cmd = on_command(
    "trump社媒状态",
    aliases={"trump_status", "trumpwatcher_status"},
    block=True,
    priority=10,
)
list_cmd = on_command(
    "trump社媒订阅列表",
    aliases={"trump_list", "trumpwatcher_list"},
    block=True,
    priority=10,
    permission=SUPERUSER,
)

_AUTO_FETCH_JOB_ID = "nonebot_plugin_trumpwatcher:auto_fetch"
_fetch_lock = asyncio.Lock()
_driver = get_driver()


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _pick_onebot_v11_bot() -> Bot | None:
    for bot in get_bots().values():
        if isinstance(bot, Bot):
            return bot
    return None


def _build_cron_trigger() -> CronTrigger | None:
    if CronTrigger is None:
        return None
    try:
        tz = ZoneInfo(config.trumpwatcher_auto_fetch_timezone)
    except ZoneInfoNotFoundError:
        logger.error(
            "trumpwatcher_auto_fetch_timezone 无效: "
            f"{config.trumpwatcher_auto_fetch_timezone}"
        )
        return None
    try:
        return CronTrigger.from_crontab(config.trumpwatcher_auto_fetch_cron, timezone=tz)
    except ValueError:
        logger.error(
            "trumpwatcher_auto_fetch_cron 无效: "
            f"{config.trumpwatcher_auto_fetch_cron}"
        )
        return None


def _register_auto_fetch_job() -> None:
    if scheduler is None:
        if config.trumpwatcher_auto_fetch_enabled:
            logger.warning(
                "已启用自动拉取，但 nonebot_plugin_apscheduler 不可用，已跳过定时任务注册"
            )
        return

    with suppress(JobLookupError):
        scheduler.remove_job(_AUTO_FETCH_JOB_ID)

    if not config.trumpwatcher_auto_fetch_enabled:
        logger.info("特朗普社媒自动拉取未启用")
        return

    trigger = _build_cron_trigger()
    if trigger is None:
        return

    scheduler.add_job(
        _run_scheduled_fetch,
        trigger=trigger,
        id=_AUTO_FETCH_JOB_ID,
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )
    logger.info(
        "已注册特朗普社媒自动拉取任务: "
        f"cron={config.trumpwatcher_auto_fetch_cron}, "
        f"timezone={config.trumpwatcher_auto_fetch_timezone}"
    )


async def _render_post_content(post: TruthPost, index: int) -> str:
    content = format_post_message(post)
    if (
        config.trumpwatcher_ai_summary_enabled
        and index < config.trumpwatcher_ai_summary_max_posts
    ):
        ai_result: AISummaryResult | None = await summarize_post(post)
        if ai_result:
            return f"{ai_result.title}\n\n{ai_result.summary}\n\n{content}"
    return content


async def _fetch_and_forward(bot: Bot, session: AsyncSession) -> str:
    async with _fetch_lock:
        try:
            posts = await fetch_archive_posts(limit=config.trumpwatcher_fetch_limit)
        except httpx.TimeoutException:
            logger.warning("拉取特朗普社媒超时")
            return "获取动态超时，请稍后再试。"
        except httpx.HTTPStatusError:
            logger.warning("拉取特朗普社媒数据源错误")
            return "数据源暂时不可用，请稍后再试。"
        except Exception:
            logger.exception("拉取特朗普社媒归档失败")
            return "获取动态失败，请稍后重试。"

        if not posts:
            return "未获取到可用动态。"

        archived_ids_result = await session.execute(
            select(PostArchive.post_id).where(
                PostArchive.post_id.in_([p.post_id for p in posts])
            )
        )
        archived_ids = set(archived_ids_result.scalars().all())
        latest_archived = _normalize_utc(
            await session.scalar(select(func.max(PostArchive.created_at)))
        )

        new_posts: list[TruthPost] = filter_new_posts(
            posts, archived_ids, latest_archived,
            skip_empty=config.trumpwatcher_skip_empty_content,
        )
        if not new_posts:
            return "暂无新的特朗普社媒动态。"

        session.add_all(
            [
                PostArchive(
                    post_id=post.post_id,
                    created_at=post.created_at,
                    content=post.content,
                    url=post.url,
                    media_text="\n".join(post.media),
                )
                for post in new_posts
            ]
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.warning("检测到并发拉取导致归档冲突")
            return "操作太频繁啦，请稍后再试。"

        group_ids_result = await session.execute(select(NotifyGroup.group_id))
        group_ids = list(group_ids_result.scalars().all())
        if not group_ids:
            return f"已记录 {len(new_posts)} 条新动态，当前无订阅群。"

        beijing_now = datetime.now(BEIJING_TZ).strftime("%m-%d %H:%M")
        title = f"特朗普最新 {len(new_posts)} 条动态 | {beijing_now}"
        nodes = [
            MessageSegment.node_custom(
                user_id=config.trumpwatcher_forward_user_id,
                nickname=config.trumpwatcher_forward_nickname,
                content=Message(MessageSegment.text(title)),
            )
        ]
        nodes.extend(
            MessageSegment.node_custom(
                user_id=config.trumpwatcher_forward_user_id,
                nickname=" ",
                content=Message(MessageSegment.text(await _render_post_content(post, index))),
            )
            for index, post in enumerate(new_posts)
        )

        success_count = 0
        failed_groups: list[int] = []
        for group_id in group_ids:
            try:
                await bot.call_api(
                    "send_group_forward_msg", group_id=group_id, messages=nodes
                )
                success_count += 1
            except Exception:
                failed_groups.append(group_id)
                logger.exception(f"推送特朗普社媒动态失败，group_id={group_id}")

        failed_text = (
            f"，失败群: {', '.join(map(str, failed_groups))}" if failed_groups else ""
        )
        return (
            f"拉取完成：新增 {len(new_posts)} 条，"
            f"推送 {success_count}/{len(group_ids)} 个群{failed_text}"
        )


async def _run_scheduled_fetch() -> None:
    bot = _pick_onebot_v11_bot()
    if bot is None:
        logger.warning("自动拉取触发时未发现 OneBot V11 Bot 连接，已跳过")
        return

    try:
        async with get_session() as session:
            result = await _fetch_and_forward(bot, session)
        logger.info(f"特朗普社媒自动拉取结果: {result}")
    except Exception:
        logger.exception("特朗普社媒自动拉取执行失败")


@_driver.on_startup
async def _startup_register_job() -> None:
    _register_auto_fetch_job()


@fetch_cmd.handle()
async def handle_fetch(bot: Bot, session: AsyncSession) -> None:
    result = await _fetch_and_forward(bot, session)
    await fetch_cmd.finish(result)


@subscribe_cmd.handle()
async def handle_subscribe(event: GroupMessageEvent, session: AsyncSession) -> None:
    if await session.get(NotifyGroup, event.group_id):
        await subscribe_cmd.finish("当前群已订阅特朗普社媒动态。")
    session.add(NotifyGroup(group_id=event.group_id))
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        await subscribe_cmd.finish("当前群已订阅特朗普社媒动态。")
    await subscribe_cmd.finish("订阅成功。")


@unsubscribe_cmd.handle()
async def handle_unsubscribe(event: GroupMessageEvent, session: AsyncSession) -> None:
    record = await session.get(NotifyGroup, event.group_id)
    if record is None:
        await unsubscribe_cmd.finish("当前群未订阅特朗普社媒动态。")
    await session.delete(record)
    await session.commit()
    await unsubscribe_cmd.finish("已取消订阅。")


@status_cmd.handle()
async def handle_status(event: GroupMessageEvent, session: AsyncSession) -> None:
    record = await session.get(NotifyGroup, event.group_id)
    if record is None:
        last_fetch = await session.scalar(select(func.max(PostArchive.fetched_at)))
        last_str = (
            last_fetch.astimezone(BEIJING_TZ).strftime("%m-%d %H:%M")
            if last_fetch
            else "暂无"
        )
        await status_cmd.finish(
            f"当前群未订阅。\n上次全局拉取: {last_str}"
        )
    sub_time = record.created_at.astimezone(BEIJING_TZ).strftime("%m-%d %H:%M")
    last_fetch = await session.scalar(select(func.max(PostArchive.fetched_at)))
    last_str = (
        last_fetch.astimezone(BEIJING_TZ).strftime("%m-%d %H:%M")
        if last_fetch
        else "暂无"
    )
    await status_cmd.finish(
        f"已订阅特朗普社媒动态。\n订阅时间: {sub_time}\n上次拉取: {last_str}"
    )


@list_cmd.handle()
async def handle_list(session: AsyncSession) -> None:
    records_result = await session.execute(
        select(NotifyGroup).order_by(NotifyGroup.created_at)
    )
    records = list(records_result.scalars().all())
    if not records:
        await list_cmd.finish("当前无任何群订阅。")
    lines = [f"共 {len(records)} 个群订阅："]
    for r in records:
        t = r.created_at.astimezone(BEIJING_TZ).strftime("%m-%d %H:%M")
        lines.append(f"  群 {r.group_id}（{t} 订阅）")
    await list_cmd.finish("\n".join(lines))
