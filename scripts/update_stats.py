"""Fetch GitHub contribution data and render the profile cards.

Usage:
    GITHUB_TOKEN=... GITHUB_LOGIN=Tejas-v-krishna python scripts/update_stats.py

In GitHub Actions the token and login are provided automatically by the
workflow. Locally, the script falls back to `gh auth token` when available.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
BLUE = "#58a6ff"
GREEN = "#3fb950"
GRID = "#21262d"

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def token_from_env_or_gh() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    gh = shutil.which("gh")
    if gh:
        try:
            return subprocess.check_output([gh, "auth", "token"], text=True).strip()
        except Exception:
            pass
    raise SystemExit("GITHUB_TOKEN is required (or run `gh auth login` first).")


def login_from_env_or_gh() -> str:
    login = os.environ.get("GITHUB_LOGIN")
    if login:
        return login
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        return repo.split("/", 1)[0]
    gh = shutil.which("gh")
    if gh:
        try:
            return subprocess.check_output([gh, "api", "user", "--jq", ".login"], text=True).strip()
        except Exception:
            pass
    raise SystemExit("GITHUB_LOGIN is required.")


def graphql(token: str, query: str, variables: dict) -> dict:
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-readme-stats/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if "errors" in data:
        raise SystemExit(json.dumps(data["errors"], indent=2))
    return data["data"]["user"]


def fetch_user(token: str, login: str) -> dict:
    base_query = """
    query($login: String!) {
      user(login: $login) {
        createdAt
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }
    """
    user = graphql(token, base_query, {"login": login})

    created = dt.date.fromisoformat(user["createdAt"][:10])
    current_year = dt.date.today().year
    aliases = []
    for year in range(created.year, current_year + 1):
        aliases.append(
            f'y{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", '
            f'to: "{year}-12-31T23:59:59Z") {{ contributionCalendar {{ totalContributions }} }}'
        )
    years_query = "query($login: String!) { user(login: $login) { " + " ".join(aliases) + " } }"
    years_user = graphql(token, years_query, {"login": login})

    total = sum(
        int(value["contributionCalendar"]["totalContributions"])
        for key, value in years_user.items()
        if key.startswith("y")
    )

    days = [
        (dt.date.fromisoformat(day["date"]), int(day["contributionCount"]))
        for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]
        for day in week["contributionDays"]
    ]
    days.sort()
    return {
        "login": login,
        "created": created,
        "total": total,
        "days": days,
    }


def streaks(days: list[tuple[dt.date, int]]) -> dict:
    best = current = 0
    best_start = best_end = None
    run_start = None

    for date, count in days:
        if count > 0:
            if current == 0:
                run_start = date
            current += 1
            if current > best:
                best = current
                best_start, best_end = run_start, date
        else:
            current = 0
            run_start = None

    # The calendar ends today. If today has no contribution yet, the current
    # streak is measured up to yesterday.
    current = 0
    current_end = None
    for date, count in reversed(days):
        if count > 0:
            if current == 0:
                current_end = date
            current += 1
        elif date < dt.date.today():
            break
    current_start = None
    if current and current_end:
        current_start = current_end - dt.timedelta(days=current - 1)

    return {
        "current": current,
        "current_start": current_start,
        "current_end": current_end,
        "best": best,
        "best_start": best_start,
        "best_end": best_end,
    }


def fmt_date(date: dt.date | None) -> str:
    if date is None:
        return ""
    return date.strftime("%b %-d") if os.name != "nt" else date.strftime("%b %d").replace(" 0", " ")


def date_range(start: dt.date | None, end: dt.date | None) -> str:
    if not start or not end:
        return "No active streak"
    return f"{fmt_date(start)} – {fmt_date(end)}"


def render_stats(login: str, total: int, created: dt.date, streak: dict) -> str:
    total_sub = f"{created.strftime('%b %Y')} – Present"
    current_sub = date_range(streak["current_start"], streak["current_end"])
    best_sub = date_range(streak["best_start"], streak["best_end"])

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="205" viewBox="0 0 900 205" role="img" aria-label="GitHub stats for {html.escape(login)}">
  <rect x="1" y="1" width="898" height="203" rx="14" fill="{BG}" stroke="{BORDER}"/>
  <text x="34" y="35" fill="{MUTED}" font-family="{FONT}" font-size="10" letter-spacing="2.2">GITHUB STATS</text>
  <circle cx="27" cy="31.5" r="2.5" fill="{BLUE}"/>
  <line x1="300" y1="58" x2="300" y2="166" stroke="{GRID}"/>
  <line x1="600" y1="58" x2="600" y2="166" stroke="{GRID}"/>
  <g text-anchor="middle" font-family="{FONT}">
    <text x="150" y="98" fill="{TEXT}" font-size="34" font-weight="700">{total:,}</text>
    <text x="150" y="126" fill="{TEXT}" font-size="12" font-weight="600">Total Contributions</text>
    <text x="150" y="146" fill="{MUTED}" font-size="10">{total_sub}</text>

    <text x="450" y="98" fill="{TEXT}" font-size="34" font-weight="700">{streak["current"]}</text>
    <text x="450" y="126" fill="{TEXT}" font-size="12" font-weight="600">Current Streak</text>
    <text x="450" y="146" fill="{MUTED}" font-size="10">{current_sub}</text>

    <text x="750" y="98" fill="{TEXT}" font-size="34" font-weight="700">{streak["best"]}</text>
    <text x="750" y="126" fill="{TEXT}" font-size="12" font-weight="600">Longest Streak</text>
    <text x="750" y="146" fill="{MUTED}" font-size="10">{best_sub}</text>
  </g>
  <text x="866" y="188" fill="{MUTED}" font-size="9" text-anchor="end" font-family="{FONT}">updated {dt.date.today().isoformat()}</text>
</svg>
"""


def month_starts(start: dt.date, end: dt.date) -> list[tuple[dt.date, str]]:
    result = []
    cursor = dt.date(start.year, start.month, 1)
    while cursor <= end:
        result.append((cursor, cursor.strftime("%b")))
        if cursor.month == 12:
            cursor = dt.date(cursor.year + 1, 1, 1)
        else:
            cursor = dt.date(cursor.year, cursor.month + 1, 1)
    return result


def render_activity(login: str, days: list[tuple[dt.date, int]]) -> str:
    # Last 365 days, ending today.
    end = days[-1][0]
    start = end - dt.timedelta(days=364)
    window = [(d, c) for d, c in days if start <= d <= end]
    if len(window) < 2:
        window = days[-365:]

    width, height = 900, 300
    left, right = 58, 866
    top, bottom = 70, 238
    chart_w, chart_h = right - left, bottom - top
    max_count = max(c for _, c in window) or 1
    y_max = max(10, ((max_count + 9) // 10) * 10)

    def x_at(index: int) -> float:
        return left + (index / (len(window) - 1)) * chart_w

    def y_at(count: int) -> float:
        return bottom - (count / y_max) * chart_h

    points = [(x_at(i), y_at(c)) for i, (_, c) in enumerate(window)]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    area = f"{left:.2f},{bottom:.2f} " + line + f" {right:.2f},{bottom:.2f}"

    grid = []
    for tick in range(0, y_max + 1, max(10, y_max // 5)):
        y = y_at(tick)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        grid.append(f'<text x="{left - 12}" y="{y + 3:.1f}" fill="{MUTED}" font-size="9" text-anchor="end" font-family="{FONT}">{tick}</text>')

    months = []
    for date, label in month_starts(start, end):
        index = next((i for i, (d, _) in enumerate(window) if d >= date), None)
        if index is None:
            continue
        x = x_at(index)
        months.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="{GRID}" stroke-width="1" stroke-dasharray="2 5"/>')
        months.append(f'<text x="{x:.1f}" y="{bottom + 20}" fill="{MUTED}" font-size="9" text-anchor="middle" font-family="{FONT}">{label}</text>')

    total = sum(c for _, c in window)
    last_x, last_y = points[-1]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="300" viewBox="0 0 900 300" role="img" aria-label="Contribution activity for {html.escape(login)}">
  <defs>
    <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{BLUE}" stop-opacity="0.28"/>
      <stop offset="100%" stop-color="{BLUE}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="898" height="298" rx="14" fill="{BG}" stroke="{BORDER}"/>
  <text x="34" y="35" fill="{TEXT}" font-family="{FONT}" font-size="13" font-weight="600">Contribution activity</text>
  <text x="866" y="35" fill="{MUTED}" font-family="{FONT}" font-size="10" text-anchor="end">Last 12 months</text>
  {''.join(grid)}
  {''.join(months)}
  <polygon points="{area}" fill="url(#area)"/>
  <polyline points="{line}" fill="none" stroke="{BLUE}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>
  <circle cx="{last_x:.2f}" cy="{last_y:.2f}" r="3.2" fill="{BG}" stroke="{BLUE}" stroke-width="2"/>
  <text x="866" y="278" fill="{MUTED}" font-family="{FONT}" font-size="10" text-anchor="end">{total:,} contributions</text>
  <text x="34" y="278" fill="{MUTED}" font-family="{FONT}" font-size="10">{start.strftime('%b %-d, %Y') if os.name != 'nt' else start.strftime('%b %d, %Y')} – {end.strftime('%b %-d, %Y') if os.name != 'nt' else end.strftime('%b %d, %Y')}</text>
</svg>
"""


def main() -> None:
    token = token_from_env_or_gh()
    login = login_from_env_or_gh()
    user = fetch_user(token, login)
    streak = streaks(user["days"])

    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "stats.svg").write_text(
        render_stats(login, user["total"], user["created"], streak), encoding="utf-8"
    )
    (ASSETS / "activity.svg").write_text(render_activity(login, user["days"]), encoding="utf-8")
    print(f"Wrote assets/stats.svg and assets/activity.svg for {login}")
    print(
        f"total={user['total']} current={streak['current']} "
        f"longest={streak['best']} days={len(user['days'])}"
    )


if __name__ == "__main__":
    main()
