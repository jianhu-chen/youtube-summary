---
name: youtube-transcribe
description: "Transcribe any YouTube video to text. Downloads audio, runs ASR via OpenAI-compatible Whisper API, returns the full transcript. Use whenever you need a YouTube video transcribed — the output is raw text ready for summarization, translation, or analysis. Also use when the user mentions video transcription, converting speech to text, or getting a video's spoken content."
argument-hint: "<youtube-url>"
allowed-tools: Bash(python3 *) Bash(yt-dlp *) Bash(ffmpeg *) Bash(brew *) Bash(pip3 *) Bash(curl *) Bash(mktemp *)
---

# YouTube Video Transcription

Convert YouTube videos into raw transcript text.

## Input

YouTube URL: `$1` (first space-separated token from user input). Any additional text in `$ARGUMENTS` beyond the URL is ignored by this skill — the user's language preference or other instructions apply to downstream processing (e.g., `/youtube-report`), not to transcription.

## Workflow

The process is split into multiple steps to avoid long-running timeouts. Each step is independent.

### 1. Create a unique working directory

```bash
WORKDIR=$(mktemp -d /tmp/yt-summary-XXXXXX)
echo "Workdir: $WORKDIR"
```

Remember `$WORKDIR` — it is used in all subsequent steps.

### 2. Prepare: download audio + metadata + chunking

```bash
python3 "./scripts/transcribe.py" prepare "$1" "$WORKDIR"
```

On success, stdout outputs a compact JSON (containing `chunk_count`, `workdir`, `title`, `channel`, `upload_date`, `duration`, `url`). Full metadata is saved in `$WORKDIR/metadata.json`.

Read and remember `chunk_count`.

**Handling missing dependencies** (non-zero exit code):

| Exit code | Meaning | Fix |
|-----------|---------|-----|
| 10 | yt-dlp not installed | Run `pip3 install yt-dlp` (or `brew install yt-dlp` on macOS), then retry |
| 11 | ffmpeg not installed | Run `sudo apt install ffmpeg` on Linux or `brew install ffmpeg` on macOS, then retry |
| 12 | ASR_API_KEY not set | Tell the user to set environment variable `ASR_API_KEY` |
| 13 | curl not installed | Install curl via system package manager, then retry |

### 3. Transcribe: parallel ASR API calls

```bash
python3 "./scripts/transcribe.py" transcribe-all "$WORKDIR"
```

Transcribe all chunks in parallel (max concurrency 4). The script prints progress like `[Progress] 2/3 chunks done`. If a chunk fails, retry individually with `transcribe "$WORKDIR" <index>`.

### 4. Collect: merge all transcription text

```bash
python3 "./scripts/transcribe.py" collect "$WORKDIR"
```

stdout outputs the full merged transcription text. Save it as transcript.

### 5. Present the transcript

Output the transcript directly in the conversation. Include the video metadata above the transcript for context:

```
## {title}

> **Channel**: {channel} | **Date**: {upload_date} | **Duration**: {duration}
> **Link**: {url}

{full transcript text}
```

Read `$WORKDIR/metadata.json` if you need additional metadata (description, tags, etc.).

Do NOT write the transcript to a file — present it directly in the conversation. The user can then use `/youtube-report` to generate a formatted summary, or use the transcript for any other purpose.

### 6. Clean up temporary files

After presenting the transcript, clean up the working directory:

```bash
python3 "./scripts/transcribe.py" cleanup "$WORKDIR"
```
