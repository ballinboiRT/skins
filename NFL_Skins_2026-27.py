#!/usr/bin/env python3
"""
NFL Skins 2026 — Daily Updater
Fetches NFL standings via ESPN API, writes nfl_data.json, pushes to GitHub.
Vercel auto-deploys whenever GitHub is updated.

Add to your crontab (runs every 5 minutes):
  crontab -e
  Add this line (replace ryantran with your Mac username from: whoami):
  */5 * * * * /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 /Users/ryantran/Documents/skins/NFL_Skins_2026-27.py >> /Users/ryantran/Documents/skins/nfl_log.txt 2>&1
"""

import urllib.request
import json
import ssl
import os
import subprocess
from datetime import datetime

# ── People Configuration ───────────────────────────────────────────────────────
PEOPLE = {
    "Mickey": [
        ("Cardinals", "losses"),
        ("Saints",    "losses"),
        ("Patriots",  "wins"),
        ("Steelers",  "wins"),
    ],
    "John": [
        ("Dolphins",    "losses"),
        ("Chargers",    "wins"),
        ("Cowboys",     "wins"),
        ("Buccaneers",  "wins"),
    ],
    "Paul I": [
        ("Rams",     "wins"),
        ("Eagles",   "wins"),
        ("49ers",    "wins"),
        ("Jaguars",  "wins"),
    ],
    "Jared": [
        ("Browns",  "losses"),
        ("Texans",  "wins"),
        ("Broncos", "wins"),
        ("Packers", "wins"),
    ],
    "Bogo": [
        ("Ravens",   "wins"),
        ("Seahawks", "wins"),
        ("Bengals",  "wins"),
        ("Bears",    "wins"),
    ],
    "Daniel": [
        ("Raiders",  "losses"),
        ("Lions",    "wins"),
        ("Panthers", "losses"),
        ("Colts",    "wins"),
    ],
    "Ryan N": [
        ("Jets",        "losses"),
        ("Falcons",     "losses"),
        ("Commanders",  "losses"),
        ("Chiefs",      "wins"),
    ],
    "Ryan T": [
        ("Bills",   "wins"),
        ("Titans",  "losses"),
        ("Giants",  "losses"),
        ("Vikings", "losses"),
    ],
}

# ESPN NFL standings API (public, no key required)
STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports/football/nfl/standings"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(SCRIPT_DIR, "nfl_data.json")
# ──────────────────────────────────────────────────────────────────────────────


def make_request(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
        return json.loads(resp.read())


def fetch_standings():
    """Fetch all 32 NFL teams with wins and losses from ESPN API."""
    data = make_request(STANDINGS_URL)
    teams = []

    # ESPN standings: data["children"] = conferences (AFC, NFC)
    # each conference has "standings" -> "entries" -> list of teams
    for conference in data.get("children", []):
        for entry in conference.get("standings", {}).get("entries", []):
            team_info = entry.get("team", {})
            team_name = team_info.get("displayName", "")    # "San Francisco 49ers"
            short_name = team_info.get("shortDisplayName", "")  # "49ers"
            nickname   = team_info.get("name", "")              # "49ers"

            wins = losses = 0
            for stat in entry.get("stats", []):
                if stat.get("name") == "wins":
                    wins = int(stat.get("value", 0))
                elif stat.get("name") == "losses":
                    losses = int(stat.get("value", 0))

            teams.append({
                "name":     team_name,
                "short":    short_name,
                "nickname": nickname,
                "wins":     wins,
                "losses":   losses,
            })

    return teams


def find_team(all_teams, search_name):
    """Find a team by partial name match (case-insensitive)."""
    s = search_name.lower()
    for t in all_teams:
        if (s in t["name"].lower() or
            s in t["short"].lower() or
            s in t["nickname"].lower()):
            return t
    return None


def calculate_all(all_teams):
    results = []
    for person, team_list in PEOPLE.items():
        person_teams, total = [], 0
        for team_name, stat in team_list:
            match = find_team(all_teams, team_name)
            if match:
                value = match[stat]
                total += value
                person_teams.append({
                    "team":  match["name"],
                    "stat":  stat.capitalize(),
                    "value": value,
                })
            else:
                print(f"  WARNING: '{team_name}' not found in standings")
                person_teams.append({
                    "team":  team_name,
                    "stat":  stat.capitalize(),
                    "value": 0,
                })
        results.append({"name": person, "teams": person_teams, "total": total})
    return results


def load_existing_data():
    try:
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    except:
        return None


def data_has_changed(new_results, existing_data):
    if not existing_data or "people" not in existing_data:
        return True
    existing_map = {p["name"]: p for p in existing_data["people"]}
    for person in new_results:
        name = person["name"]
        if name not in existing_map:
            return True
        if person["total"] != existing_map[name]["total"]:
            return True
        for i, team in enumerate(person["teams"]):
            if i < len(existing_map[name]["teams"]):
                if team["value"] != existing_map[name]["teams"][i]["value"]:
                    return True
    return False


def write_data_json(results):
    now = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    payload = {"updated": now, "people": results}
    with open(DATA_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"nfl_data.json saved.")


def push_to_github():
    print("Pushing to GitHub...")
    for cmd in [
        ["git", "-C", SCRIPT_DIR, "pull", "--rebase"],
        ["git", "-C", SCRIPT_DIR, "add", "nfl_data.json"],
        ["git", "-C", SCRIPT_DIR, "commit", "-m", f"NFL update {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
        ["git", "-C", SCRIPT_DIR, "push"],
    ]:
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = result.stdout.strip() or result.stderr.strip()
        if out:
            print(out)


def print_summary(results):
    print(f"\n{'='*48}")
    print(f"  NFL Skins 2026  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*48}")
    for p in sorted(results, key=lambda x: x["total"], reverse=True):
        print(f"  {p['name']:<20} {p['total']}")
    print(f"{'='*48}\n")


def main():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n[{now_str}] Checking NFL standings...")
    try:
        all_teams = fetch_standings()
        if not all_teams:
            print("No team data returned — NFL season may not have started yet.")
            return
        results = calculate_all(all_teams)
        existing = load_existing_data()
        if not data_has_changed(results, existing):
            print("No changes — skipping update.")
            return
        print("Standings changed! Updating site...")
        print_summary(results)
        write_data_json(results)
        push_to_github()
        print("Done! Site updated at https://playskins.vercel.app")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
