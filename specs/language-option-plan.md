# Plan: Add `--language` option to CLI

## Context

Transcripts are currently hardcoded to English (`languages=["en"]` in `fetch_transcript()`). Users need to download transcripts in other languages. The underlying `youtube-transcript-api` library already supports a `languages` parameter that accepts a list of language codes in priority order.

## Changes

### 1. Add `--language` CLI option

**File:** `src/youtube_transcript_downloader/youtube_transcript_downloader.py` (lines 109-124)

Add a `--language` / `-l` option with default `"en"`. It accepts a comma-separated string of language codes (e.g. `"de,en"` to prefer German, fall back to English).

```python
@click.option(
    "--language",
    "-l",
    default="en",
    help="Comma-separated language codes in priority order (default: en).",
)
```

Update `main()` signature to accept `language: str`, split it into a list, and pass it through to `fetch_transcript()`.

### 2. Parameterize `fetch_transcript()`

**File:** `src/youtube_transcript_downloader/youtube_transcript_downloader.py` (lines 68-76)

Change signature from `fetch_transcript(video_id: str)` to `fetch_transcript(video_id: str, languages: list[str])` and pass `languages` to `ytt.fetch()` instead of the hardcoded `["en"]`.

### 3. Update `main()` to thread the language through

**File:** `src/youtube_transcript_downloader/youtube_transcript_downloader.py` (line ~134)

Parse `language` string → list via `language.split(",")` and pass to `fetch_transcript()`.

### 4. Update tests

**File:** `tests/test_youtube_transcript_downloader.py`

- **`test_fetch_transcript()`** (line 156): Update to pass a `languages` parameter and verify it reaches `ytt.fetch()`.
- **`test_fetch_transcript_error()`** (line 170): Same — pass `languages`.
- **`test_main_cli()`** (line 183): Add a test variant that passes `--language` and verifies it propagates.
- **Add new test**: Verify comma-separated language parsing (e.g. `"de,en"` → `["de", "en"]`).

### 5. Update `__init__.py` exports if needed

**File:** `src/youtube_transcript_downloader/__init__.py` — no change expected since `fetch_transcript` is already exported; just verify the new signature doesn't break the export.

## Verification

1. `make` — must pass lint + tests cleanly
2. Manual: `uv run youtube_transcript_downloader --help` shows `--language` option
3. Manual (if API key available): `uv run youtube_transcript_downloader -l de <video_url>` fetches German transcript
