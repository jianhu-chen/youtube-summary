# youtube-summary

通用 AI agent skill，将 YouTube 视频转录为 Markdown 报告。

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

```
/youtube-summary <youtube-url>
```

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
/youtube-summary <youtube-url> 请用英文撰写报告
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

1. 📥 **下载** — 通过 yt-dlp 获取音频
2. ✂️ **分段** — 超过 50 分钟自动切分，所有分片统一压缩至 32k mono
3. 🎙️ **转录** — 并行调用 OpenAI 兼容 Whisper ASR API（最大并发 4）
4. 🤖 **总结** — AI 生成 Highlights + 详细文字版
5. 📄 **输出** — 在当前目录保存 `.md` 报告

## 🔗 相关项目

- [bilibili-summary](https://github.com/jianhu-chen/bilibili-summary) — 将哔哩哔哩视频转录为 Markdown 报告

## 📄 许可证

MIT
