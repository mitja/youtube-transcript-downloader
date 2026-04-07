# Plan: Implement YouTube Transcript Downloader with Click

## Context

Port the reference script (`../youtube_transcripts.py`) into the existing package structure, replacing argparse with click, and add comprehensive tests. The tool downloads YouTube video transcripts with metadata and saves them as Markdown files with YAML front matter.

## Step 1: Add dependencies to `pyproject.toml`

**File:** `pyproject.toml` (line 41-42)

Add to `dependencies`:
```
"click>=8.1.0",
"youtube-transcript-api>=1.0.0",
"google-api-python-client>=2.0.0",
```

Run `uv sync --all-extras` to install.

## Step 2: Implement main module

**File:** `src/youtube_transcript_downloader/youtube_transcript_downloader.py`

Port all functions from the reference script:
- `extract_video_id(url_or_id)` — regex extraction of video IDs from URLs
- `format_duration(iso_duration)` — ISO 8601 to HH:MM:SS
- `fetch_metadata(youtube, video_ids)` — YouTube Data API v3 metadata (batches of 50)
- `fetch_transcript(video_id)` — english transcript via youtube-transcript-api
- `yaml_escape(value)` — escape strings for YAML front matter
- `save_transcript(meta, transcript, output_dir)` — save as markdown with YAML front matter
- `main()` — **click CLI** replacing argparse

Click CLI design:
```python
@click.command()
@click.argument("videos", nargs=-1, required=True)
@click.option("--api-key", envvar="YOUTUBE_API_KEY", required=True, help="YouTube Data API v3 key.")
@click.option("--output-dir", "-o", default="transcripts", type=click.Path(), help="Output directory.")
def main(videos, api_key, output_dir): ...
```

- Use `click.echo()` / `click.echo(..., err=True)` instead of `print()`
- click's `envvar` on `--api-key` replaces the manual `os.environ.get()` fallback

## Step 3: Update `__init__.py` exports

**File:** `src/youtube_transcript_downloader/__init__.py`

Update `__all__` to list all public symbols: `extract_video_id`, `format_duration`, `fetch_metadata`, `fetch_transcript`, `yaml_escape`, `save_transcript`, `main`.

## Step 4: Write tests

**File:** `tests/test_youtube_transcript_downloader.py` (new)

### Unit tests (no mocking)
- **`test_extract_video_id`** — standard URL, short URL, embed URL, bare ID, URL with params, invalid input raises `ValueError`
- **`test_format_duration`** — hours+min+sec, min+sec only, seconds only, hours only, invalid passthrough
- **`test_yaml_escape`** — plain string unchanged, strings with `:`, `"`, `&` get quoted/escaped
- **`test_save_transcript`** — uses `tmp_path`, verifies file creation, filename pattern, YAML front matter content, title sanitization

### Mocked tests
- **`test_fetch_metadata`** — mock `youtube.videos().list().execute()` chain, verify returned dict structure and value transforms
- **`test_fetch_transcript`** — patch `YouTubeTranscriptApi`, verify joined text output; error case returns `None`
- **`test_main_cli`** — `click.testing.CliRunner`, patch `build` and `YouTubeTranscriptApi`, verify exit code 0 and file output

### End-to-end test
- **`test_e2e_download`** — `@pytest.mark.skipif(not os.environ.get("YOUTUBE_API_KEY"), reason="...")`, uses video ID `xdxgLTzfCWI`, invokes CLI via CliRunner with real API key, asserts file created with correct front matter

## Step 5: Delete placeholder test

**File:** `tests/test_placeholder.py` — remove

## Step 6: Verify

- Run `make` (install + lint + test)
- Fix any ruff/basedpyright issues
- Run e2e test locally with `YOUTUBE_API_KEY=... uv run pytest tests/ -k test_e2e`

## Notes
- Keep English-only (no `--language` option for now)
- Single module file — not splitting into multiple files
- `googleapiclient` has poor type stubs; may need `# type: ignore` on `build()` call
