"""
parse_games.py
--------------
Parses a game list .txt file (one entry per line in the format:
  https://cdn.../folder-name-hexid/index.html | Game Name HexId
) and updates an existing games JSON file, preserving thumbnails and descriptions.

Usage:
  python parse_games.py <input.txt> <output.json>

Example:
  python parse_games.py ruffle.txt _data/ruffleGames.json
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


def clean_name(raw: str) -> str:
    """Strip the trailing hex ID suffix from a display name.
    e.g. '1 Screen Hero 17692Cbcc' -> '1 Screen Hero'
    """
    return re.sub(r'\s+[0-9A-Fa-f]{6,}$', '', raw).strip()


def extract_path(url: str) -> tuple[str, str, str] | None:
    """Extract slug, path, and cdn from URL.
    e.g. 'https://...wl-ruffle.../abc-123/index.html' -> ('abc-123', 'abc-123/index.html', 'ruffle')
         'https://...wl-main.../bloonstd/index.html' -> ('bloonstd', 'bloonstd/index.html', 'html')
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    
    # Detect CDN from URL
    if 'wl-main' in url:
        cdn = 'html'
    elif 'wl-ruffle' in url:
        cdn = 'ruffle'
    elif 'wl-ports' in url:
        cdn = 'webPorts'
    else:
        cdn = 'ruffle'  # default
    
    # Find index.html and work backwards
    if 'index.html' in path_parts:
        idx = path_parts.index('index.html')
        if idx > 0:
            slug = path_parts[idx - 1]
            path = f"{slug}/index.html"
            return slug, path, cdn
    
    return None


def load_existing(output_path: str) -> dict[str, dict]:
    """Load existing JSON and return a dict keyed by slug for quick lookup."""
    if not Path(output_path).exists():
        return {}
    
    with open(output_path, encoding="utf-8") as f:
        games = json.load(f)
    
    return {g['slug']: g for g in games}


def parse(input_path: str, existing: dict[str, dict]) -> list[dict]:
    games = []
    added = 0
    updated = 0

    with open(input_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            parts = line.split(" | ")
            if len(parts) < 2:
                print(f"  [!] Line {lineno} skipped (unexpected format): {line[:80]}")
                continue

            # Handle both "URL | Name" and "URL | Name | Source" formats
            url = parts[0].strip()
            raw_name = parts[1].strip()
            # parts[2] would be source (e.g. "3kh0") - ignored for now

            # Extract path from URL
            result = extract_path(url)
            if not result:
                print(f"  [!] Line {lineno} skipped (can't parse URL): {url[:80]}")
                continue

            slug, path, cdn = result
            name = clean_name(raw_name)

            # Check if game already exists
            if slug in existing:
                # Preserve existing thumbnail and description
                game = existing[slug].copy()
                game['name'] = name
                game['path'] = path
                game['cdn'] = cdn  # Update CDN in case it changed
                updated += 1
            else:
                # New game
                game = {
                    "name": name,
                    "slug": slug,
                    "path": path,
                    "cdn": cdn,
                    "thumbnail": f"{slug}/thumbnail.jpg",
                    "description": ""
                }
                added += 1
            
            games.append(game)

    print(f"  {added} new games added, {updated} existing games preserved")
    return games


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    input_path  = sys.argv[1]
    output_path = sys.argv[2]

    if not Path(input_path).exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    print(f"Loading existing {output_path} ...")
    existing = load_existing(output_path)
    print(f"  {len(existing)} existing games found")

    print(f"Parsing {input_path} ...")
    games = parse(input_path, existing)
    print(f"  {len(games)} total games")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
        f.write('\n')

    print(f"Written to {output_path}")


if __name__ == "__main__":
    main()