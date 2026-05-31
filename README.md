# youtube-summary

Universal AI agent skills for transcribing YouTube videos and generating structured reports.

**[🏠 GitHub](https://github.com/jianhu-chen/youtube-summary)** | **[🇨🇳 中文文档](README.zh-CN.md)**

## ✨ Features

- [x] Download YouTube audio via yt-dlp
- [x] ASR transcription via OpenAI-compatible Whisper API (parallel processing for long videos)
- [x] AI-powered summary with Highlights + Detailed transcript sections
- [x] Auto audio segmentation for videos > 50 minutes
- [x] Auto dependency installation (yt-dlp, ffmpeg)
- [x] Customizable report language — defaults to the video's language; override by appending to the command or telling the agent in natural language (see [Language](#language))

## 📦 Installation

```bash
npx skills add jianhu-chen/youtube-summary
```

Install to a specific agent:

```bash
# Claude Code
npx skills add jianhu-chen/youtube-summary -a claude-code

# Cursor
npx skills add jianhu-chen/youtube-summary -a cursor

# Codex
npx skills add jianhu-chen/youtube-summary -a codex
```

Install globally (available in all projects):

```bash
npx skills add jianhu-chen/youtube-summary -g
```

## 🚀 Usage

This package provides **two skills** that work together or independently:

### Step 1: Transcribe the video

```
/youtube-transcribe <youtube-url>
```

Downloads the audio, runs ASR, and outputs the full transcript text directly in the conversation.

### Step 2: Generate a report

```
/youtube-report [language preference]
```

Takes the transcript (already in the conversation) and generates a polished Markdown report with Highlights and Video Details sections. The report renders directly in the conversation — no file is saved to disk.

> **Tip:** `/youtube-report` is generic — it works with transcripts from any source (YouTube, Bilibili, pasted text), not just `/youtube-transcribe`.

## ⚙️ Configuration

| Environment Variable | Required | Default | Description |
|---------------------|----------|---------|-------------|
| `ASR_API_KEY` | ✅ Yes | - | API key for Whisper-compatible ASR service |
| `ASR_MODEL` | No | `whisper-1` | ASR model name |
| `ASR_BASE_URL` | No | `https://api.openai.com/v1` | Custom API base URL |

## 🌐 Language

By default, reports are written in the same language as the video. Technical terms are preserved in their original language.

To specify a different language for the report, include your language preference in your request, e.g.:

```
/youtube-report Please write the report in Simplified Chinese
```

## 📋 Dependencies

Missing dependencies will be auto-installed by the agent during the first run.

| Dependency | macOS | Linux (Debian/Ubuntu) |
|-----------|-------|----------------------|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | `brew install yt-dlp` or `pip3 install yt-dlp` | `pip3 install yt-dlp` |
| [ffmpeg](https://ffmpeg.org/) | `brew install ffmpeg` | `sudo apt install ffmpeg` |
| Python 3 | Pre-installed or `brew install python3` | `sudo apt install python3` |
| curl | Pre-installed or `brew install curl` | `sudo apt install curl` |

## ⚡ How It Works

### `/youtube-transcribe`
1. 📥 **Download** — Fetches audio via yt-dlp
2. ✂️ **Segment** — Splits audio into chunks if > 50 min, compresses all chunks to 32k mono
3. 🎙️ **Transcribe** — Calls OpenAI-compatible Whisper ASR API in parallel (max 4 concurrent)
4. 📝 **Output** — Presents the full transcript in the conversation

### `/youtube-report`
1. 📖 **Read** — Gets transcript text from the conversation context
2. 🤖 **Summarize** — AI generates Highlights + detailed written transcript
3. 📄 **Output** — Renders the formatted report in the conversation

## 🔗 Related Projects

- [bilibili-summary](https://github.com/jianhu-chen/bilibili-summary) — Transcribe Bilibili videos into Markdown reports

## 📄 License

MIT
