#!/usr/bin/env python3
"""
Download flash game thumbnails from Flashpoint database
"""

import json
import requests
import time
from pathlib import Path
from urllib.parse import quote

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "_data"
GAMES_DIR = SCRIPT_DIR.parent / "assets" / "games"

# API endpoints
SEARCH_API = "https://db-api.unstable.life/search"
IMAGE_BASE = "https://infinity.unstable.life/images/Logos"

def get_image_url(game_id):
    """Construct image URL from Flashpoint game ID"""
    # URL format: /Logos/{first2}/{next2}/{id}.png?type=jpg
    first2 = game_id[:2]
    next2 = game_id[2:4]
    return f"{IMAGE_BASE}/{first2}/{next2}/{game_id}.png?type=jpg"

def search_flashpoint(title):
    """Search Flashpoint database for a game"""
    try:
        # Clean up title for search
        clean_title = title.strip()
        response = requests.get(
            SEARCH_API,
            params={"title": clean_title},
            timeout=15
        )
        if response.status_code == 200:
            results = response.json()
            if results:
                return results
    except Exception as e:
        print(f"  Search error: {e}")
    return []

def download_image(url, save_path):
    """Download image from URL"""
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200 and len(response.content) > 500:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(response.content)
            return True, len(response.content)
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def find_best_match(title, results):
    """Find best matching result from search"""
    title_lower = title.lower().strip()
    
    # Exact match first
    for r in results:
        if r.get('title', '').lower() == title_lower:
            return r
    
    # Check alternate titles
    for r in results:
        alts = r.get('alternateTitles', '') or ''
        for alt in alts.split(';'):
            if alt.strip().lower() == title_lower:
                return r
    
    # Partial match - title starts with search term
    for r in results:
        if r.get('title', '').lower().startswith(title_lower):
            return r
    
    # Return first result if any
    return results[0] if results else None

def main():
    # Load ruffle games
    ruffle_path = DATA_DIR / "ruffleGames.json"
    with open(ruffle_path, 'r', encoding='utf-8') as f:
        games = json.load(f)
    
    print(f"Loaded {len(games)} flash games")
    
    # Find games needing thumbnails
    needs_thumb = []
    for game in games:
        thumb = game.get('thumbnail', '')
        if not thumb or thumb == '':
            needs_thumb.append(game)
            continue
        
        # Check if thumbnail exists
        thumb_path = GAMES_DIR / thumb
        if not thumb_path.exists():
            needs_thumb.append(game)
    
    print(f"Games needing thumbnails: {len(needs_thumb)}")
    
    if not needs_thumb:
        print("All games have thumbnails!")
        return
    
    # Process games
    success = 0
    failed = 0
    not_found = 0
    
    # Create webp folder for new thumbnails
    webp_dir = GAMES_DIR / "webp"
    webp_dir.mkdir(exist_ok=True)
    
    for i, game in enumerate(needs_thumb, 1):
        title = game['name']
        slug = game['slug']
        
        print(f"[{i}/{len(needs_thumb)}] {title}...", end=" ", flush=True)
        
        # Search Flashpoint
        results = search_flashpoint(title)
        
        if not results:
            print("NOT FOUND in Flashpoint")
            not_found += 1
            continue
        
        # Find best match
        match = find_best_match(title, results)
        if not match:
            print("NO MATCH")
            not_found += 1
            continue
        
        # Get image
        game_id = match['id']
        image_url = get_image_url(game_id)
        
        # Download
        save_name = slug.replace('/', '-') + ".webp"
        save_path = webp_dir / save_name
        
        ok, result = download_image(image_url, save_path)
        
        if ok:
            print(f"OK ({result} bytes) - matched '{match['title']}'")
            # Update game thumbnail in JSON
            game['thumbnail'] = f"webp/{save_name}"
            success += 1
        else:
            print(f"DOWNLOAD FAILED: {result}")
            failed += 1
        
        # Rate limit
        time.sleep(0.2)
    
    # Save updated JSON
    with open(ruffle_path, 'w', encoding='utf-8') as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
        f.write('\n')
    
    print(f"\n=== SUMMARY ===")
    print(f"Successfully downloaded: {success}")
    print(f"Failed to download: {failed}")
    print(f"Not found in Flashpoint: {not_found}")

if __name__ == "__main__":
    main()
