#!/usr/bin/env python3
"""
MLB Skins 2026 — Real-Time Updater
Runs every 5 minutes via cron. Fetches standings and pushes to GitHub
only when the data has actually changed since the last update.

Cron schedule (every 5 minutes):
  */5 * * * * /Library/Frameworks/Python.framework/Versions/3.14/bin/python3 /Users/ryantran/Documents/skins/MLB_Skins_2026-27.py >> /Users/ryantran/Documents/skins/mlb_log.txt 2>&1
"""

import urllib.request
import json
import ssl
import os
import subprocess
from datetime import datetime

# ── People Configuration ───────────────────────────────────────────────────────
PEOPLE = {
    "Jared": [
        ("Rockies",  "losses"),
        ("Cubs",     "wins"),
        ("Twins",    "losses"),
        ("Tigers",   "wins"),
        ("Red Sox",  "wins"),
        ("Brewers",  "wins"),
        ("Padres",   "wins"),
    ],
    "Bogo": [
        ("Dodgers",   "wins"),
        ("Yankees",   "wins"),
        ("Phillies",  "wins"),
        ("Athletics", "losses"),
        ("Blue Jays", "wins"),
        ("Orioles",   "wins"),
        ("Rangers",   "wins"),
    ],
    "RT": [
        ("Nationals", "losses"),
        ("Angels",    "losses"),
        ("Marlins",   "losses"),
        ("Rays",      "losses"),
        ("Pirates",   "losses"),
        ("Astros",    "wins"),
        ("Guardians", "wins"),
    ],
    "Nuney": [
        ("White Sox",  "losses"),
        ("Cardinals",  "losses"),
        ("Mets",       "wins"),
        ("Mariners",   "wins"),
        ("Braves",     "wins"),
        ("D-backs",    "losses"),
        ("Giants",     "wins"),
    ],
}

STANDINGS_URL = (
    "https://statsapi.mlb.com/api/v1/standings"
    "?leagueId=103,104"
    "&season={year}"
    "&standingsTypes=regularSeason"
    "&fields=records,teamRecords,team,name,wins,losses"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(SCRIPT_DIR, "data.json")
# ──────────────────────────────────────────────────────────────────────────────


def make_request(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
        return json.loads(resp.read())


def fetch_standings(year):
    data = make_request(STANDINGS_URL.format(year=year))
    teams = []
    for division in data.get("records", []):
        for record in division.get("teamRecords", []):
            teams.append({
                "name":   record["team"]["name"],
                "wins":   record["wins"],
                "losses": record["losses"],
            })
    return teams


def calculate_all(all_teams):
    results = []
    for person, team_list in PEOPLE.items():
        person_teams = []
        total = 0
        for team_name, stat in team_list:
            match = next((t for t in all_teams if team_name.lower() in t["name"].lower()), None)
            if match:
                value = match[stat]
                total += value
                person_teams.append({"team": match["name"], "stat": stat.capitalize(), "value": value})
            else:
                person_teams.append({"team": team_name, "stat": stat.capitalize(), "value": 0})
        results.append({"name": person, "teams": person_teams, "total": total})
    return results


def load_existing_data():
    """Load the current data.json to compare against new data."""
    try:
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


def data_has_changed(new_results, existing_data):
    """Return True if standings have changed since last update."""
    if not existing_data or "people" not in existing_data:
        return True
    # Compare totals and individual values
    existing_map = {p["name"]: p for p in existing_data["people"]}
    for person in new_results:
        name = person["name"]
        if name not in existing_map:
            return True
        if person["total"] != existing_map[name]["total"]:
            return True
        for i, team in enumerate(person["teams"]):
            if team["value"] != existing_map[name]["teams"][i]["value"]:
                return True
    return False


def write_data_json(results):
    now = datetime.now().strftime("%b %d, %Y at %I:%M %p")
    payload = {"updated": now, "people": results}
    with open(DATA_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"data.json saved.")


def push_to_github():
    print("Pushing to GitHub...")
    for cmd in [
        ["git", "-C", SCRIPT_DIR, "pull", "--rebase"],
        ["git", "-C", SCRIPT_DIR, "add", "data.json"],
        ["git", "-C", SCRIPT_DIR, "commit", "-m", f"Update {datetime.now().strftime('%Y-%m-%d %H:%M')}"],
        ["git", "-C", SCRIPT_DIR, "push"],
    ]:
        result = subprocess.run(cmd, capture_output=True, text=True)
        out = result.stdout.strip() or result.stderr.strip()
        if out:
            print(out)


def main():
    year = datetime.now().year
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n[{now_str}] Checking standings...")

    all_teams = fetch_standings(year)
    results = calculate_all(all_teams)
    existing = load_existing_data()

    if not data_has_changed(results, existing):
        print("No changes — skipping update.")
        return

    print("Standings changed! Updating site...")

    # Print leaderboard
    print(f"\n{'='*48}")
    for p in sorted(results, key=lambda x: x["total"], reverse=True):
        print(f"  {p['name']:<20} {p['total']}")
    print(f"{'='*48}\n")

    write_data_json(results)
    push_to_github()
    print("Done! Site updated at https://playskins.vercel.app")


if __name__ == "__main__":
    main()
