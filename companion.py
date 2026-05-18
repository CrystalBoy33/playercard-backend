#!/usr/bin/env python3
"""
PlayerCard Companion App
Watches the WoW SavedVariables file and syncs reviews/endorsements
to the PlayerCard API in real time.

Usage:
    python companion.py
    python companion.py --wow-path "D:/Games/World of Warcraft/_retail_"
    python companion.py --api-url "https://api.playercard.gg"
"""

import os
import re
import time
import json
import argparse
import hashlib
import requests
from pathlib import Path
from datetime import datetime

# ============================================================
# Config
# ============================================================

DEFAULT_WOW_PATHS = [
    r"C:\Program Files (x86)\World of Warcraft\_retail_",
    r"C:\Program Files\World of Warcraft\_retail_",
    r"D:\World of Warcraft\_retail_",
    os.path.expanduser("~/Games/World of Warcraft/_retail_"),
]

API_URL      = os.getenv("PLAYERCARD_API_URL", "http://localhost:8000")
POLL_SECONDS = 5   # how often to check for changes


# ============================================================
# Lua parser — minimal, handles PlayerCardDB structure
# ============================================================

def parse_lua_value(text: str):
    """Parse a Lua value into a Python object. Supports string, number, bool, table."""
    text = text.strip()
    if text == "true":  return True
    if text == "false": return False
    if text == "nil":   return None

    # String
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1].replace('\\"', '"').replace("\\n", "\n")

    # Number
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        pass

    # Table: { ... }
    if text.startswith("{") and text.endswith("}"):
        return parse_lua_table(text[1:-1].strip())

    return text  # fallback: return as-is


def parse_lua_table(inner: str) -> dict | list:
    """Parse the contents of a Lua table { ... }."""
    items = split_lua_items(inner)
    result_dict = {}
    result_list = []
    is_array = True

    for item in items:
        item = item.strip()
        if not item:
            continue

        # Key-value: ["key"] = value  or  key = value
        kv_match = re.match(r'^\["?(.+?)"?\]\s*=\s*(.+)$', item, re.DOTALL)
        if not kv_match:
            kv_match = re.match(r'^(\w+)\s*=\s*(.+)$', item, re.DOTALL)

        if kv_match:
            is_array = False
            key   = kv_match.group(1).strip('"')
            value = parse_lua_value(kv_match.group(2).strip().rstrip(","))
            result_dict[key] = value
        else:
            # Array element
            result_list.append(parse_lua_value(item.rstrip(",")))

    return result_list if is_array and result_list else result_dict


def split_lua_items(s: str) -> list[str]:
    """Split a Lua table body by commas, respecting nested braces/strings."""
    items = []
    depth  = 0
    in_str = False
    buf    = []

    for ch in s:
        if ch == '"' and not in_str:
            in_str = True; buf.append(ch)
        elif ch == '"' and in_str:
            in_str = False; buf.append(ch)
        elif not in_str and ch == "{":
            depth += 1; buf.append(ch)
        elif not in_str and ch == "}":
            depth -= 1; buf.append(ch)
        elif not in_str and ch == "," and depth == 0:
            items.append("".join(buf)); buf = []
        else:
            buf.append(ch)

    if buf:
        items.append("".join(buf))

    return items


def load_saved_variables(path: Path) -> dict:
    """Parse PlayerCardDB.lua and return the DB dict."""
    text = path.read_text(encoding="utf-8")
    # Find PlayerCardDB = { ... }
    match = re.search(r"PlayerCardDB\s*=\s*(\{.+\})", text, re.DOTALL)
    if not match:
        return {}
    try:
        return parse_lua_table(match.group(1)[1:-1].strip())
    except Exception as e:
        print(f"[!] Parse error: {e}")
        return {}


# ============================================================
# API client
# ============================================================

session = requests.Session()
session.headers.update({"Content-Type": "application/json"})


def api_post(endpoint: str, data: dict) -> bool:
    try:
        r = session.post(f"{API_URL}{endpoint}", json=data, timeout=10)
        if r.status_code in (200, 201):
            return True
        if r.status_code == 409:
            return True  # already exists, that's fine
        print(f"[!] API {endpoint} returned {r.status_code}: {r.text[:120]}")
        return False
    except requests.RequestException as e:
        print(f"[!] API error ({endpoint}): {e}")
        return False


def sync_review(player_key: str, review: dict) -> bool:
    author = review.get("author", "")
    rating = review.get("rating", 3)
    role   = review.get("role", "UNKNOWN")
    text   = review.get("text", "")
    edited = review.get("edited", False)

    if not author or not text:
        return False

    if edited:
    	endpoint = f"/reviews/{player_key}/{author}/edit"
    	return api_post(endpoint, {"rating": rating, "role": role, "text": text})
    else:
        return api_post("/reviews/", {
            "player_key": player_key,
            "author":     author,
            "rating":     rating,
            "role":       role,
            "text":       text,
        })


def sync_endorsement(player_key: str, badge: str, author: str) -> bool:
    return api_post("/endorsements/", {
        "player_key": player_key,
        "author":     author,
        "badge":      badge,
    })


def sync_player(player_key: str, stats: dict) -> bool:
    if not stats:
        return False
    name, realm = (player_key.split("-", 1) + ["Unknown"])[:2]
    return api_post("/players/upsert", {
        "player_key":   player_key,
        "name":         name,
        "realm":        realm,
        "player_class": stats.get("class"),
        "spec":         stats.get("spec"),
        "guild":        stats.get("guild"),
        "item_level":   stats.get("ilvl"),
    })


def sync_keystones(player_key: str, history: list) -> None:
    for run in history:
        api_post("/keystones/", {
            "player_key": player_key,
            "partner":    player_key,
            "map_id":     run.get("mapID", 0),
            "level":      run.get("level", 0),
        })


# ============================================================
# File watcher
# ============================================================

def get_file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def find_saved_variables(wow_path: str) -> Path | None:
    base = Path(wow_path)
    candidates = list(base.glob("WTF/Account/*/SavedVariables/PlayerCard.lua"))
    if not candidates:
        candidates = list(base.glob("WTF/Account/*/SavedVariables/PlayerCard*.lua"))
    return candidates[0] if candidates else None


def sync_all(db: dict, synced: set) -> int:
    count = 0
    players = db.get("players", {})
    history = db.get("keystoneHistory", {})
    endorsed = db.get("myEndorsements", {})

    for player_key, player in players.items():
        stats   = player.get("cachedStats", {})
        reviews = player.get("reviews", [])
        if not isinstance(reviews, list):
            reviews = list(reviews.values()) if isinstance(reviews, dict) else []

        sync_player(player_key, stats)

        for rev in reviews:
            if not isinstance(rev, dict):
                continue
            uid = f"rev:{player_key}:{rev.get('author')}:{rev.get('timestamp')}"
            if uid not in synced:
                if sync_review(player_key, rev):
                    synced.add(uid)
                    count += 1

        # Keystone history
        runs = history.get(player_key, [])
        if isinstance(runs, list):
            for run in runs:
                uid = f"key:{player_key}:{run.get('timestamp')}"
                if uid not in synced:
                    sync_keystones(player_key, [run])
                    synced.add(uid)

    # Endorsements we gave
    for player_key, badges in endorsed.items():
        if not isinstance(badges, dict):
            continue
        for badge, given in badges.items():
            if given:
                uid = f"end:{player_key}:{badge}"
                if uid not in synced:
                    my_name = db.get("_myName", "Unknown")
                    if sync_endorsement(player_key, badge, my_name):
                        synced.add(uid)

    return count


def run(wow_path: str, api_url: str):
    global API_URL
    API_URL = api_url

    print(f"PlayerCard Companion App")
    print(f"  WoW path : {wow_path}")
    print(f"  API      : {api_url}")
    print(f"  Polling every {POLL_SECONDS}s — press Ctrl+C to stop\n")

    sv_path = find_saved_variables(wow_path)
    if not sv_path:
        print(f"[!] SavedVariables file not found in {wow_path}")
        print("    Make sure PlayerCard addon is installed and you have logged in at least once.")
        return

    print(f"[+] Watching: {sv_path}\n")

    last_hash = ""
    synced    = set()

    while True:
        try:
            current_hash = get_file_hash(sv_path)
            if current_hash != last_hash:
                last_hash = current_hash
                db = load_saved_variables(sv_path)
                if db:
                    count = sync_all(db, synced)
                    if count > 0:
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"[{ts}] Synced {count} new item(s) to {api_url}")
        except Exception as e:
            print(f"[!] Error: {e}")

        time.sleep(POLL_SECONDS)


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PlayerCard Companion App")
    parser.add_argument(
        "--wow-path",
        default=next((p for p in DEFAULT_WOW_PATHS if Path(p).exists()), DEFAULT_WOW_PATHS[0]),
        help="Path to World of Warcraft _retail_ directory"
    )
    parser.add_argument(
        "--api-url",
        default=API_URL,
        help="PlayerCard API base URL"
    )
    args = parser.parse_args()
    run(args.wow_path, args.api_url)
