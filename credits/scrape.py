#!/usr/bin/env python3
"""
download_ports.py

Parses a GitHub README with lines like:
  * [Game Name](https://github.com/user/repo) - port by [porter]
  * [Game Name](https://github.com/user/repo/tree/branch/subdir) - port by [porter]
  - [Game Name](link1), [2](link2), [3](link3) - multiple links → always uses the FIRST

Handles:
  - Both * and - bullet styles
  - Malformed [Title][url] (square brackets instead of parens)
  - Trailing ? or other junk on URLs
  - Lines with no URL at all (skipped gracefully)
  - Multiple links on one line (first GitHub URL wins)

Downloads each link into its own folder under an output directory.
- Full repo  → downloads default branch ZIP and extracts it
- Subfolder  → downloads only that folder's contents via the GitHub API
"""

import argparse
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "port-downloader/1.0"}


_token_override: str = ""


def gh_token() -> dict:
    """Return auth header, preferring --token arg over GITHUB_TOKEN env var."""
    token = _token_override or os.environ.get("GITHUB_TOKEN", "")
    if token:
        return {**HEADERS, "Authorization": f"Bearer {token}"}
    return HEADERS


def fetch_json(url: str) -> object:
    req = urllib.request.Request(url, headers=gh_token())
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers=gh_token())
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def safe_dirname(name: str) -> str:
    """Turn a game name or repo name into a safe folder name."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name or "unnamed"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Matches standard markdown links: [text](url)
_PAREN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\)\s]+)\)")
# Matches malformed links with square bracket url: [text][url]
_BRACKET_LINK = re.compile(r"\[([^\]]+)\]\[(https?://[^\]\s]+)\]")
# Any raw https://github.com URL (fallback)
_RAW_GH = re.compile(r"(https?://github\.com/[^\s\),\]]+)")
# Bullet line detector (- or * with optional leading whitespace)
_BULLET = re.compile(r"^\s*[-*]")
# Clean trailing junk from URLs: ?, ), ], comma, etc.
_URL_TRAILING = re.compile(r"[?)\],]+$")


def _first_github_url(line: str) -> str | None:
    """
    Extract the FIRST GitHub URL from a line by position, handling:
    - Standard [text](url)
    - Malformed [text][url]
    - Raw https://github.com/... URL
    Always returns the URL that appears earliest in the line.
    """
    candidates = []  # (start_pos, url)

    for m in _PAREN_LINK.finditer(line):
        url = _URL_TRAILING.sub("", m.group(2).strip())
        if "github.com" in url:
            candidates.append((m.start(), url))

    for m in _BRACKET_LINK.finditer(line):
        url = _URL_TRAILING.sub("", m.group(2).strip())
        if "github.com" in url:
            candidates.append((m.start(), url))

    for m in _RAW_GH.finditer(line):
        url = _URL_TRAILING.sub("", m.group(1).strip())
        candidates.append((m.start(), url))

    if not candidates:
        return None

    # Pick the match that starts earliest in the line
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _entry_name(line: str) -> str:
    """Extract the game/port name — first bracketed text on the line."""
    m = re.search(r"\[([^\]]+)\]", line)
    if m:
        return m.group(1)
    # Fallback: text between bullet and first - or ,
    stripped = re.sub(r"^\s*[-*]\s*", "", line)
    name = re.split(r"\s[-–]|\s*,", stripped)[0].strip()
    return name or "unnamed"


def _extract_porters(line: str) -> list[str]:
    """
    Extract porter name(s) from a line after the first "by" keyword.
    Handles linked [name](url) porters and plain-text names.
    Examples:
      - port by [bread](https://github.com/genizy)        -> ["bread"]
      - Ports by [crackers](...) and [slant](...)          -> ["crackers", "slant"]
      - port by bog                                        -> ["bog"]
    """
    by_match = re.search(r"\bby\b(.+)$", line, re.IGNORECASE)
    if not by_match:
        return []

    by_section = by_match.group(1)

    # Collect linked porter names [name](url), skip bare number labels like [2](...)
    linked = re.findall(r"\[([^\]]+)\]\(https?://[^\)\s]+\)", by_section)
    porters = [re.sub(r"[?!.,]+$", "", n) for n in linked if not re.fullmatch(r"\d+", n)]
    if porters:
        return porters

    # No linked names — parse plain text (comma/and separated)
    plain = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", by_section)
    plain = re.sub(r"https?://\S+", "", plain)
    plain = re.sub(r"[,()\[\]]", " ", plain)
    names = [p.strip() for p in re.split(r"\band\b|,", plain) if p.strip()]
    return names


def parse_readme(text: str) -> list[dict]:
    """
    Return list of {name, url, porters} dicts for every bullet line that has a GitHub URL.
    - Always picks the FIRST GitHub URL on the line.
    - Skips lines with no GitHub URL.
    - Handles -, * bullets and both (url) and [url] link formats.
    """
    entries = []
    for line in text.splitlines():
        if not _BULLET.match(line):
            continue  # not a bullet line
        url = _first_github_url(line)
        if not url:
            continue  # no link found — skip (e.g. "Beatblock - port by bog")
        name = _entry_name(line)
        porters = _extract_porters(line)
        entries.append({"name": name, "url": url, "porters": porters})
    return entries


# ---------------------------------------------------------------------------
# GitHub URL analysis
# ---------------------------------------------------------------------------

GH_RE = re.compile(
    r"https?://github\.com/"
    r"(?P<owner>[^/]+)/"
    r"(?P<repo>[^/]+)"
    r"(?:/tree/(?P<ref>[^/]+)(?P<path>/.*))?"
)


def parse_github_url(url: str) -> dict | None:
    """
    Returns dict with keys: owner, repo, ref (branch/tag), path (subdir or '')
    Returns None if not a GitHub repo URL.
    """
    m = GH_RE.match(url)
    if not m:
        return None
    return {
        "owner": m.group("owner"),
        "repo": re.sub(r"\.git$", "", m.group("repo")),
        "ref": m.group("ref") or "",
        "path": (m.group("path") or "").lstrip("/"),
    }


# ---------------------------------------------------------------------------
# Download strategies
# ---------------------------------------------------------------------------

def get_default_branch(owner: str, repo: str) -> str:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    data = fetch_json(url)
    return data.get("default_branch", "main")


def download_full_repo(owner: str, repo: str, ref: str, dest: Path) -> None:
    """Download a branch ZIP and extract into dest/."""
    if not ref:
        ref = get_default_branch(owner, repo)
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{ref}.zip"
    print(f"    ↓ Downloading repo ZIP: {zip_url}")
    try:
        data = fetch_bytes(zip_url)
    except urllib.error.HTTPError:
        # Maybe it's a tag, not a branch
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/tags/{ref}.zip"
        print(f"    ↓ Retrying as tag ZIP: {zip_url}")
        data = fetch_bytes(zip_url)

    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BytesIO(data)) as zf:
        # GitHub ZIPs have a top-level folder like repo-branch/; strip it
        top = zf.namelist()[0].split("/")[0]
        for member in zf.infolist():
            rel = member.filename[len(top) + 1 :]  # strip top-level folder
            if not rel:
                continue
            target = dest / rel
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(member.filename))
    print(f"    ✓ Extracted to {dest}/")


def download_subfolder(owner: str, repo: str, ref: str, path: str, dest: Path) -> None:
    """Recursively download a subfolder via the GitHub Trees API."""
    if not ref:
        ref = get_default_branch(owner, repo)
    tree_url = (
        f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{ref}"
        f"?recursive=1"
    )
    print(f"    ↓ Fetching tree: {tree_url}")
    tree_data = fetch_json(tree_url)

    if tree_data.get("truncated"):
        print("    ⚠ Tree truncated by GitHub API — some files may be missing.")

    prefix = path.rstrip("/") + "/"
    blobs = [
        item for item in tree_data.get("tree", [])
        if item["type"] == "blob" and item["path"].startswith(prefix)
    ]

    if not blobs:
        print(f"    ⚠ No files found under '{path}' — trying full repo download instead.")
        download_full_repo(owner, repo, ref, dest)
        return

    dest.mkdir(parents=True, exist_ok=True)
    for item in blobs:
        rel = item["path"][len(prefix):]
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        raw_url = (
            "https://raw.githubusercontent.com/{}/{}/{}/{}".format(
                owner, repo, ref,
                urllib.parse.quote(item["path"], safe="/")
            )
        )
        target.write_bytes(fetch_bytes(raw_url))
        print(f"      • {rel}")
    print(f"    ✓ {len(blobs)} file(s) written to {dest}/")


# ---------------------------------------------------------------------------
# Main download logic
# ---------------------------------------------------------------------------

def write_credits(dest: Path, game_name: str, porters: list[str], source_url: str) -> None:
    """Write a credits.txt file into the downloaded folder."""
    lines = [
        f"Game: {game_name}",
        f"Source: {source_url}",
        "",
    ]
    if porters:
        if len(porters) == 1:
            lines.append(f"Ported by: {porters[0]}")
        else:
            lines.append("Ported by:")
            for p in porters:
                lines.append(f"  - {p}")
    else:
        lines.append("Porter: unknown")

    (dest / "credits.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"    ✎ credits.txt written ({', '.join(porters) if porters else 'no porter info'})")


def write_credits_only(entry: dict, output_dir: Path) -> None:
    """Write credits.txt into an already-downloaded folder, skipping the download."""
    name = entry["name"]
    url = entry["url"]
    porters = entry.get("porters", [])

    gh = parse_github_url(url)
    if gh and gh["path"]:
        folder_name = gh["path"].rstrip("/").split("/")[-1]
    elif gh:
        folder_name = gh["repo"]
    else:
        folder_name = safe_dirname(name)

    dest = output_dir / folder_name

    print(f"\n[{name}]")
    if not dest.exists():
        print(f"  ⚠ Folder not found, creating it: {dest}/")
        dest.mkdir(parents=True, exist_ok=True)
    write_credits(dest, name, porters, url)


def download_entry(entry: dict, output_dir: Path, delay: float) -> None:
    name = entry["name"]
    url = entry["url"]
    porters = entry.get("porters", [])

    # Use the repo name or subfolder name from the URL as the folder name
    gh = parse_github_url(url)
    if gh and gh["path"]:
        # subfolder URL — use the last path segment, e.g. "amanda-the-adventurer"
        folder_name = gh["path"].rstrip("/").split("/")[-1]
    elif gh:
        # full repo URL — use the repo name, e.g. "antonblast"
        folder_name = gh["repo"]
    else:
        # fallback to README name if URL can't be parsed
        folder_name = safe_dirname(name)

    dest = output_dir / folder_name

    print(f"\n[{name}]")
    print(f"  URL  : {url}")
    print(f"  Dest : {dest}/")
    if porters:
        print(f"  By   : {', '.join(porters)}")

    if dest.exists():
        print("  ⏭  Already exists — skipping.")
        return

    if not gh:
        print("  ✗ Not a GitHub URL — skipping.")
        return

    owner, repo, ref, subpath = gh["owner"], gh["repo"], gh["ref"], gh["path"]

    try:
        if subpath:
            download_subfolder(owner, repo, ref, subpath, dest)
        else:
            download_full_repo(owner, repo, ref, dest)
        write_credits(dest, name, porters, url)
    except urllib.error.HTTPError as e:
        print(f"  ✗ HTTP {e.code}: {e.reason} — {url}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    if delay > 0:
        time.sleep(delay)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def fetch_readme_url(url: str) -> str:
    """
    Fetch README text from a GitHub URL. Accepts:
      - https://github.com/user/repo                       -> fetches default branch README.md
      - https://github.com/user/repo/blob/branch/path.md  -> converts to raw URL
      - https://raw.githubusercontent.com/...              -> fetched directly
    """
    # Already a raw URL
    if "raw.githubusercontent.com" in url:
        print(f"  Fetching: {url}")
        return fetch_bytes(url).decode("utf-8")

    # github.com/user/repo/blob/branch/file -> raw
    blob_match = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)", url
    )
    if blob_match:
        owner, repo, branch, filepath = blob_match.groups()
        raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"
        print(f"  Fetching: {raw}")
        return fetch_bytes(raw).decode("utf-8")

    # github.com/user/repo (bare repo URL) -> fetch default branch README.md via API
    repo_match = re.match(r"https://github\.com/([^/]+)/([^/?\s]+)", url)
    if repo_match:
        owner, repo = repo_match.group(1), re.sub(r"\.git$", "", repo_match.group(2))
        branch = get_default_branch(owner, repo)
        raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/README.md"
        print(f"  Fetching: {raw}")
        return fetch_bytes(raw).decode("utf-8")

    raise ValueError(f"Unrecognised GitHub URL format: {url}")

def main():
    parser = argparse.ArgumentParser(
        description="Parse a README and download GitHub repos/folders from bullet-list links."
    )
    parser.add_argument(
        "readme",
        help=(
            "Path to a local README file, a GitHub URL, or '-' to read from stdin.\n"
            "Accepted URL formats:\n"
            "  https://github.com/user/repo                     (uses default branch README.md)\n"
            "  https://github.com/user/repo/blob/main/README.md\n"
            "  https://raw.githubusercontent.com/user/repo/main/README.md"
        ),
    )
    parser.add_argument(
        "-o", "--output",
        default="ports",
        help="Output directory (default: ./ports)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between downloads (default: 1.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and list entries without downloading anything",
    )
    parser.add_argument(
        "--credits-only",
        action="store_true",
        help="Only write credits.txt into each existing folder, skip all downloads",
    )
    parser.add_argument(
        "--token",
        default="",
        metavar="GITHUB_TOKEN",
        help="GitHub personal access token (overrides GITHUB_TOKEN env var)",
    )
    args = parser.parse_args()

    # Apply token override
    global _token_override
    if args.token:
        _token_override = args.token
        print("  Using provided GitHub token.")
    elif os.environ.get("GITHUB_TOKEN"):
        print("  Using GITHUB_TOKEN from environment.")

    # Read README — local file, URL, or stdin
    readme_arg = args.readme.strip()
    if readme_arg == "-":
        text = sys.stdin.read()
    elif readme_arg.startswith("http://") or readme_arg.startswith("https://"):
        text = fetch_readme_url(readme_arg)
    else:
        text = Path(readme_arg).read_text(encoding="utf-8")

    entries = parse_readme(text)
    if not entries:
        print("No markdown links found in the README.")
        sys.exit(1)

    print(f"Found {len(entries)} link(s) in README.")

    output_dir = Path(args.output)

    if args.dry_run:
        print("\nDry run — would download:\n")
        for e in entries:
            gh = parse_github_url(e["url"])
            kind = "subfolder" if (gh and gh["path"]) else "full repo"
            print(f"  [{e['name']}]  ({kind})")
            print(f"    {e['url']}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir.resolve()}\n")

    for entry in entries:
        if args.credits_only:
            write_credits_only(entry, output_dir)
        else:
            download_entry(entry, output_dir, args.delay)

    print("\nDone.")


if __name__ == "__main__":
    main()