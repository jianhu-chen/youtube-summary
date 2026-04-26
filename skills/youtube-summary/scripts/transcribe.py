#!/usr/bin/env python3
"""
YouTube audio downloader + OpenAI-compatible Whisper ASR transcription.

Multi-step workflow to avoid Bash tool timeout:
  Step 1 - prepare: Check deps, download audio, split, compress, validate sizes
  Step 2 - transcribe-all: Transcribe all chunks in parallel
  Step 3 - collect: Merge all chunk transcripts
  Step 4 - cleanup: Remove workdir

Usage:
  transcribe.py prepare <youtube_url> <workdir>
  transcribe.py transcribe-all <workdir>
  transcribe.py transcribe <workdir> <chunk_index>   (single chunk fallback)
  transcribe.py collect <workdir>
  transcribe.py cleanup <workdir>
  transcribe.py --version

Exit codes:
  0  = success
  1  = operation failure
  2  = argument error
  10 = yt-dlp not found
  11 = ffmpeg not found
  12 = ASR_API_KEY not set
  13 = curl not found
"""

import concurrent.futures
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

__version__ = "1.0.1"

# --- Configuration ---

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_ASR_PATH = "/audio/transcriptions"
DEFAULT_MODEL = "whisper-1"
MAX_SEGMENT_DURATION = 3000  # 50 minutes in seconds
MAX_CHUNK_SIZE = 45 * 1024 * 1024  # 45 MB safety margin
AUDIO_BITRATE = "32k"
MAX_CONCURRENCY = 4
CURL_TIMEOUT = 300  # 5 minutes per API call
YOUTUBE_URL_PATTERN = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/(watch\?v=|shorts/|embed/|live/)|youtu\.be/)[\w\-]+"
)

_print_lock = threading.Lock()


def eprint(*args, **kwargs):
    with _print_lock:
        print(*args, file=sys.stderr, **kwargs)


def mask_key(key):
    if len(key) <= 8:
        return "***"
    return key[:3] + "***" + key[-3:]


def is_youtube_url(url):
    return bool(YOUTUBE_URL_PATTERN.match(url.strip()))


def check_dependencies():
    eprint("[Check] Verifying dependencies...")
    if not shutil.which("yt-dlp"):
        eprint("[Error] yt-dlp not installed. Run: pip3 install yt-dlp (or brew install yt-dlp on macOS)")
        sys.exit(10)
    eprint("[Check] yt-dlp OK")
    if not shutil.which("ffmpeg"):
        eprint("[Error] ffmpeg not installed. Run: sudo apt install ffmpeg (or brew install ffmpeg on macOS)")
        sys.exit(11)
    eprint("[Check] ffmpeg OK")
    if not shutil.which("ffprobe"):
        eprint("[Error] ffprobe not installed (usually bundled with ffmpeg). Run: sudo apt install ffmpeg (or brew install ffmpeg on macOS)")
        sys.exit(11)
    eprint("[Check] ffprobe OK")
    if not shutil.which("curl"):
        eprint("[Error] curl not installed. Install via system package manager")
        sys.exit(13)
    eprint("[Check] curl OK")


def get_asr_config():
    base_url_env = os.environ.get("ASR_BASE_URL", "").strip()
    model_env = os.environ.get("ASR_MODEL", "").strip()

    api_url = (base_url_env if base_url_env else DEFAULT_BASE_URL) + DEFAULT_ASR_PATH
    model = model_env if model_env else DEFAULT_MODEL

    return {"api_url": api_url, "model": model}


def run_cmd(cmd, **kwargs):
    eprint(f"[Run] {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        eprint(f"[Warn] Command exited with code {result.returncode}")
        if result.stderr:
            eprint(f"[Warn] stderr: {result.stderr[:500]}")
    else:
        if result.stderr:
            for line in result.stderr.strip().split("\n")[:3]:
                eprint(f"  {line}")
    return result


def format_metadata(meta):
    duration_sec = meta.get("duration", 0)
    minutes = int(duration_sec) // 60
    seconds = int(duration_sec) % 60

    upload_date = meta.get("upload_date", "")
    if upload_date and len(upload_date) == 8:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"

    return {
        "title": meta.get("title", "Unknown"),
        "channel": meta.get("channel", meta.get("uploader", "Unknown")),
        "upload_date": upload_date,
        "duration": f"{minutes}m{seconds}s",
        "duration_seconds": duration_sec,
        "description": meta.get("description", ""),
        "tags": meta.get("tags", []),
        "categories": meta.get("categories", []),
        "view_count": meta.get("view_count"),
        "url": meta.get("webpage_url", meta.get("original_url", "")),
    }


def compress_chunk(filepath):
    base, ext = os.path.splitext(filepath)
    output = f"{base}_compressed{ext}"
    eprint(f"[Compress] {os.path.basename(filepath)} -> {AUDIO_BITRATE} mono...")
    result = run_cmd([
        "ffmpeg", "-y", "-i", filepath,
        "-b:a", AUDIO_BITRATE, "-ac", "1", output,
    ])
    if result.returncode != 0:
        eprint(f"[Error] Compression failed: {filepath}")
        sys.exit(1)
    os.replace(output, filepath)


# --- Step 1: prepare ---

def cmd_prepare(url, workdir):
    t_start = time.time()
    eprint(f"[Prepare] Processing URL: {url}")
    eprint(f"[Prepare] Working directory: {workdir}")

    if not is_youtube_url(url):
        eprint(f"[Error] Not a YouTube URL: {url}")
        eprint("[Error] Supported formats: https://www.youtube.com/watch?v=xxx, https://youtu.be/xxx, https://www.youtube.com/shorts/xxx, etc.")
        sys.exit(2)

    os.makedirs(workdir, exist_ok=True)
    eprint(f"[Prepare] Working directory created: {workdir}")

    check_dependencies()

    if not os.environ.get("ASR_API_KEY", "").strip():
        eprint("[Error] Environment variable ASR_API_KEY is not set")
        sys.exit(12)

    config = get_asr_config()
    base_url_env = os.environ.get("ASR_BASE_URL", "").strip()
    model_env = os.environ.get("ASR_MODEL", "").strip()
    eprint(f"[Config] API endpoint: {config['api_url']} ({'custom' if base_url_env else 'default'})")
    eprint(f"[Config] ASR model:    {config['model']} ({'custom' if model_env else 'default'})")
    eprint(f"[Config] API Key:      {mask_key(os.environ.get('ASR_API_KEY', '').strip())} (configured)")

    # Fetch metadata
    t_meta = time.time()
    eprint("[Prepare] Step 1/3: Fetching video metadata...")
    result = run_cmd(["yt-dlp", "-j", "--no-download", url])
    if result.returncode != 0:
        eprint("[Error] Failed to fetch video metadata")
        eprint(f"[Error] yt-dlp output: {result.stderr[:500]}")
        sys.exit(1)
    try:
        meta = format_metadata(json.loads(result.stdout))
    except (json.JSONDecodeError, KeyError) as e:
        eprint(f"[Error] Failed to parse video metadata: {e}")
        eprint(f"[Error] yt-dlp raw output (first 300 chars): {result.stdout[:300]}")
        sys.exit(1)

    with open(os.path.join(workdir, "metadata.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    eprint("[Prepare] Metadata saved: metadata.json")
    eprint(f"[Info] Title: {meta['title']}")
    eprint(f"[Info] Channel: {meta['channel']}")
    eprint(f"[Info] Duration: {meta['duration']}")
    eprint(f"[Info] Upload date: {meta['upload_date']}")
    eprint(f"[Info] View count: {meta.get('view_count', 'N/A')}")
    eprint(f"[Time] Fetch metadata: {time.time() - t_meta:.1f}s")

    # Download audio
    t_dl = time.time()
    eprint("[Prepare] Step 2/3: Downloading audio...")
    output_template = os.path.join(workdir, "audio")
    result = run_cmd([
        "yt-dlp", "-x",
        "--audio-format", "mp3",
        "--audio-quality", "7",
        "-o", output_template,
        "--no-playlist",
        url,
    ])
    if result.returncode != 0:
        eprint("[Error] Audio download failed")
        eprint(f"[Error] yt-dlp output: {result.stderr[:500]}")
        sys.exit(1)

    audio_file = None
    for f in os.listdir(workdir):
        if f.startswith("audio") and not f.endswith(".json"):
            audio_file = os.path.join(workdir, f)
            break
    if not audio_file:
        eprint("[Error] Downloaded audio file not found")
        eprint(f"[Debug] Working directory contents: {os.listdir(workdir)}")
        sys.exit(1)

    audio_size_mb = os.path.getsize(audio_file) / 1024 / 1024
    eprint(f"[Prepare] Audio downloaded: {os.path.basename(audio_file)} ({audio_size_mb:.1f}MB)")
    eprint(f"[Time] Download audio: {time.time() - t_dl:.1f}s")

    # Check duration -> split if needed
    t_split = time.time()
    eprint("[Prepare] Step 3/3: Preparing audio files...")
    result = run_cmd([
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "json", audio_file,
    ])
    duration = 0
    if result.returncode == 0:
        try:
            duration = float(json.loads(result.stdout)["format"]["duration"])
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            eprint(f"[Warn] Cannot parse audio duration: {e}, treating as single chunk")
    else:
        eprint("[Warn] ffprobe execution failed, treating as single chunk")
    eprint(f"[Prepare] Audio duration: {duration:.0f}s ({duration / 60:.1f} min)")

    chunks_dir = os.path.join(workdir, "chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    if duration > MAX_SEGMENT_DURATION:
        eprint(f"[Prepare] Duration exceeds {MAX_SEGMENT_DURATION // 60} min, splitting (max {MAX_SEGMENT_DURATION // 60} min per chunk)...")
        pattern = os.path.join(chunks_dir, "chunk_%03d.mp3")
        result = run_cmd([
            "ffmpeg", "-y", "-i", audio_file,
            "-f", "segment",
            "-segment_time", str(MAX_SEGMENT_DURATION),
            "-c", "copy", pattern,
        ])
        if result.returncode != 0:
            eprint("[Error] Audio splitting failed")
            sys.exit(1)
        eprint("[Prepare] Splitting complete")
    else:
        eprint("[Prepare] Duration within limit, no splitting needed")
        target = os.path.join(chunks_dir, "chunk_000.mp3")
        shutil.copy2(audio_file, target)

    # Clean up original audio file to save space
    try:
        os.remove(audio_file)
        eprint(f"[Prepare] Removed original audio: {os.path.basename(audio_file)}")
    except OSError:
        pass

    chunks = sorted(glob.glob(os.path.join(chunks_dir, "chunk_*.mp3")))
    eprint(f"[Prepare] Found {len(chunks)} chunk(s)")

    # Compress all chunks to reduce file size for ASR API upload
    eprint(f"[Prepare] Compressing {len(chunks)} chunk(s) to {AUDIO_BITRATE} mono...")
    for i, chunk in enumerate(chunks):
        size_mb = os.path.getsize(chunk) / 1024 / 1024
        eprint(f"[Prepare] Compressing chunk {i:03d}: {os.path.basename(chunk)} ({size_mb:.1f}MB)")
        compress_chunk(chunk)
        new_size_mb = os.path.getsize(chunk) / 1024 / 1024
        eprint(f"[Compress] Done: chunk {i:03d} -> {new_size_mb:.1f}MB")

    # Final validation
    for chunk in chunks:
        size = os.path.getsize(chunk)
        if size > MAX_CHUNK_SIZE:
            eprint(f"[Error] {os.path.basename(chunk)} exceeds 45MB after compression ({size / 1024 / 1024:.1f}MB)")
            sys.exit(1)

    eprint(f"[Prepare] All {len(chunks)} chunk(s) validated")
    eprint(f"[Time] Audio splitting & validation: {time.time() - t_split:.1f}s")
    eprint(f"[Time] prepare total: {time.time() - t_start:.1f}s")

    # Output essential fields to stdout, full metadata in metadata.json
    print(json.dumps({
        "chunk_count": len(chunks),
        "workdir": workdir,
        "title": meta["title"],
        "channel": meta["channel"],
        "upload_date": meta["upload_date"],
        "duration": meta["duration"],
        "url": meta["url"],
    }, ensure_ascii=False))


# --- Step 2: transcribe ---

def call_asr(chunk_file, config):
    api_key = os.environ.get("ASR_API_KEY", "").strip()
    if not api_key:
        return None, "Environment variable ASR_API_KEY is not set"

    eprint(f"[ASR] Sending request: {os.path.basename(chunk_file)} -> {config['api_url']} (model: {config['model']})")

    result = subprocess.run([
        "curl", "-s", "--max-time", str(CURL_TIMEOUT),
        "-X", "POST", config["api_url"],
        "-H", f"Authorization: Bearer {api_key}",
        "-F", f"file=@{chunk_file}",
        "-F", f"model={config['model']}",
    ], capture_output=True, text=True)

    if result.returncode != 0:
        eprint(f"[ASR] curl failed with return code: {result.returncode}")
        return None, f"curl call failed: {result.stderr}"

    eprint(f"[ASR] Response received, length: {len(result.stdout)} chars")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        eprint(f"[ASR] JSON parse failed, raw response (first 300 chars): {result.stdout[:300]}")
        return None, f"API response parse failed: {result.stdout[:300]}"

    if "text" in data:
        text = data["text"]
        eprint(f"[ASR] Transcription successful, text length: {len(text)} chars")
        return text, None
    if "error" in data:
        error_msg = data["error"]
        eprint(f"[ASR] API returned error: {error_msg}")
        return None, f"API returned error: {error_msg}"

    eprint(f"[ASR] Unexpected response (first 300 chars): {result.stdout[:300]}")
    return None, f"Unexpected API response: {result.stdout[:300]}"


def cmd_transcribe(workdir, chunk_index):
    t_start = time.time()
    eprint(f"[Transcribe] Single chunk mode: chunk {chunk_index}")

    config = get_asr_config()

    chunk_file = os.path.join(workdir, "chunks", f"chunk_{chunk_index:03d}.mp3")
    if not os.path.exists(chunk_file):
        eprint(f"[Error] Chunk file not found: {chunk_file}")
        eprint(f"[Debug] Chunks directory contents: {os.listdir(os.path.join(workdir, 'chunks'))}")
        sys.exit(1)

    chunk_size = os.path.getsize(chunk_file) / 1024 / 1024
    eprint(f"[ASR] Transcribing chunk {chunk_index}: {os.path.basename(chunk_file)} ({chunk_size:.1f}MB)")

    text, error = call_asr(chunk_file, config)
    if error:
        eprint(f"[Error] Chunk {chunk_index} transcription failed: {error}")
        sys.exit(1)

    out_file = os.path.join(workdir, "chunks", f"chunk_{chunk_index:03d}.txt")
    with open(out_file, "w") as f:
        f.write(text)
    eprint(f"[Done] Chunk {chunk_index} transcribed, {len(text)} chars -> {os.path.basename(out_file)}")
    eprint(f"[Time] transcribe single chunk: {time.time() - t_start:.1f}s")


def cmd_transcribe_all(workdir):
    t_start = time.time()
    eprint(f"[Transcribe] Parallel mode: {workdir}")

    config = get_asr_config()

    chunk_files = sorted(glob.glob(os.path.join(workdir, "chunks", "chunk_*.mp3")))
    if not chunk_files:
        eprint("[Error] No chunk files found")
        chunks_dir = os.path.join(workdir, "chunks")
        if os.path.exists(chunks_dir):
            eprint(f"[Debug] Chunks directory contents: {os.listdir(chunks_dir)}")
        else:
            eprint("[Debug] Chunks directory does not exist")
        sys.exit(1)

    chunk_count = len(chunk_files)
    workers = min(chunk_count, MAX_CONCURRENCY)
    eprint(f"[ASR] Transcribing {chunk_count} chunk(s) in parallel (max concurrency {workers})...")
    for i, f in enumerate(chunk_files):
        size_mb = os.path.getsize(f) / 1024 / 1024
        eprint(f"[ASR]   Chunk {i:03d}: {os.path.basename(f)} ({size_mb:.1f}MB)")

    completed = 0
    completed_lock = threading.Lock()
    errors = {}

    def transcribe_one(args):
        nonlocal completed
        idx, chunk_file = args
        chunk_size_mb = os.path.getsize(chunk_file) / 1024 / 1024
        eprint(f"[ASR] Starting chunk {idx}/{chunk_count}: {os.path.basename(chunk_file)} ({chunk_size_mb:.1f}MB)")
        text, error = call_asr(chunk_file, config)
        if error:
            eprint(f"[Error] Chunk {idx}/{chunk_count} failed: {error}")
            return idx, None, error
        base, _ = os.path.splitext(chunk_file)
        out_file = f"{base}.txt"
        with open(out_file, "w") as f:
            f.write(text)
        with completed_lock:
            completed += 1
            eprint(f"[Progress] {completed}/{chunk_count} chunks done ({idx} -> {len(text)} chars)")
        return idx, len(text), None

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(transcribe_one, (i, f)): i
            for i, f in enumerate(chunk_files)
        }
        for future in concurrent.futures.as_completed(futures):
            idx, char_count, error = future.result()
            if error:
                errors[idx] = error

    if errors:
        eprint(f"[Error] {len(errors)}/{chunk_count} chunk(s) failed")
        for idx in sorted(errors.keys()):
            eprint(f"[Error]   Chunk {idx}: {errors[idx]}")
        eprint("[Hint] Retry failed chunks individually with:")
        for idx in sorted(errors.keys()):
            eprint(f"[Hint]   python3 transcribe.py transcribe \"{workdir}\" {idx}")
        sys.exit(1)

    eprint(f"[Done] All {chunk_count} chunk(s) transcribed successfully")
    eprint(f"[Time] transcribe-all total: {time.time() - t_start:.1f}s")


# --- Step 3: collect ---

def cmd_collect(workdir):
    t_start = time.time()
    eprint(f"[Collect] Merging transcripts: {workdir}")
    chunks_dir = os.path.join(workdir, "chunks")
    txt_files = sorted(glob.glob(os.path.join(chunks_dir, "chunk_*.txt")))

    if not txt_files:
        eprint("[Error] No transcript files found")
        if os.path.exists(chunks_dir):
            eprint(f"[Debug] Chunks directory contents: {os.listdir(chunks_dir)}")
        sys.exit(1)

    eprint(f"[Collect] Found {len(txt_files)} transcript file(s):")
    total_chars = 0
    transcripts = []
    for f in txt_files:
        with open(f) as fh:
            text = fh.read().strip()
            transcripts.append(text)
            chars = len(text)
            total_chars += chars
            eprint(f"[Collect]   {os.path.basename(f)}: {chars} chars")

    full_text = "\n".join(transcripts)
    print(full_text)
    eprint(f"[Done] Merged {len(txt_files)} transcript(s), {total_chars} chars total")
    eprint(f"[Time] collect total: {time.time() - t_start:.1f}s")


# --- Step 4: cleanup ---

def cmd_cleanup(workdir):
    t_start = time.time()
    if not workdir.startswith("/tmp/yt-summary-"):
        eprint(f"[Error] Refusing to delete unsafe path: {workdir} (only /tmp/yt-summary-* allowed)")
        sys.exit(2)

    if os.path.exists(workdir):
        eprint(f"[Cleanup] Removing working directory: {workdir}")
        # List contents before cleanup for debugging
        for root, dirs, files in os.walk(workdir):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fp)
                    eprint(f"[Cleanup]   {os.path.relpath(fp, workdir)} ({size / 1024:.1f}KB)")
                except OSError:
                    pass
        shutil.rmtree(workdir)
        eprint(f"[Cleanup] Working directory removed: {workdir}")
        eprint(f"[Time] cleanup total: {time.time() - t_start:.1f}s")
    else:
        eprint(f"[Cleanup] Working directory does not exist, nothing to clean: {workdir}")


# --- Main ---

def main():
    if len(sys.argv) < 2:
        eprint("Usage:")
        eprint(f"  {sys.argv[0]} prepare <youtube_url> <workdir>")
        eprint(f"  {sys.argv[0]} transcribe-all <workdir>")
        eprint(f"  {sys.argv[0]} transcribe <workdir> <chunk_index>")
        eprint(f"  {sys.argv[0]} collect <workdir>")
        eprint(f"  {sys.argv[0]} cleanup <workdir>")
        eprint(f"  {sys.argv[0]} --version")
        sys.exit(2)

    command = sys.argv[1]

    if command == "--version":
        print(f"youtube-summary skill v{__version__}")
        sys.exit(0)

    if command == "prepare":
        if len(sys.argv) < 4:
            eprint(f"Usage: {sys.argv[0]} prepare <youtube_url> <workdir>")
            sys.exit(2)
        cmd_prepare(sys.argv[2], sys.argv[3])

    elif command == "transcribe-all":
        if len(sys.argv) < 3:
            eprint(f"Usage: {sys.argv[0]} transcribe-all <workdir>")
            sys.exit(2)
        cmd_transcribe_all(sys.argv[2])

    elif command == "transcribe":
        if len(sys.argv) < 4:
            eprint(f"Usage: {sys.argv[0]} transcribe <workdir> <chunk_index>")
            sys.exit(2)
        cmd_transcribe(sys.argv[2], int(sys.argv[3]))

    elif command == "collect":
        if len(sys.argv) < 3:
            eprint(f"Usage: {sys.argv[0]} collect <workdir>")
            sys.exit(2)
        cmd_collect(sys.argv[2])

    elif command == "cleanup":
        if len(sys.argv) < 3:
            eprint(f"Usage: {sys.argv[0]} cleanup <workdir>")
            sys.exit(2)
        cmd_cleanup(sys.argv[2])

    else:
        eprint(f"[Error] Unknown command: {command}")
        sys.exit(2)


if __name__ == "__main__":
    main()
