---
name: youtube-report
description: "Generate a polished Markdown report from any video transcript. Takes raw transcript text from any source (YouTube, Bilibili, pasted text) and optional metadata, produces a structured report with Highlights and Video Details sections. Use after running /youtube-transcribe, or whenever the user pastes a transcript and wants a formatted summary, report, or writeup. Also use when the user mentions summarizing a transcript, writing a video report, or converting spoken content into written form."
argument-hint: "[language preference]"
---

# Video Transcript Report Generator

Turn raw transcript text into a structured, polished Markdown report.

## Input

This skill works with transcript text that is already available in the conversation context. Typical usage:

1. **After `/youtube-transcribe`** — the transcript and metadata are already in the conversation
2. **User pastes a transcript** — use the pasted text directly
3. **User provides a transcript file** — read the file and use its contents

If video metadata (title, channel, date, duration, URL) is available in the conversation, use it. If not, generate the report without it — the header adapts automatically.

## Report structure

ALWAYS use this template:

```markdown
# {Video title, or "Video Transcript Report" if no title available}

> **Channel**: {channel, or omit this line} | **Date**: {upload_date, or omit} | **Duration**: {duration, or omit}
> **Link**: {url, or omit this line}

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

When no metadata is available, simplify the header:

```markdown
# Video Transcript Report

## Highlights
...

## Video Details
...
```

## Writing guidelines

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
- **Language**: By default, write reports in the **same language as the video**. Preserve technical terms in their original language. If the user specifies a language preference in `$ARGUMENTS` (e.g., "Please write the report in English" or "请用繁体中文撰写报告"), follow that preference instead.
- If the video is short (< 5 minutes), the structure can be simplified

## Output

Render the complete report directly in the conversation. Do NOT save to a local file. The user can ask to save it separately if needed.
