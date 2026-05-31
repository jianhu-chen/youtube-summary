# youtube-summary

通用 AI agent skill，用于转录 YouTube 视频并生成结构化报告。

**[🏠 GitHub](https://github.com/jianhu-chen/youtube-summary)** | **[🇬🇧 English](README.md)**

## ✨ 功能

- [x] 通过 yt-dlp 下载 YouTube 音频
- [x] 通过 OpenAI 兼容 Whisper API 进行 ASR 语音转文字（长视频自动并行处理）
- [x] AI 生成包含 Highlights 和视频详情的 Markdown 报告
- [x] 超过 50 分钟的视频自动分段处理
- [x] 自动安装缺失依赖（yt-dlp、ffmpeg）
- [x] 可自定义报告语言 — 默认使用视频原语言，追加到命令后或直接用自然语言告诉 Agent 即可覆盖（详见[语言](#语言)）

## 📦 安装

```bash
npx skills add jianhu-chen/youtube-summary
```

安装到指定 agent：

```bash
# Claude Code
npx skills add jianhu-chen/youtube-summary -a claude-code

# Cursor
npx skills add jianhu-chen/youtube-summary -a cursor

# Codex
npx skills add jianhu-chen/youtube-summary -a codex
```

全局安装（所有项目可用）：

```bash
npx skills add jianhu-chen/youtube-summary -g
```

## 🚀 使用

本包提供**两个技能**，可搭配使用或独立使用：

### 第 1 步：转录视频

```
/youtube-transcribe <youtube-url>
```

下载音频、运行 ASR、输出完整转录文本，直接显示在对话中。

### 第 2 步：生成报告

```
/youtube-report [语言偏好]
```

接收对话中的转录文本，生成包含 Highlights 和 Video Details 的格式化 Markdown 报告。报告直接渲染在对话中 — 不保存文件到磁盘。

> **提示：** `/youtube-report` 是通用的 — 适用于任何来源的转录文本（YouTube、Bilibili、粘贴文本），不限于 `/youtube-transcribe`。

## ⚙️ 配置

| 环境变量 | 必填 | 默认值 | 说明 |
|---------|------|-------|------|
| `ASR_API_KEY` | ✅ 是 | - | Whisper 兼容 ASR 服务的 API 密钥 |
| `ASR_MODEL` | 否 | `whisper-1` | ASR 模型名称 |
| `ASR_BASE_URL` | 否 | `https://api.openai.com/v1` | 自定义 API 基础 URL |

## 🌐 语言

默认情况下，报告使用与视频相同的语言撰写，技术术语保留原文。

如需指定其他语言，请在请求中说明，例如：

```
/youtube-report 请用英文撰写报告
```

## 📋 依赖

缺失的依赖会在首次运行时由 Agent 自动安装。

| 依赖 | macOS | Linux (Debian/Ubuntu) |
|------|-------|----------------------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | `brew install yt-dlp` 或 `pip3 install yt-dlp` | `pip3 install yt-dlp` |
| [ffmpeg](https://ffmpeg.org/) | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| Python 3 | 系统自带 或 `brew install python3` | `sudo apt install python3` |
| curl | 系统自带 或 `brew install curl` | `sudo apt install curl` |

## ⚡ 工作原理

### `/youtube-transcribe`
1. 📥 **下载** — 通过 yt-dlp 获取音频
2. ✂️ **分段** — 超过 50 分钟自动切分，所有分片统一压缩至 32k mono
3. 🎙️ **转录** — 并行调用 OpenAI 兼容 Whisper ASR API（最大并发 4）
4. 📝 **输出** — 在对话中展示完整转录文本

### `/youtube-report`
1. 📖 **读取** — 从对话上下文中获取转录文本
2. 🤖 **总结** — AI 生成 Highlights + 详细文字版
3. 📄 **输出** — 在对话中渲染格式化报告

## 🔗 相关项目

- [bilibili-summary](https://github.com/jianhu-chen/bilibili-summary) — 将哔哩哔哩视频转录为 Markdown 报告

## 📄 许可证

MIT
