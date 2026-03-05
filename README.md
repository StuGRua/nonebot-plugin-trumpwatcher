# nonebot-plugin-trumpwatcher

<div align="center">

_✨ 监控特朗普 Truth Social 动态并推送到订阅群 ✨_

<a href="./LICENSE">
    <img src="https://img.shields.io/github/license/StuGRua/nonebot-plugin-trumpwatcher.svg" alt="license">
</a>
<a href="https://pypi.python.org/pypi/nonebot-plugin-trumpwatcher">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-trumpwatcher.svg" alt="pypi">
</a>
<img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="python">

</div>

## 📖 介绍

一个用于监控特朗普 Truth Social 动态的 NoneBot2 插件,支持自动拉取、群组订阅推送和 AI 翻译总结。

## 💿 安装

<details open>
<summary>使用 nb-cli 安装（推荐）</summary>

在 NoneBot2 项目的根目录下打开命令行,输入以下指令即可安装:

```bash
nb plugin install nonebot-plugin-trumpwatcher
```

</details>

<details>
<summary>使用包管理器安装</summary>

在 NoneBot2 项目的插件目录下,打开命令行,根据你使用的包管理器,输入相应的安装命令:

<details>
<summary>pip</summary>

```bash
pip install nonebot-plugin-trumpwatcher
```

</details>

<details>
<summary>pdm</summary>

```bash
pdm add nonebot-plugin-trumpwatcher
```

</details>

<details>
<summary>poetry</summary>

```bash
poetry add nonebot-plugin-trumpwatcher
```

</details>

<details>
<summary>conda</summary>

```bash
conda install nonebot-plugin-trumpwatcher
```

</details>

打开 NoneBot2 项目根目录下的 `pyproject.toml` 文件,在 `[tool.nonebot]` 部分追加写入:

```toml
plugins = ["nonebot_plugin_trumpwatcher"]
```

</details>

## 🎉 数据源

- [CNN Truth Social Archive](https://ix.cnn.io/data/truth-social/truth_archive.json)
- 免费公开接口,无需代理,约每 5 分钟更新一次

## 📝 依赖

- NoneBot2 >= 2.4.0
- nonebot-adapter-onebot >= 2.4.0
- [nonebot-plugin-orm](https://github.com/nonebot/plugin-orm) >= 0.8.0
- [nonebot-plugin-apscheduler](https://github.com/nonebot/plugin-apscheduler) >= 0.4.0

> **注意**: 本插件不指定 NoneBot2 驱动器依赖，请根据你的需求在主项目中配置驱动器。
>
> 例如，在 `.env` 文件中配置：
> ```env
> DRIVER=~fastapi+~httpx+~websockets
> ```
>
> 并在主项目的 `pyproject.toml` 中安装对应的驱动器包（如果使用 poetry）：
> ```bash
> poetry add nonebot2[fastapi,websockets]
> ```

## ⚙️ 配置

在 NoneBot2 项目的 `.env` 文件中添加以下配置项（未配置则使用默认值）:

### 基础配置

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `TRUMPWATCHER_SOURCE_URL` | `str` | `https://ix.cnn.io/data/truth-social/truth_archive.json` | 数据源地址 |
| `TRUMPWATCHER_FETCH_LIMIT` | `int` | `20` | 每次拉取并比对的最大条数（1-100） |
| `TRUMPWATCHER_TIMEOUT` | `float` | `20.0` | 拉取数据超时（秒） |
| `TRUMPWATCHER_FORWARD_USER_ID` | `int` | `10000` | 合并转发节点显示的 QQ 号 |
| `TRUMPWATCHER_FORWARD_NICKNAME` | `str` | `特朗普观察员` | 合并转发节点显示昵称 |

### AI 翻译总结配置

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `TRUMPWATCHER_AI_SUMMARY_ENABLED` | `bool` | `false` | 是否启用 AI 翻译总结 |
| `TRUMPWATCHER_AI_SUMMARY_MAX_POSTS` | `int` | `3` | 每次拉取最多对前 N 条追加 AI 总结（0-100） |
| `TRUMPWATCHER_AI_PROVIDER` | `str` | `qwen` | AI 服务提供方标识 |
| `TRUMPWATCHER_AI_API_BASE` | `str` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | AI API Base URL |
| `TRUMPWATCHER_AI_API_KEY` | `str` | `""` | AI API Key（开启 AI 时必填） |
| `TRUMPWATCHER_AI_MODEL` | `str` | `qwen-plus` | AI 模型名 |
| `TRUMPWATCHER_AI_TIMEOUT` | `float` | `20.0` | AI 请求超时（秒） |
| `TRUMPWATCHER_AI_TEMPERATURE` | `float` | `0.2` | AI 生成温度（0-2） |
| `TRUMPWATCHER_AI_MAX_CHARS` | `int` | `2000` | 单条动态送入 AI 的最大字符数（200-20000） |
| `TRUMPWATCHER_AI_MULTIMODAL_ENABLED` | `bool` | `true` | 是否启用图片多模态输入 |
| `TRUMPWATCHER_AI_MULTIMODAL_MAX_IMAGES` | `int` | `3` | 单条动态最多传入的图片 URL 数量（0-10） |

### 自动推送配置

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `TRUMPWATCHER_AUTO_FETCH_ENABLED` | `bool` | `false` | 是否启用自动拉取并推送 |
| `TRUMPWATCHER_AUTO_FETCH_CRON` | `str` | `*/10 * * * *` | 自动拉取 cron（5 段 crontab 表达式） |
| `TRUMPWATCHER_AUTO_FETCH_TIMEZONE` | `str` | `Asia/Shanghai` | 自动拉取时区 |

### 配置示例

```env
# 基础配置
TRUMPWATCHER_FETCH_LIMIT=20
TRUMPWATCHER_TIMEOUT=20.0

# 启用 AI 翻译总结
TRUMPWATCHER_AI_SUMMARY_ENABLED=true
TRUMPWATCHER_AI_API_KEY=your_api_key_here
TRUMPWATCHER_AI_MODEL=qwen-plus

# 启用自动推送（每 5 分钟）
TRUMPWATCHER_AUTO_FETCH_ENABLED=true
TRUMPWATCHER_AUTO_FETCH_CRON=*/5 * * * *
```

## 🎮 使用

### 命令列表

| 命令 | 别名 | 权限 | 说明 |
| --- | --- | --- | --- |
| `trump社媒拉取` | `trump` / `trump_fetch` / `trumpwatcher_fetch` | 任意群成员 | 拉取最新动态、归档并推送到所有订阅群 |
| `trump社媒订阅` | `trump_sub` / `trumpwatcher_sub` | 群管理员/群主/SUPERUSER | 当前群加入推送列表 |
| `trump社媒取消订阅` | `trump_unsub` / `trumpwatcher_unsub` | 群管理员/群主/SUPERUSER | 当前群移出推送列表 |

### 使用流程

1. **订阅推送**: 在需要接收推送的群中发送 `trump社媒订阅`
2. **手动拉取**: 发送 `trump社媒拉取` 立即拉取最新动态
3. **自动推送**: 配置 `TRUMPWATCHER_AUTO_FETCH_ENABLED=true` 启用定时自动推送
4. **取消订阅**: 发送 `trump社媒取消订阅` 停止接收推送

## 🔧 数据库迁移

首次启用或升级表结构后执行:

```bash
nb orm upgrade
```

涉及表:
- `trumpwatcher_post_archive`: 动态归档
- `trumpwatcher_notify_group`: 订阅群列表

## 💡 AI 翻译总结说明

- 默认使用千问（Qwen）兼容接口
- 启用后会在转发内容后追加"AI翻译总结"
- 支持多模态图片输入（需模型支持）
- 如果模型不支持图片,会自动降级为纯文本总结
- 请求失败时自动降级为仅发送原始消息,不影响主流程

## 📄 许可证

本项目使用 [MIT](./LICENSE) 许可证。

## 📦 发布信息

- PyPI: https://pypi.org/project/nonebot-plugin-trumpwatcher/
- GitHub: https://github.com/StuGRua/nonebot-plugin-trumpwatcher

## 🔧 开发者须知

如果你想参与开发或了解插件的最佳实践，请查看 [MAINTENANCE.md](./MAINTENANCE.md)。

## 🙏 致谢

- 数据源: [CNN Truth Social Archive](https://ix.cnn.io/data/truth-social/truth_archive.json)
- 框架: [NoneBot2](https://github.com/nonebot/nonebot2)
