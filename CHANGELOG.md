# Changelog

## [1.1.0] - 2025-05-25

### Added
- 合并转发标题节点：外部预览显示"特朗普最新 N 条动态 | MM-DD HH:MM"，各帖文昵称精简
- AI 双参数输出：标题 + 概要分离，去掉"AI翻译总结："前缀
- AI 解析失败自动重试 3 次，仍失败降级为时间戳标题
- `trumpwatcher_skip_empty_content` 配置项，默认开启，纯图推文（无正文有图片）正常放行
- `trump社媒状态` 命令：查看当前群订阅状态和上次拉取时间
- `trump社媒订阅列表` 命令（SUPERUSER）：查看所有订阅群

### Changed
- 帖文格式精简：去掉"特朗普Truth Social新动态:"前缀和"发布时间:"标签
- 反馈消息去技术化：异常分类提示，不再暴露原始异常文本
- 帮助文本补充完整命令列表和权限说明

### Removed
- 死配置项 `TRUMPWATCHER_AI_PROVIDER`（代码从未使用）

### Fixed
- `_TITLE_PATTERN` 正则 `\s*` 跨行 bug 改为 `[ \t]*`

## [1.0.3] - 2025-03-06
### Fixed
- 修复 NoneBot 加载器对 hyphen 包名的兼容

## [1.0.2] - 2025-03-06
### Fixed
- 添加 NoneBot entry point

## [1.0.1] - 2025-03-06
### Fixed
- 添加 packages 配置修复模块导入错误

## [1.0.0] - 2025-03-06
### Added
- 初始发布：Trump Truth Social 监控、群订阅推送、AI 翻译总结
