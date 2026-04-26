---
name: youtube-summary
description: "Transcribe YouTube videos into Markdown reports. Downloads audio, runs ASR via OpenAI-compatible Whisper API, generates highlights and detailed transcript."
argument-hint: "<youtube-url> [language preference]"
allowed-tools: Bash(python3 *) Bash(yt-dlp *) Bash(ffmpeg *) Bash(brew *) Bash(pip3 *) Bash(curl *) Bash(mktemp *)
---

# YouTube Video Transcription Report Generator

Convert YouTube videos into Markdown text reports.

## Input

YouTube URL: `$1` (first space-separated token from user input). The full `$ARGUMENTS` may contain additional text beyond the URL — treat it as user instructions (e.g., language preference).

## Workflow

To avoid long-running timeouts, the process is split into multiple steps. Each step is independent.

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

### 5. Generate Markdown report

Read `$WORKDIR/metadata.json` for full metadata (description, tags, etc. help understand the video content), then combine with the transcript to write the report and save it in the current working directory.

**Filename**: Based on the video content, use the LLM to generate a concise title (max 30 characters, summarizing the core theme of the video) as the filename `{summarized-title}.md` (strip illegal characters `\/:*?"<>|`). Do NOT use the YouTube original title directly.

**Report structure**:

```markdown
# {YouTube original title}

> **Channel**: {channel} | **Date**: {upload_date} | **Duration**: {duration}
> **Link**: {url}

## Highlights

- {key point 1}
- {key point 2}
- ... (extract the most critical points, no more than 10, keep it concise)

## Video Details

{Organize as a polished written version following the original video's narrative order}

### {Topic 1}

{Detailed content...}

### {Topic 2}

{Detailed content...}
```

### 6. Writing guidelines

**Highlights section**:
- Extract the most critical points from the video, concise and refined
- One sentence per point, highlight key information
- Preserve data, conclusions, and core arguments

**Video Details section**:
- Preserve the original video's narrative structure and information density as much as possible
- Only apply the following treatments:
  - Remove subjective expressions, filler words, and pauses (e.g. "嗯", "那个", "就是说", "sort of", "you know", etc.)
  - Remove redundant phrasing
  - Convert spoken language into polished written form
- **Do NOT heavily compress the content** — preserve the full reasoning logic and information volume
- Split naturally by topic transitions in the video, using `###` subheadings
- Preserve data, quotes, arguments, and case studies from the video

**Ad handling**:
- Skip ads at the beginning or end of the video, sponsor reads, and promotional content (e.g. "thanks to our sponsor", "click the link to get", "use my promo code", etc.)
- If ad segments are inserted in the middle of the video, skip them as well
- Do not mention any ad content in the report

**General rules**:
- **Language**: By default, write reports in the **same language as the video**. Preserve technical terms in their original language. If the full user input (`$ARGUMENTS`) contains text beyond the URL (e.g., "Please write the report in English" or "请用繁体中文撰写报告"), follow that language preference instead.
- If the video is short (< 5 minutes), the structure can be simplified

### 7. Clean up temporary files

After the report is written, clean up the working directory:

```bash
python3 "./scripts/transcribe.py" cleanup "$WORKDIR"
```

Tell the user where the report was saved.
