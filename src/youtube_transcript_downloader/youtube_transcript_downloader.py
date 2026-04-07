"""Download YouTube video transcripts with metadata as Markdown files with YAML front matter."""

import re
from datetime import timedelta
from pathlib import Path
from typing import Any

import click
from googleapiclient.discovery import build  # pyright: ignore[reportUnknownVariableType]
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound


def extract_video_id(url_or_id: str) -> str:
    """Extract video ID from a YouTube URL or return as-is if already an ID."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/|/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url_or_id}")


def format_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration (PT1H2M3S) to HH:MM:SS or MM:SS."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return iso_duration
    h, m, s = (int(v) if v else 0 for v in match.groups())
    td = timedelta(hours=h, minutes=m, seconds=s)
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def fetch_metadata(youtube: Any, video_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetch video metadata from YouTube Data API v3."""
    metadata: dict[str, dict[str, Any]] = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        response = (
            youtube.videos()
            .list(part="snippet,contentDetails,statistics", id=",".join(batch))
            .execute()
        )
        for item in response.get("items", []):
            vid = item["id"]
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            metadata[vid] = {
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "date": snippet["publishedAt"][:10],
                "duration": format_duration(item["contentDetails"]["duration"]),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "video_id": vid,
            }
    return metadata


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str | None:
    """Fetch transcript for a video in the specified languages.

    First tries to find a direct transcript in the requested languages.
    If none exists, falls back to translating an available transcript.
    """
    if languages is None:
        languages = ["en"]
    try:
        ytt = YouTubeTranscriptApi()
        try:
            transcript = ytt.fetch(video_id, languages=languages)
        except NoTranscriptFound:
            transcript_list = ytt.list(video_id)
            source = transcript_list.find_transcript(["en"])
            transcript = source.translate(languages[0]).fetch()
        return "\n".join(entry.text for entry in transcript)
    except Exception as e:
        click.echo(f"  Could not fetch transcript for {video_id}: {e}", err=True)
        return None


def yaml_escape(value: str) -> str:
    """Escape a string for YAML front matter."""
    if any(c in value for c in ":#{}[]|>&*!?,\"'"):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def save_transcript(meta: dict[str, Any], transcript: str, output_dir: Path) -> Path:
    """Save transcript as a Markdown file with YAML front matter."""
    safe_title = re.sub(r'[<>:"/\\|?*]', "", meta["title"])
    safe_title = re.sub(r"\s+", " ", safe_title).strip()[:120]
    filename = f"{meta['date']}_{safe_title}.md"
    filepath = output_dir / filename

    frontmatter = f"""---
title: {yaml_escape(meta["title"])}
channel: {yaml_escape(meta["channel"])}
date: {meta["date"]}
duration: {meta["duration"]}
views: {meta["views"]}
likes: {meta["likes"]}
comments: {meta["comments"]}
video_id: {meta["video_id"]}
url: https://www.youtube.com/watch?v={meta["video_id"]}
---"""

    filepath.write_text(f"{frontmatter}\n\n{transcript}\n", encoding="utf-8")
    return filepath


@click.command()
@click.argument("videos", nargs=-1, required=True)
@click.option(
    "--api-key",
    envvar="YOUTUBE_API_KEY",
    required=True,
    help="YouTube Data API v3 key (or set YOUTUBE_API_KEY env var).",
)
@click.option(
    "--output-dir",
    "-o",
    default="transcripts",
    type=click.Path(),
    help="Output directory (default: transcripts).",
)
@click.option(
    "--language",
    "-l",
    default="en",
    help="Comma-separated language codes in priority order (default: en).",
)
def main(videos: tuple[str, ...], api_key: str, output_dir: str, language: str) -> None:
    """Download YouTube video transcripts with metadata."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    video_ids: list[str] = []
    for v in videos:
        try:
            video_ids.append(extract_video_id(v))
        except ValueError as e:
            click.echo(f"Skipping invalid input: {e}", err=True)

    if not video_ids:
        click.echo("No valid video IDs provided.", err=True)
        raise SystemExit(1)

    languages = [lang.strip() for lang in language.split(",")]

    click.echo(f"Processing {len(video_ids)} video(s)...")

    youtube: Any = build("youtube", "v3", developerKey=api_key)  # pyright: ignore[reportUnknownVariableType]
    metadata = fetch_metadata(youtube, video_ids)

    success = 0
    for vid in video_ids:
        if vid not in metadata:
            click.echo(f"  [{vid}] metadata not found, skipping", err=True)
            continue

        meta = metadata[vid]
        click.echo(f"  [{meta['title'][:60]}] ", nl=False)

        transcript = fetch_transcript(vid, languages=languages)
        if transcript is None:
            click.echo("- no transcript available")
            continue

        filepath = save_transcript(meta, transcript, out)
        click.echo(f"-> {filepath}")
        success += 1

    click.echo(f"\nDone: {success}/{len(video_ids)} transcripts saved to {out}/")


if __name__ == "__main__":
    main()
