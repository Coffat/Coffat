#!/usr/bin/env python3
"""
Cozy Lo-fi Espresso & Warm Amber GitHub Profile Generator for Coffat (CoffatDev).
Pure Python 3 standard library — zero third-party dependencies.

Generates paired Dark & Light 880px-wide SVGs in assets/:
  - hero-lofi-dark.svg                 / hero-lofi-light.svg
  - stats-cards-dark.svg               / stats-cards-light.svg
  - activity-graph-dark.svg            / activity-graph-light.svg
  - pacman-contribution-graph-dark.svg / pacman-contribution-graph.svg (unless --skip-pacman)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = os.environ.get("GITHUB_USERNAME", "Coffat")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets"

UI_FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO_FONT = "'SFMono-Regular', ui-monospace, Consolas, 'Liberation Mono', Menlo, monospace"

EXCLUDED_LANGUAGES = {
    "html",
    "css",
    "scss",
    "less",
    "makefile",
    "dockerfile",
    "shell",
    "batchfile",
    "powershell",
}

GRAPHQL_LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

LANGUAGE_COLORS = {
    "python": "#3572A5",
    "java": "#E08E45",
    "typescript": "#3178C6",
    "kotlin": "#A97BFF",
    "javascript": "#F1E05A",
    "go": "#00ADD8",
    "rust": "#DEA584",
    "c++": "#F34B7D",
    "c": "#7D8590",
    "c#": "#178600",
    "dart": "#00B4AB",
    "swift": "#F05138",
    "php": "#4F5D95",
    "ruby": "#CC342D",
    "vue": "#41B883",
    "svelte": "#FF3E00",
    "lua": "#000080",
    "sql": "#E38C00",
    "jupyter notebook": "#DA5B0B",
}

THEMES = {
    "dark": {
        "canvas": "#0d1117",
        "card": "#13161f",
        "inner": "#191d28",
        "border": "#252a38",
        "text": "#f3efe8",
        "secondary": "#9ca3b0",
        "muted": "#6e7685",
        "amber": "#F59E0B",
        "amber_bright": "#FBBF24",
        "green": "#39D353",
        "blue": "#38BDF8",
        "coral": "#FB7185",
        "pill_bg": "#1b202e",
        "pill_border": "#2c3347",
        "grid_line": "#252a38",
        "bar_bg": "#212736",
        "levels": ["#191d28", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "pacman": "#FACC15",
        "ghosts": ["#FB7185", "#F472B6", "#38BDF8"],
        "pupil": "#0d1117",
        # Pixel scene dark palette
        "sky_top": "#0b0e1a",
        "sky_mid": "#15192c",
        "sky_bot": "#261f33",
        "city_far": "#121524",
        "city_near": "#191c2e",
        "city_win": "#F59E0B",
        "window_frame": "#2b2533",
        "cloud": "#2c324a",
        "desk_top": "#4a3326",
        "desk_mid": "#3a261c",
        "desk_front": "#281912",
        "desk_grain": "#5c4030",
        "lamp_metal": "#94a3b8",
        "lamp_shade": "#D97706",
        "lamp_glow": "#FBBF24",
        "monitor_bezel": "#252b3b",
        "monitor_edge": "#363e54",
        "screen_bg": "#0b0f17",
        "mug_body": "#D97706",
        "mug_shade": "#B45309",
        "mug_rim": "#FDE68A",
        "steam": "#e2e8f0",
        "cat_body": "#1d1a26",
        "cat_ear": "#FB7185",
        "cat_eye": "#FBBF24",
        "cat_highlight": "#2f2a3d",
    },
    "light": {
        "canvas": "#ffffff",
        "card": "#FFFDF8",
        "inner": "#F6F2EA",
        "border": "#E6DFD3",
        "text": "#1F1D1A",
        "secondary": "#5C564E",
        "muted": "#8A8277",
        "amber": "#D97706",
        "amber_bright": "#F59E0B",
        "green": "#2DA44E",
        "blue": "#0284C7",
        "coral": "#E11D48",
        "pill_bg": "#F6EFE2",
        "pill_border": "#E5D8C3",
        "grid_line": "#EAE2D6",
        "bar_bg": "#ECE5D9",
        "levels": ["#EFEAE0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
        "pacman": "#EAB308",
        "ghosts": ["#E11D48", "#EC4899", "#0284C7"],
        "pupil": "#1F1D1A",
        # Pixel scene light palette
        "sky_top": "#FCE2C4",
        "sky_mid": "#FAD4B2",
        "sky_bot": "#F7C59F",
        "city_far": "#E4C4A8",
        "city_near": "#D4AE90",
        "city_win": "#FFF7ED",
        "window_frame": "#C8A98E",
        "cloud": "#FFF7ED",
        "desk_top": "#B68256",
        "desk_mid": "#9E6B43",
        "desk_front": "#7D5232",
        "desk_grain": "#C99669",
        "lamp_metal": "#64748b",
        "lamp_shade": "#B45309",
        "lamp_glow": "#F59E0B",
        "monitor_bezel": "#3B3530",
        "monitor_edge": "#574F48",
        "screen_bg": "#181C24",
        "mug_body": "#C2410C",
        "mug_shade": "#9A3412",
        "mug_rim": "#FEF3C7",
        "steam": "#FFFFFF",
        "cat_body": "#4A3728",
        "cat_ear": "#F472B6",
        "cat_eye": "#FDE047",
        "cat_highlight": "#634B38",
    },
}


# ---------------------------------------------------------------------------
# HTTP & GitHub Data Fetching
# ---------------------------------------------------------------------------
def http_get_json(url: str, headers: dict[str, str] | None = None) -> dict | list:
    req_headers = {"User-Agent": "Coffat-Profile-Generator/3.0"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req_headers = {
        "User-Agent": "Coffat-Profile-Generator/3.0",
        "Content-Type": "application/json",
    }
    req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compute_streaks(days: list[tuple[str, int, int]]) -> tuple[int, int, int]:
    """Return (current_streak, longest_streak, active_days) from sorted (date, count, level)."""
    longest = 0
    running = 0
    active_days = 0
    for _, count, _ in days:
        if count > 0:
            active_days += 1
            running += 1
            if running > longest:
                longest = running
        else:
            running = 0

    current = 0
    idx = len(days) - 1
    if idx >= 0 and days[idx][1] == 0:
        idx -= 1
    while idx >= 0 and days[idx][1] > 0:
        current += 1
        idx -= 1
    return current, longest, active_days


def filter_top_languages(lang_bytes: dict[str, int], limit: int = 5) -> list[tuple[str, float, str]]:
    """Return top `limit` coding languages as (name, percentage, hex_color)."""
    filtered = [
        (name, size)
        for name, size in lang_bytes.items()
        if name and name.strip().lower() not in EXCLUDED_LANGUAGES and size > 0
    ]
    if not filtered:
        defaults = [
            ("Python", 36.0),
            ("Java", 24.0),
            ("TypeScript", 19.0),
            ("Kotlin", 12.0),
            ("JavaScript", 9.0),
        ][:limit]
        return [(n, p, LANGUAGE_COLORS.get(n.lower(), "#F59E0B")) for n, p in defaults]

    filtered.sort(key=lambda x: (-x[1], x[0].lower()))
    top = filtered[:limit]
    total = sum(size for _, size in top) or 1
    result: list[tuple[str, float, str]] = []
    for name, size in top:
        pct = round((size / total) * 100.0, 1)
        color = LANGUAGE_COLORS.get(name.lower(), "#F59E0B")
        result.append((name, pct, color))
    return result


def build_52x7_grid_from_days(
    days: list[tuple[str, int, int]],
) -> tuple[list[list[tuple[int, int]]], list[datetime.date], list[int], int, int]:
    """
    Build a 52-column x 7-row (Sun=0..Sat=6) grid of (level, count) tuples,
    plus week Sunday dates, weekly commit totals, peak weekly commits, and peak week index.
    """
    today = datetime.datetime.now(datetime.timezone.utc).date()
    if not days:
        empty = [[(0, 0) for _ in range(7)] for _ in range(52)]
        sun_row = (today.weekday() + 1) % 7
        this_sun = today - datetime.timedelta(days=sun_row)
        sundays = [this_sun - datetime.timedelta(weeks=51 - i) for i in range(52)]
        return empty, sundays, [0] * 52, 0, 0

    weeks_map: dict[datetime.date, list[tuple[int, int]]] = {}
    for date_str, count, level in days:
        dt = datetime.date.fromisoformat(date_str)
        sun_row = (dt.weekday() + 1) % 7  # Sun=0, Mon=1, ..., Sat=6
        week_sun = dt - datetime.timedelta(days=sun_row)
        if week_sun not in weeks_map:
            weeks_map[week_sun] = [(0, 0) for _ in range(7)]
        clamped_lvl = max(0, min(4, int(level)))
        weeks_map[week_sun][sun_row] = (clamped_lvl, int(count))

    sorted_sundays = sorted(weeks_map.keys())
    recent = sorted_sundays[-52:]
    grid: list[list[tuple[int, int]]] = [weeks_map[w] for w in recent]
    sundays: list[datetime.date] = list(recent)
    while len(grid) < 52:
        prev_sun = sundays[0] - datetime.timedelta(weeks=1)
        sundays.insert(0, prev_sun)
        grid.insert(0, [(0, 0) for _ in range(7)])

    weekly_counts = [sum(cnt for _, cnt in col) for col in grid]
    peak_week = max(weekly_counts, default=0)
    peak_idx = weekly_counts.index(peak_week) if weekly_counts else 0
    return grid, sundays, weekly_counts, peak_week, peak_idx


def fetch_via_graphql(username: str, token: str) -> dict:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
              }
            }
          }
        }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          totalCount
          nodes {
            stargazerCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                }
              }
            }
          }
        }
      }
    }
    """
    resp = http_post_json(
        "https://api.github.com/graphql",
        {"query": query, "variables": {"login": username}},
        {"Authorization": f"Bearer {token}"},
    )
    if "errors" in resp:
        raise RuntimeError(f"GraphQL errors: {resp['errors']}")

    user = resp["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    total_contributions = int(cal["totalContributions"])

    all_days: list[tuple[str, int, int]] = []
    for week in cal["weeks"]:
        for d in week["contributionDays"]:
            lvl = GRAPHQL_LEVEL_MAP.get(d.get("contributionLevel", "NONE"), 0)
            all_days.append((d["date"], int(d["contributionCount"]), lvl))

    all_days.sort(key=lambda x: x[0])
    current_streak, longest_streak, active_days = compute_streaks(all_days)
    grid, sundays, weekly_counts, peak_week, peak_idx = build_52x7_grid_from_days(all_days)

    repos = user["repositories"]
    public_repos = int(repos["totalCount"])
    total_stars = sum(int(node.get("stargazerCount", 0)) for node in repos["nodes"])

    lang_bytes: dict[str, int] = {}
    for node in repos["nodes"]:
        for edge in node["languages"]["edges"]:
            name = edge["node"]["name"]
            size = int(edge["size"])
            lang_bytes[name] = lang_bytes.get(name, 0) + size

    return {
        "source": "graphql",
        "total_contributions": total_contributions,
        "peak_week": peak_week,
        "peak_idx": peak_idx,
        "weekly_counts": weekly_counts,
        "week_sundays": sundays,
        "public_repos": public_repos,
        "total_stars": total_stars,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "active_days": active_days,
        "grid": grid,
        "top_languages": filter_top_languages(lang_bytes, limit=5),
        "updated_date": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
    }


def fetch_via_rest_and_html(username: str) -> dict:
    repos_raw = http_get_json(f"https://api.github.com/users/{username}/repos?per_page=100&type=owner")
    non_fork = [r for r in repos_raw if not r.get("fork")]
    public_repos = len(non_fork)
    total_stars = sum(int(r.get("stargazers_count", 0)) for r in non_fork)

    lang_bytes: dict[str, int] = {}
    for r in non_fork:
        lang = r.get("language")
        if lang:
            weight = max(int(r.get("size", 1)), 1)
            lang_bytes[lang] = lang_bytes.get(lang, 0) + weight

    req = urllib.request.Request(
        f"https://github.com/users/{username}/contributions",
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8", "ignore")

    header_match = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
    header_total = int(header_match.group(1).replace(",", "")) if header_match else 0

    tip_counts: dict[str, int] = {}
    for tid, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]+)</tool-tip>', html):
        m = re.match(r"^\s*([\d,]+)\s+contribution", text)
        tip_counts[tid] = int(m.group(1).replace(",", "")) if m else 0

    level_fallback = {0: 0, 1: 1, 2: 4, 3: 8, 4: 14}
    all_days: list[tuple[str, int, int]] = []
    for td_tag in re.findall(r'<td\b[^>]*data-date="[^"]+"[^>]*>', html):
        date_m = re.search(r'data-date="([^"]+)"', td_tag)
        if not date_m:
            continue
        date_str = date_m.group(1)
        id_m = re.search(r'id="([^"]+)"', td_tag)
        level_m = re.search(r'data-level="(\d+)"', td_tag)
        lvl = int(level_m.group(1)) if level_m else 0
        if id_m and id_m.group(1) in tip_counts:
            count = tip_counts[id_m.group(1)]
        else:
            count = level_fallback.get(lvl, 0)
        if count > 0 and lvl == 0:
            lvl = 1
        all_days.append((date_str, count, lvl))

    all_days.sort(key=lambda x: x[0])
    total_contributions = header_total or sum(c for _, c, _ in all_days)
    current_streak, longest_streak, active_days = compute_streaks(all_days)
    grid, sundays, weekly_counts, peak_week, peak_idx = build_52x7_grid_from_days(all_days)

    return {
        "source": "rest+html",
        "total_contributions": total_contributions,
        "peak_week": peak_week,
        "peak_idx": peak_idx,
        "weekly_counts": weekly_counts,
        "week_sundays": sundays,
        "public_repos": public_repos,
        "total_stars": total_stars,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "active_days": active_days,
        "grid": grid,
        "top_languages": filter_top_languages(lang_bytes, limit=5),
        "updated_date": datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
    }


def fetch_github_data() -> dict:
    if GITHUB_TOKEN:
        try:
            return fetch_via_graphql(USERNAME, GITHUB_TOKEN)
        except Exception as exc:
            print(f"[warn] GraphQL fetch failed ({exc}); falling back to REST + HTML")
    try:
        return fetch_via_rest_and_html(USERNAME)
    except Exception as exc:
        print(f"[warn] REST + HTML fetch failed ({exc}); using safe fallback")
        today = datetime.datetime.now(datetime.timezone.utc).date()
        sun_row = (today.weekday() + 1) % 7
        this_sun = today - datetime.timedelta(days=sun_row)
        sundays = [this_sun - datetime.timedelta(weeks=51 - i) for i in range(52)]
        grid = []
        for col in range(52):
            col_cells = []
            for row in range(7):
                v = (col * 3 + row * 5) % 11
                lvl = 0 if v < 6 else min(4, v - 5)
                col_cells.append((lvl, lvl * 2))
            grid.append(col_cells)
        weekly_counts = [sum(cnt for _, cnt in col) for col in grid]
        peak_week = max(weekly_counts)
        return {
            "source": "fallback",
            "total_contributions": 682,
            "peak_week": peak_week,
            "peak_idx": weekly_counts.index(peak_week),
            "weekly_counts": weekly_counts,
            "week_sundays": sundays,
            "public_repos": 35,
            "total_stars": 2,
            "current_streak": 0,
            "longest_streak": 15,
            "active_days": 100,
            "grid": grid,
            "top_languages": filter_top_languages({}, limit=5),
            "updated_date": today.isoformat(),
        }


# ---------------------------------------------------------------------------
# SVG 1: COZY LO-FI PIXEL-ART HERO (880 x 256)
# ---------------------------------------------------------------------------
def build_hero_lofi_svg(theme_name: str) -> str:
    t = THEMES[theme_name]
    uid = f"hl-{theme_name}"
    is_dark = theme_name == "dark"

    # Celestial body: pixel crescent moon (dark) or warm pixel sun (light)
    if is_dark:
        celestial = """
        <!-- Pixel crescent moon -->
        <g fill="#FDE68A">
          <rect x="774" y="38" width="12" height="4"/>
          <rect x="770" y="42" width="12" height="4"/>
          <rect x="766" y="46" width="10" height="8"/>
          <rect x="770" y="54" width="12" height="4"/>
          <rect x="774" y="58" width="12" height="4"/>
        </g>
        <g fill="#FEF9C3" opacity="0.55">
          <rect x="774" y="42" width="4" height="4"/>
          <rect x="770" y="46" width="4" height="8"/>
        </g>"""
    else:
        celestial = """
        <!-- Warm pixel sun -->
        <g fill="#F59E0B" opacity="0.22">
          <rect x="762" y="34" width="28" height="28"/>
        </g>
        <g fill="#F59E0B">
          <rect x="770" y="38" width="12" height="4"/>
          <rect x="766" y="42" width="20" height="12"/>
          <rect x="770" y="54" width="12" height="4"/>
        </g>
        <g fill="#FEF3C7">
          <rect x="770" y="42" width="8" height="8"/>
        </g>"""

    # 6 twinkling stars (dark) or sunlit sparkles (light)
    star_coords = [
        (542, 38, "s1"),
        (586, 52, "s2"),
        (634, 34, "s3"),
        (686, 46, "s4"),
        (734, 36, "s5"),
        (824, 54, "s6"),
    ]
    star_color = "#FDE68A" if is_dark else "#FFFBEB"
    stars_svg = []
    for sx, sy, cls in star_coords:
        stars_svg.append(
            f'<g class="{uid}-{cls}" fill="{star_color}">'
            f'<rect x="{sx}" y="{sy}" width="4" height="4"/>'
            f'<rect x="{sx - 2}" y="{sy + 1}" width="8" height="2" opacity="0.5"/>'
            f'<rect x="{sx + 1}" y="{sy - 2}" width="2" height="8" opacity="0.5"/>'
            f"</g>"
        )

    # Weather: diagonal pixel rain (dark) or floating sunlit dust motes (light)
    weather_items = []
    if is_dark:
        rain_drops = [
            (548, 30, "r1"),
            (596, 24, "r2"),
            (648, 32, "r3"),
            (704, 26, "r4"),
            (758, 34, "r5"),
            (812, 28, "r6"),
            (572, 48, "r7"),
            (788, 44, "r8"),
        ]
        for rx, ry, rcls in rain_drops:
            weather_items.append(
                f'<g class="{uid}-{rcls}" fill="#93C5FD" opacity="0.45">'
                f'<rect x="{rx}" y="{ry}" width="2" height="4"/>'
                f'<rect x="{rx - 2}" y="{ry + 4}" width="2" height="4"/>'
                f'<rect x="{rx - 4}" y="{ry + 8}" width="2" height="4"/>'
                f"</g>"
            )
    else:
        motes = [
            (552, 62, "r1"),
            (604, 48, "r2"),
            (658, 66, "r3"),
            (716, 52, "r4"),
            (764, 68, "r5"),
            (816, 58, "r6"),
        ]
        for mx, my, mcls in motes:
            weather_items.append(
                f'<rect class="{uid}-{mcls}" x="{mx}" y="{my}" width="3" height="3" fill="#FFFBEB" opacity="0.75"/>'
            )

    # Distant pixel skyline (inside window y=106..152)
    skyline = f"""
      <!-- Distant city skyline -->
      <g fill="{t['city_far']}">
        <rect x="520" y="114" width="24" height="42"/>
        <rect x="548" y="104" width="20" height="52"/>
        <rect x="576" y="118" width="28" height="38"/>
        <rect x="724" y="110" width="26" height="46"/>
        <rect x="756" y="100" width="24" height="56"/>
        <rect x="786" y="116" width="28" height="40"/>
        <rect x="820" y="108" width="28" height="48"/>
      </g>
      <g fill="{t['city_near']}">
        <rect x="524" y="126" width="32" height="30"/>
        <rect x="562" y="120" width="36" height="36"/>
        <rect x="736" y="122" width="34" height="34"/>
        <rect x="776" y="126" width="38" height="30"/>
        <rect x="818" y="120" width="30" height="36"/>
      </g>
      <!-- Tiny glowing city windows -->
      <g fill="{t['city_win']}" opacity="{'0.72' if is_dark else '0.55'}">
        <rect x="554" y="110" width="4" height="4"/>
        <rect x="554" y="118" width="4" height="4"/>
        <rect x="534" y="132" width="4" height="4"/>
        <rect x="544" y="132" width="4" height="4"/>
        <rect x="572" y="128" width="4" height="4"/>
        <rect x="762" y="108" width="4" height="4"/>
        <rect x="770" y="116" width="4" height="4"/>
        <rect x="744" y="130" width="4" height="4"/>
        <rect x="790" y="134" width="4" height="4"/>
        <rect x="828" y="116" width="4" height="4"/>
        <rect x="828" y="128" width="4" height="4"/>
      </g>"""

    # Scrolling code lines block (height = 60px, repeated twice for seamless loop)
    def code_block(y0: int) -> str:
        rows = [
            # (y_off, [(x_off, w, color), ...])
            (4, [(0, 14, t["coral"]), (18, 22, t["blue"]), (44, 16, t["amber_bright"])]),
            (12, [(8, 18, t["green"]), (30, 30, "#94A3B8"), (64, 14, t["amber"])]),
            (20, [(8, 12, t["amber_bright"]), (24, 24, t["blue"]), (52, 20, t["green"])]),
            (28, [(14, 28, "#CBD5E1"), (46, 18, t["coral"])]),
            (36, [(0, 10, t["coral"]), (14, 26, t["amber_bright"]), (44, 24, t["blue"])]),
            (44, [(8, 22, t["green"]), (34, 14, t["amber"]), (52, 26, "#94A3B8")]),
            (52, [(14, 16, t["blue"]), (34, 34, t["green"])]),
        ]
        rects = []
        for y_off, segs in rows:
            for x_off, w, col in segs:
                rects.append(f'<rect x="{618 + x_off}" y="{y0 + y_off}" width="{w}" height="4" fill="{col}"/>')
        return "".join(rects)

    weather_kf = (
        f"@keyframes {uid}-rain{{0%{{transform:translate(10px,-16px);opacity:0}}20%{{opacity:0.55}}80%{{opacity:0.45}}100%{{transform:translate(-16px,72px);opacity:0}}}}"
        if is_dark
        else f"@keyframes {uid}-rain{{0%,100%{{transform:translate(0px,0px);opacity:0.25}}50%{{transform:translate(6px,-10px);opacity:0.9}}}}"
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="880" height="256" viewBox="0 0 880 256" fill="none" role="img" aria-label="CoffatDev / Vu Toan Thang — Cozy Lo-fi Coder Profile">
  <defs>
    <clipPath id="{uid}-card-clip">
      <rect x="0.5" y="0.5" width="879" height="255" rx="16"/>
    </clipPath>
    <clipPath id="{uid}-scene-clip">
      <rect x="520" y="22" width="328" height="212" rx="12"/>
    </clipPath>
    <clipPath id="{uid}-screen-clip">
      <rect x="612" y="92" width="114" height="56"/>
    </clipPath>
    <linearGradient id="{uid}-sky" x1="0" y1="22" x2="0" y2="160" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['sky_top']}"/>
      <stop offset="55%" stop-color="{t['sky_mid']}"/>
      <stop offset="100%" stop-color="{t['sky_bot']}"/>
    </linearGradient>
    <radialGradient id="{uid}-ambient" cx="0.22" cy="0.25" r="0.65">
      <stop offset="0%" stop-color="{t['amber']}" stop-opacity="{'0.10' if is_dark else '0.09'}"/>
      <stop offset="100%" stop-color="{t['amber']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="{uid}-lamp-cone" x1="564" y1="128" x2="564" y2="188" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['lamp_glow']}" stop-opacity="{'0.42' if is_dark else '0.28'}"/>
      <stop offset="100%" stop-color="{t['lamp_glow']}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="{uid}-eq-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{t['amber_bright']}"/>
      <stop offset="100%" stop-color="{t['amber']}"/>
    </linearGradient>
  </defs>

  <style>
    @keyframes {uid}-pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.45; transform: scale(1.65); }}
    }}
    @keyframes {uid}-blink {{
      0%, 49% {{ opacity: 1; }}
      50%, 100% {{ opacity: 0; }}
    }}
    @keyframes {uid}-eq1 {{ 0%,100%{{transform:scaleY(0.32)}} 50%{{transform:scaleY(1.0)}} }}
    @keyframes {uid}-eq2 {{ 0%,100%{{transform:scaleY(0.85)}} 50%{{transform:scaleY(0.28)}} }}
    @keyframes {uid}-eq3 {{ 0%,100%{{transform:scaleY(0.45)}} 40%{{transform:scaleY(1.0)}} 75%{{transform:scaleY(0.25)}} }}
    @keyframes {uid}-eq4 {{ 0%,100%{{transform:scaleY(0.95)}} 55%{{transform:scaleY(0.35)}} }}
    @keyframes {uid}-eq5 {{ 0%,100%{{transform:scaleY(0.38)}} 45%{{transform:scaleY(0.88)}} }}
    @keyframes {uid}-twinkle {{
      0%, 100% {{ opacity: 0.25; }}
      50% {{ opacity: 1; }}
    }}
    @keyframes {uid}-cloud {{
      0% {{ transform: translateX(-28px); }}
      50% {{ transform: translateX(32px); }}
      100% {{ transform: translateX(-28px); }}
    }}
    {weather_kf}
    @keyframes {uid}-lamp {{
      0%, 100% {{ opacity: 0.78; }}
      50% {{ opacity: 1; }}
    }}
    @keyframes {uid}-scroll {{
      0% {{ transform: translateY(0px); }}
      100% {{ transform: translateY(-60px); }}
    }}
    @keyframes {uid}-steam {{
      0% {{ transform: translateY(4px); opacity: 0; }}
      35% {{ opacity: 0.85; }}
      100% {{ transform: translateY(-16px); opacity: 0; }}
    }}
    @keyframes {uid}-catblink {{
      0%, 92%, 100% {{ transform: scaleY(1); }}
      95%, 97% {{ transform: scaleY(0.12); }}
    }}
    @keyframes {uid}-tail {{
      0%, 100% {{ transform: rotate(-10deg); }}
      50% {{ transform: rotate(14deg); }}
    }}

    .{uid}-dot-ring {{ transform-origin: 48px 42px; animation: {uid}-pulse 2.2s ease-in-out infinite; }}
    .{uid}-cur {{ animation: {uid}-blink 1.05s step-end infinite; }}
    .{uid}-eq1 {{ transform-origin: 37.75px 222px; animation: {uid}-eq1 1.05s ease-in-out infinite; }}
    .{uid}-eq2 {{ transform-origin: 43.75px 222px; animation: {uid}-eq2 0.88s ease-in-out infinite; }}
    .{uid}-eq3 {{ transform-origin: 49.75px 222px; animation: {uid}-eq3 1.22s ease-in-out infinite; }}
    .{uid}-eq4 {{ transform-origin: 55.75px 222px; animation: {uid}-eq4 0.94s ease-in-out infinite; }}
    .{uid}-eq5 {{ transform-origin: 61.75px 222px; animation: {uid}-eq5 1.14s ease-in-out infinite; }}

    .{uid}-s1 {{ animation: {uid}-twinkle 2.8s ease-in-out infinite 0.0s; }}
    .{uid}-s2 {{ animation: {uid}-twinkle 3.4s ease-in-out infinite 0.6s; }}
    .{uid}-s3 {{ animation: {uid}-twinkle 2.5s ease-in-out infinite 1.1s; }}
    .{uid}-s4 {{ animation: {uid}-twinkle 3.8s ease-in-out infinite 0.3s; }}
    .{uid}-s5 {{ animation: {uid}-twinkle 2.9s ease-in-out infinite 1.5s; }}
    .{uid}-s6 {{ animation: {uid}-twinkle 3.2s ease-in-out infinite 0.9s; }}
    .{uid}-cloud {{ animation: {uid}-cloud 16s ease-in-out infinite; }}
    .{uid}-r1 {{ animation: {uid}-rain 2.4s linear infinite 0.0s; }}
    .{uid}-r2 {{ animation: {uid}-rain 2.8s linear infinite 0.5s; }}
    .{uid}-r3 {{ animation: {uid}-rain 2.2s linear infinite 1.1s; }}
    .{uid}-r4 {{ animation: {uid}-rain 2.6s linear infinite 0.3s; }}
    .{uid}-r5 {{ animation: {uid}-rain 2.5s linear infinite 1.4s; }}
    .{uid}-r6 {{ animation: {uid}-rain 2.9s linear infinite 0.8s; }}
    .{uid}-r7 {{ animation: {uid}-rain 2.3s linear infinite 1.7s; }}
    .{uid}-r8 {{ animation: {uid}-rain 2.7s linear infinite 1.2s; }}
    .{uid}-lamp {{ animation: {uid}-lamp 3.6s ease-in-out infinite; }}
    .{uid}-code {{ animation: {uid}-scroll 6.5s linear infinite; }}
    .{uid}-st1 {{ animation: {uid}-steam 2.6s ease-in-out infinite 0.0s; }}
    .{uid}-st2 {{ animation: {uid}-steam 2.6s ease-in-out infinite 0.85s; }}
    .{uid}-st3 {{ animation: {uid}-steam 2.6s ease-in-out infinite 1.7s; }}
    .{uid}-eyes {{ transform-origin: 806px 141px; animation: {uid}-catblink 4.4s ease-in-out infinite; }}
    .{uid}-tail {{ transform-origin: 822px 164px; animation: {uid}-tail 2.4s ease-in-out infinite; }}
  </style>

  <!-- Outer Card Shell -->
  <g clip-path="url(#{uid}-card-clip)">
    <rect x="0.5" y="0.5" width="879" height="255" rx="16" fill="{t['card']}"/>
    <rect x="0.5" y="0.5" width="879" height="255" rx="16" fill="url(#{uid}-ambient)"/>
  </g>
  <rect x="0.5" y="0.5" width="879" height="255" rx="16" stroke="{t['border']}" stroke-width="1"/>

  <!-- ================= LEFT EDITORIAL COLUMN (x=36..495) ================= -->
  <!-- Top status pill -->
  <rect x="36" y="30" width="218" height="24" rx="12" fill="{t['pill_bg']}" stroke="{t['pill_border']}" stroke-width="1"/>
  <circle class="{uid}-dot-ring" cx="48" cy="42" r="4.5" fill="{t['amber']}" opacity="0.35"/>
  <circle cx="48" cy="42" r="3" fill="{t['amber']}"/>
  <text x="60" y="45.8" font-family="{MONO_FONT}" font-size="11" fill="{t['secondary']}">brewing code &amp; ai · vietnam</text>

  <!-- Bold display heading -->
  <text x="36" y="106" font-family="{UI_FONT}">
    <tspan fill="{t['text']}" font-size="38" font-weight="800" letter-spacing="-1.1">CoffatDev</tspan>
    <tspan fill="{t['muted']}" font-size="16" font-weight="400" dx="10">/</tspan>
    <tspan fill="{t['secondary']}" font-size="15" font-weight="500" dx="8">Vu Toan Thang</tspan>
  </text>

  <!-- Natural 2-line bio + blinking amber cursor -->
  <text x="36" y="140" font-family="{UI_FONT}" font-size="14.5" fill="{t['secondary']}">Building full-stack apps, AI workflows, and developer tools.</text>
  <text x="36" y="164" font-family="{UI_FONT}" font-size="14.5" fill="{t['secondary']}">
    <tspan>Fueled by coffee and curiosity.</tspan>
    <tspan class="{uid}-cur" fill="{t['amber']}" font-family="{MONO_FONT}" font-size="17" font-weight="700" dx="4">_</tspan>
  </text>

  <!-- Subtle hairline divider -->
  <line x1="36" y1="194" x2="486" y2="194" stroke="{t['border']}" stroke-width="1"/>

  <!-- Bottom cozy Lo-fi Equalizer Bar -->
  <g>
    <rect class="{uid}-eq1" x="36" y="206" width="3.5" height="16" rx="1.75" fill="url(#{uid}-eq-grad)"/>
    <rect class="{uid}-eq2" x="42" y="206" width="3.5" height="16" rx="1.75" fill="url(#{uid}-eq-grad)"/>
    <rect class="{uid}-eq3" x="48" y="206" width="3.5" height="16" rx="1.75" fill="url(#{uid}-eq-grad)"/>
    <rect class="{uid}-eq4" x="54" y="206" width="3.5" height="16" rx="1.75" fill="url(#{uid}-eq-grad)"/>
    <rect class="{uid}-eq5" x="60" y="206" width="3.5" height="16" rx="1.75" fill="url(#{uid}-eq-grad)"/>
  </g>
  <text x="74" y="218" font-family="{MONO_FONT}" font-size="11" fill="{t['muted']}">now playing · <tspan fill="{t['secondary']}">lo-fi beats &amp; espresso</tspan></text>
  <text x="486" y="218" font-family="{MONO_FONT}" font-size="11" fill="{t['muted']}" text-anchor="end">github.com/Coffat</text>

  <!-- ================= RIGHT PIXEL-ART CODER SCENE (x=520..848, y=22..234) ================= -->
  <g clip-path="url(#{uid}-scene-clip)" shape-rendering="crispEdges">
    <!-- Sky background -->
    <rect x="520" y="22" width="328" height="144" fill="url(#{uid}-sky)"/>

    <!-- Celestial Moon / Sun -->
    {celestial}

    <!-- 6 Twinkling Pixel Stars / Sparkles -->
    {''.join(stars_svg)}

    <!-- Drifting Pixel Cloud -->
    <g class="{uid}-cloud" fill="{t['cloud']}" opacity="{'0.85' if is_dark else '0.92'}">
      <rect x="652" y="56" width="32" height="6"/>
      <rect x="646" y="62" width="46" height="6"/>
      <rect x="660" y="50" width="16" height="6"/>
    </g>

    <!-- Distant Skyline -->
    {skyline}

    <!-- Animated Rain / Sunlit Dust Motes -->
    {''.join(weather_items)}

    <!-- Cozy Window Sill & Mullions -->
    <rect x="520" y="22" width="6" height="142" fill="{t['window_frame']}"/>
    <rect x="842" y="22" width="6" height="142" fill="{t['window_frame']}"/>
    <rect x="520" y="22" width="328" height="6" fill="{t['window_frame']}"/>
    <rect x="520" y="154" width="328" height="8" fill="{t['window_frame']}"/>

    <!-- Warm Wooden Desk -->
    <rect x="520" y="162" width="328" height="10" fill="{t['desk_top']}"/>
    <rect x="520" y="172" width="328" height="44" fill="{t['desk_mid']}"/>
    <rect x="520" y="216" width="328" height="18" fill="{t['desk_front']}"/>
    <!-- Subtle pixel wood grain -->
    <g fill="{t['desk_grain']}" opacity="0.45">
      <rect x="536" y="182" width="44" height="2"/>
      <rect x="614" y="196" width="58" height="2"/>
      <rect x="720" y="186" width="48" height="2"/>
      <rect x="782" y="204" width="42" height="2"/>
    </g>

    <!-- Pixel Desk Lamp + Breathing Glow Cone -->
    <polygon class="{uid}-lamp" points="558,128 584,128 606,182 532,182" fill="url(#{uid}-lamp-cone)" shape-rendering="auto"/>
    <g>
      <!-- Lamp base -->
      <rect x="538" y="168" width="24" height="6" fill="{t['lamp_metal']}"/>
      <rect x="542" y="164" width="16" height="4" fill="{t['lamp_metal']}"/>
      <!-- Lamp arm -->
      <rect x="548" y="142" width="4" height="22" fill="{t['lamp_metal']}"/>
      <rect x="552" y="130" width="4" height="14" fill="{t['lamp_metal']}"/>
      <rect x="556" y="122" width="12" height="4" fill="{t['lamp_metal']}"/>
      <!-- Lamp hood -->
      <rect x="560" y="118" width="18" height="6" fill="{t['lamp_shade']}"/>
      <rect x="556" y="124" width="26" height="6" fill="{t['lamp_shade']}"/>
      <!-- Glowing bulb -->
      <rect x="564" y="130" width="10" height="4" fill="#FEF08A"/>
    </g>

    <!-- Glowing Dual-Tone Pixel Monitor -->
    <g>
      <!-- Monitor outer bezel -->
      <rect x="604" y="84" width="130" height="72" fill="{t['monitor_bezel']}"/>
      <rect x="604" y="84" width="130" height="4" fill="{t['monitor_edge']}"/>
      <rect x="604" y="84" width="4" height="72" fill="{t['monitor_edge']}"/>
      <!-- Monitor stand -->
      <rect x="662" y="156" width="14" height="12" fill="{t['monitor_bezel']}"/>
      <rect x="646" y="166" width="46" height="6" fill="{t['monitor_edge']}"/>
      <!-- Tiny green power LED -->
      <rect x="724" y="150" width="4" height="2" fill="{t['green']}"/>
      <!-- Inner IDE Screen -->
      <rect x="612" y="92" width="114" height="56" fill="{t['screen_bg']}"/>
      <!-- Animated Scrolling Syntax-Highlighted Code -->
      <g clip-path="url(#{uid}-screen-clip)">
        <g class="{uid}-code">
          {code_block(92)}
          {code_block(152)}
        </g>
      </g>
      <!-- Mini Pixel Keyboard -->
      <rect x="622" y="180" width="94" height="14" fill="{t['monitor_bezel']}"/>
      <g fill="{t['monitor_edge']}">
        <rect x="626" y="183" width="8" height="3"/>
        <rect x="636" y="183" width="8" height="3"/>
        <rect x="646" y="183" width="8" height="3"/>
        <rect x="656" y="183" width="8" height="3"/>
        <rect x="666" y="183" width="8" height="3"/>
        <rect x="676" y="183" width="8" height="3"/>
        <rect x="686" y="183" width="8" height="3"/>
        <rect x="696" y="183" width="16" height="3"/>
        <rect x="628" y="188" width="14" height="3"/>
        <rect x="644" y="188" width="40" height="3"/>
        <rect x="686" y="188" width="24" height="3"/>
      </g>
    </g>

    <!-- Steaming Coffat Pixel Coffee Mug -->
    <g>
      <!-- 3 staggered rising pixel steam puffs -->
      <g class="{uid}-st1" fill="{t['steam']}">
        <rect x="752" y="134" width="4" height="6"/>
        <rect x="750" y="128" width="4" height="6"/>
      </g>
      <g class="{uid}-st2" fill="{t['steam']}">
        <rect x="760" y="132" width="4" height="6"/>
        <rect x="762" y="126" width="4" height="6"/>
      </g>
      <g class="{uid}-st3" fill="{t['steam']}">
        <rect x="768" y="135" width="4" height="5"/>
        <rect x="766" y="129" width="4" height="6"/>
      </g>
      <!-- Mug body & handle -->
      <rect x="748" y="148" width="24" height="24" fill="{t['mug_body']}"/>
      <rect x="766" y="148" width="6" height="24" fill="{t['mug_shade']}"/>
      <rect x="748" y="148" width="24" height="4" fill="{t['mug_rim']}"/>
      <rect x="752" y="156" width="12" height="4" fill="{t['mug_rim']}" opacity="0.65"/>
      <!-- Handle -->
      <rect x="772" y="153" width="6" height="4" fill="{t['mug_shade']}"/>
      <rect x="776" y="157" width="4" height="8" fill="{t['mug_shade']}"/>
      <rect x="772" y="165" width="6" height="4" fill="{t['mug_shade']}"/>
    </g>

    <!-- Cute Pixel Cat on Right Desk Corner -->
    <g>
      <!-- Wagging pixel tail -->
      <g class="{uid}-tail">
        <rect x="822" y="162" width="8" height="4" fill="{t['cat_body']}"/>
        <rect x="828" y="154" width="4" height="10" fill="{t['cat_body']}"/>
        <rect x="830" y="148" width="4" height="8" fill="{t['cat_body']}"/>
      </g>
      <!-- Cat body -->
      <rect x="794" y="148" width="28" height="24" fill="{t['cat_body']}"/>
      <rect x="798" y="152" width="6" height="16" fill="{t['cat_highlight']}"/>
      <!-- Cat head -->
      <rect x="794" y="132" width="24" height="18" fill="{t['cat_body']}"/>
      <!-- Pointed ears -->
      <rect x="794" y="126" width="6" height="6" fill="{t['cat_body']}"/>
      <rect x="812" y="126" width="6" height="6" fill="{t['cat_body']}"/>
      <rect x="796" y="128" width="2" height="4" fill="{t['cat_ear']}"/>
      <rect x="814" y="128" width="2" height="4" fill="{t['cat_ear']}"/>
      <!-- Blinking warm eyes -->
      <g class="{uid}-eyes" fill="{t['cat_eye']}">
        <rect x="798" y="139" width="4" height="4"/>
        <rect x="810" y="139" width="4" height="4"/>
      </g>
      <!-- Tiny paws -->
      <rect x="796" y="170" width="6" height="4" fill="{t['cat_highlight']}"/>
      <rect x="810" y="170" width="6" height="4" fill="{t['cat_highlight']}"/>
    </g>
  </g>
  <!-- Crisp frame border around pixel scene -->
  <rect x="520" y="22" width="328" height="212" rx="12" stroke="{t['border']}" stroke-width="1"/>
</svg>
"""


# ---------------------------------------------------------------------------
# SVG 2: GITHUB STATS & TOP LANGUAGES CARDS (880 x 188)
# ---------------------------------------------------------------------------
def build_stats_cards_svg(theme_name: str, data: dict) -> str:
    t = THEMES[theme_name]
    uid = f"sc-{theme_name}"

    total_contrib = data["total_contributions"]
    public_repos = data["public_repos"]
    total_stars = data["total_stars"]
    longest_streak = data["longest_streak"]
    active_days = data["active_days"]
    top_langs = data["top_languages"][:5]

    # Build 5 Top Language rows with animated horizontal bars
    lang_rows: list[str] = []
    lang_styles: list[str] = []
    bar_x = 576
    bar_max_w = 224.0
    row_y0 = 56
    row_step = 25

    for idx, (lang_name, pct, color) in enumerate(top_langs):
        y = row_y0 + idx * row_step
        fill_w = max(8.0, (pct / 100.0) * bar_max_w)
        delay = idx * 0.12
        lang_styles.append(
            f".{uid}-b{idx}{{transform-origin:{bar_x}px {y}px;"
            f"animation:{uid}-grow 1.1s cubic-bezier(0.22,1,0.36,1) {delay:.2f}s both,"
            f"{uid}-breathe 4.2s ease-in-out {1.2 + delay:.2f}s infinite;}}"
        )
        lang_rows.append(
            f"""  <g>
    <circle cx="474" cy="{y}" r="4" fill="{color}"/>
    <text x="486" y="{y + 4}" font-family="{UI_FONT}" font-size="12.5" font-weight="500" fill="{t['text']}">{escape(lang_name)}</text>
    <rect x="{bar_x}" y="{y - 4}" width="{bar_max_w:.0f}" height="8" rx="4" fill="{t['bar_bg']}"/>
    <rect class="{uid}-b{idx}" x="{bar_x}" y="{y - 4}" width="{fill_w:.1f}" height="8" rx="4" fill="{color}"/>
    <text x="856" y="{y + 4}" font-family="{MONO_FONT}" font-size="11.5" fill="{t['secondary']}" text-anchor="end">{pct:.1f}%</text>
  </g>"""
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="880" height="188" viewBox="0 0 880 188" fill="none" role="img" aria-label="GitHub Overview and Top Languages">
  <defs>
    <linearGradient id="{uid}-accent-bar" x1="22" y1="0" x2="410" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['amber']}"/>
      <stop offset="55%" stop-color="{t['amber_bright']}"/>
      <stop offset="100%" stop-color="{t['green']}"/>
    </linearGradient>
  </defs>
  <style>
    @keyframes {uid}-live {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.4; transform: scale(1.6); }}
    }}
    @keyframes {uid}-grow {{
      0% {{ transform: scaleX(0); opacity: 0.4; }}
      100% {{ transform: scaleX(1); opacity: 1; }}
    }}
    @keyframes {uid}-breathe {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.82; }}
    }}
    .{uid}-live {{ transform-origin: 349px 26px; animation: {uid}-live 2.2s ease-in-out infinite; }}
    .{uid}-accent {{ animation: {uid}-breathe 3.5s ease-in-out infinite; }}
    {''.join(lang_styles)}
  </style>

  <!-- ================= LEFT CARD: GITHUB OVERVIEW (0..432) ================= -->
  <rect x="0.5" y="0.5" width="431" height="187" rx="14" fill="{t['card']}" stroke="{t['border']}" stroke-width="1"/>

  <!-- Card Header -->
  <text x="22" y="30" font-family="{UI_FONT}" font-size="13.5" font-weight="700" fill="{t['text']}">GitHub Overview</text>
  <rect x="339" y="16" width="71" height="20" rx="10" fill="{t['pill_bg']}" stroke="{t['pill_border']}" stroke-width="1"/>
  <circle class="{uid}-live" cx="349" cy="26" r="4" fill="{t['green']}" opacity="0.35"/>
  <circle cx="349" cy="26" r="2.6" fill="{t['green']}"/>
  <text x="357" y="29.5" font-family="{MONO_FONT}" font-size="9.5" font-weight="600" fill="{t['secondary']}">LIVE · 1Y</text>

  <!-- 2x2 KPI Tiles -->
  <!-- Tile 1: Contributions -->
  <rect x="22" y="46" width="188" height="58" rx="10" fill="{t['inner']}" stroke="{t['border']}" stroke-width="1"/>
  <g transform="translate(34, 63)" stroke="{t['amber']}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="8" cy="8" r="3"/>
    <line x1="1" y1="8" x2="5" y2="8"/>
    <line x1="11" y1="8" x2="15" y2="8"/>
  </g>
  <text x="58" y="75" font-family="{UI_FONT}" font-size="20" font-weight="700" fill="{t['text']}">{total_contrib:,}</text>
  <text x="58" y="92" font-family="{UI_FONT}" font-size="11" fill="{t['muted']}">Contributions (1Y)</text>

  <!-- Tile 2: Public Repos -->
  <rect x="222" y="46" width="188" height="58" rx="10" fill="{t['inner']}" stroke="{t['border']}" stroke-width="1"/>
  <g transform="translate(234, 63)" stroke="{t['blue']}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 3.5A1.5 1.5 0 0 1 4.5 2H13v12H4.5A1.5 1.5 0 0 1 3 12.5v-9z"/>
    <line x1="3" y1="11.5" x2="13" y2="11.5"/>
  </g>
  <text x="258" y="75" font-family="{UI_FONT}" font-size="20" font-weight="700" fill="{t['text']}">{public_repos}</text>
  <text x="258" y="92" font-family="{UI_FONT}" font-size="11" fill="{t['muted']}">Public Repos</text>

  <!-- Tile 3: Total Stars -->
  <rect x="22" y="114" width="188" height="58" rx="10" fill="{t['inner']}" stroke="{t['border']}" stroke-width="1"/>
  <g transform="translate(34, 131)" stroke="{t['amber_bright']}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <polygon points="8,1.5 10,5.6 14.5,6.2 11.2,9.4 12,14 8,11.8 4,14 4.8,9.4 1.5,6.2 6,5.6"/>
  </g>
  <text x="58" y="143" font-family="{UI_FONT}" font-size="20" font-weight="700" fill="{t['text']}">{total_stars}</text>
  <text x="58" y="160" font-family="{UI_FONT}" font-size="11" fill="{t['muted']}">Total Stars</text>

  <!-- Tile 4: Longest Streak -->
  <rect x="222" y="114" width="188" height="58" rx="10" fill="{t['inner']}" stroke="{t['border']}" stroke-width="1"/>
  <g transform="translate(234, 131)" stroke="{t['coral']}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M8.5 1.5C9.5 4.5 13 6 13 9.5a5 5 0 0 1-10 0c0-2 1.2-3.8 2.5-5 .2 1.5 1 2.2 1.8 2.2.2-1.8.4-3.7 1.2-5.2z"/>
  </g>
  <text x="258" y="143" font-family="{UI_FONT}" font-size="20" font-weight="700" fill="{t['text']}">{longest_streak}d</text>
  <text x="258" y="160" font-family="{UI_FONT}" font-size="11" fill="{t['muted']}">Longest Streak · {active_days}d active</text>

  <!-- Subtle bottom animated accent bar -->
  <rect x="22" y="179" width="388" height="2.5" rx="1.25" fill="{t['bar_bg']}"/>
  <rect class="{uid}-accent" x="22" y="179" width="388" height="2.5" rx="1.25" fill="url(#{uid}-accent-bar)"/>

  <!-- ================= RIGHT CARD: TOP LANGUAGES (448..880) ================= -->
  <rect x="448.5" y="0.5" width="431" height="187" rx="14" fill="{t['card']}" stroke="{t['border']}" stroke-width="1"/>

  <!-- Card Header -->
  <text x="470" y="30" font-family="{UI_FONT}" font-size="13.5" font-weight="700" fill="{t['text']}">Top Languages</text>
  <text x="856" y="30" font-family="{MONO_FONT}" font-size="10.5" fill="{t['muted']}" text-anchor="end">filtered · top 5</text>

  <!-- 5 Language Rows -->
{chr(10).join(lang_rows)}
</svg>
"""


# ---------------------------------------------------------------------------
# SVG 3: 52-WEEK CONTRIBUTION ACTIVITY WAVE (880 x 196)
# ---------------------------------------------------------------------------
def build_smooth_spline(points: list[tuple[float, float]], y_min: float, y_max: float) -> str:
    """Build a smooth, overshoot-clamped cubic Bezier SVG path through `points`."""
    if not points:
        return ""
    if len(points) == 1:
        return f"M {points[0][0]:.2f} {points[0][1]:.2f}"

    d_parts = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    n = len(points)
    for i in range(n - 1):
        p0 = points[max(0, i - 1)]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[min(n - 1, i + 2)]

        cp1x = p1[0] + (p2[0] - p0[0]) / 6.0
        cp1y = max(y_min, min(y_max, p1[1] + (p2[1] - p0[1]) / 6.0))
        cp2x = p2[0] - (p3[0] - p1[0]) / 6.0
        cp2y = max(y_min, min(y_max, p2[1] - (p3[1] - p1[1]) / 6.0))
        d_parts.append(f"C {cp1x:.2f} {cp1y:.2f}, {cp2x:.2f} {cp2y:.2f}, {p2[0]:.2f} {p2[1]:.2f}")
    return " ".join(d_parts)


def build_activity_graph_svg(theme_name: str, data: dict) -> str:
    t = THEMES[theme_name]
    uid = f"ag-{theme_name}"

    weekly = data["weekly_counts"]
    sundays: list[datetime.date] = data["week_sundays"]
    total_contrib = data["total_contributions"]
    peak_week = data["peak_week"]
    peak_idx = data["peak_idx"]
    updated_date = data["updated_date"]

    chart_l = 46.0
    chart_r = 852.0
    chart_t = 58.0
    chart_b = 158.0
    chart_w = chart_r - chart_l
    chart_h = chart_b - chart_t

    y_scale_max = max(peak_week, 4)
    y_mid = max(1, round(y_scale_max / 2))

    points: list[tuple[float, float]] = []
    bars: list[str] = []
    n_weeks = len(weekly)
    step_x = chart_w / max(1, n_weeks - 1)

    for i, val in enumerate(weekly):
        x = chart_l + i * step_x
        ratio = val / y_scale_max
        y = chart_b - ratio * chart_h
        points.append((x, y))
        bar_h = max(0.0, ratio * chart_h)
        if bar_h > 0.5:
            bars.append(
                f'<rect x="{x - 4.5:.1f}" y="{chart_b - bar_h:.1f}" width="9" height="{bar_h:.1f}" rx="2.5" fill="{t["bar_bg"]}" opacity="0.65"/>'
            )

    spline_d = build_smooth_spline(points, chart_t, chart_b)
    area_d = f"{spline_d} L {points[-1][0]:.2f} {chart_b:.2f} L {points[0][0]:.2f} {chart_b:.2f} Z"

    # Month labels along X-axis (show when month changes, keeping clean spacing)
    month_labels: list[str] = []
    last_month = None
    last_label_x = -100.0
    for i, dt in enumerate(sundays):
        if dt.month != last_month:
            x = chart_l + i * step_x
            if x - last_label_x >= 44.0:
                month_labels.append(
                    f'<text x="{x:.1f}" y="178" font-family="{MONO_FONT}" font-size="10" fill="{t["muted"]}">{dt.strftime("%b")}</text>'
                )
                last_label_x = x
            last_month = dt.month

    # Peak point marker + badge placement (keep inside bounds)
    px, py = points[peak_idx]
    badge_w = 88
    badge_x = min(max(px - badge_w / 2.0, chart_l), chart_r - badge_w)
    badge_y = max(36.0, py - 28.0)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="880" height="196" viewBox="0 0 880 196" fill="none" role="img" aria-label="52-Week Contribution Activity: {total_contrib:,} commits">
  <defs>
    <linearGradient id="{uid}-line" x1="{chart_l}" y1="0" x2="{chart_r}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['amber']}"/>
      <stop offset="55%" stop-color="{t['amber_bright']}"/>
      <stop offset="100%" stop-color="{t['green']}"/>
    </linearGradient>
    <linearGradient id="{uid}-area" x1="0" y1="{chart_t}" x2="0" y2="{chart_b}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['amber']}" stop-opacity="0.24"/>
      <stop offset="60%" stop-color="{t['green']}" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="{t['green']}" stop-opacity="0.0"/>
    </linearGradient>
    <radialGradient id="{uid}-comet-halo" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0%" stop-color="{t['amber_bright']}" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="{t['amber']}" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <style>
    @keyframes {uid}-peakPulse {{
      0% {{ transform: scale(0.75); opacity: 0.85; }}
      100% {{ transform: scale(2.6); opacity: 0; }}
    }}
    .{uid}-peak-ring {{
      transform-origin: {px:.2f}px {py:.2f}px;
      animation: {uid}-peakPulse 2.4s cubic-bezier(0.2, 0.8, 0.3, 1) infinite;
    }}
  </style>

  <!-- Outer Card -->
  <rect x="0.5" y="0.5" width="879" height="195" rx="14" fill="{t['card']}" stroke="{t['border']}" stroke-width="1"/>

  <!-- Header -->
  <circle cx="28" cy="26" r="4" fill="{t['amber']}"/>
  <text x="40" y="30.5" font-family="{UI_FONT}" font-size="13.5" font-weight="700" fill="{t['text']}">Contribution Activity · 52 Weeks</text>
  <text x="854" y="30" font-family="{MONO_FONT}" font-size="10.5" fill="{t['muted']}" text-anchor="end">{total_contrib:,} commits · peak {peak_week}/wk · updated {updated_date}</text>

  <!-- Horizontal Dashed Gridlines & Y-Axis Labels -->
  <g stroke="{t['grid_line']}" stroke-width="1" stroke-dasharray="3 4">
    <line x1="{chart_l}" y1="{chart_t}" x2="{chart_r}" y2="{chart_t}"/>
    <line x1="{chart_l}" y1="{(chart_t + chart_b) / 2:.1f}" x2="{chart_r}" y2="{(chart_t + chart_b) / 2:.1f}"/>
  </g>
  <line x1="{chart_l}" y1="{chart_b}" x2="{chart_r}" y2="{chart_b}" stroke="{t['border']}" stroke-width="1"/>

  <text x="38" y="{chart_t + 3.5:.1f}" font-family="{MONO_FONT}" font-size="10" fill="{t['muted']}" text-anchor="end">{y_scale_max}</text>
  <text x="38" y="{(chart_t + chart_b) / 2 + 3.5:.1f}" font-family="{MONO_FONT}" font-size="10" fill="{t['muted']}" text-anchor="end">{y_mid}</text>
  <text x="38" y="{chart_b + 3.5:.1f}" font-family="{MONO_FONT}" font-size="10" fill="{t['muted']}" text-anchor="end">0</text>

  <!-- Subtle Weekly Histogram Bars -->
  <g>
    {''.join(bars)}
  </g>

  <!-- Soft Translucent Area Fill -->
  <path d="{area_d}" fill="url(#{uid}-area)"/>

  <!-- Smooth Amber -> Matcha Spline Curve -->
  <path d="{spline_d}" stroke="url(#{uid}-line)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>

  <!-- Peak Radar Ripple & Badge -->
  <circle class="{uid}-peak-ring" cx="{px:.2f}" cy="{py:.2f}" r="5.5" stroke="{t['amber_bright']}" stroke-width="1.6" fill="none"/>
  <circle cx="{px:.2f}" cy="{py:.2f}" r="4.2" fill="{t['card']}" stroke="{t['amber_bright']}" stroke-width="2.2"/>
  <rect x="{badge_x:.1f}" y="{badge_y:.1f}" width="{badge_w}" height="18" rx="9" fill="{t['pill_bg']}" stroke="{t['amber']}" stroke-width="1"/>
  <text x="{badge_x + badge_w / 2:.1f}" y="{badge_y + 12.2:.1f}" font-family="{MONO_FONT}" font-size="9.5" font-weight="700" fill="{t['amber_bright']}" text-anchor="middle">PEAK {peak_week}/wk</text>

  <!-- Glowing Amber Comet Traveling Along the Spline (SMIL animateMotion) -->
  <g>
    <circle cx="0" cy="0" r="10" fill="url(#{uid}-comet-halo)"/>
    <circle cx="0" cy="0" r="3.4" fill="{t['amber_bright']}" stroke="{t['card']}" stroke-width="1.2"/>
    <animateMotion dur="7s" repeatCount="indefinite" path="{spline_d}"/>
  </g>

  <!-- X-Axis Month Labels -->
  <g>
    {''.join(month_labels)}
  </g>
</svg>
"""


# ---------------------------------------------------------------------------
# SVG 4: FALLBACK PAC-MAN CONTRIBUTION GAME (880 x 168, cozy card)
# ---------------------------------------------------------------------------
def build_pacman_path() -> list[tuple[float, float]]:
    waypoints: list[tuple[float, float]] = [(-1.5, 0.0)]
    for row in range(7):
        if row % 2 == 0:
            waypoints.append((51.0, float(row)))
            if row < 6:
                waypoints.append((51.0, float(row + 1)))
        else:
            waypoints.append((0.0, float(row)))
            if row < 6:
                waypoints.append((0.0, float(row + 1)))
    waypoints.append((52.5, 6.0))
    return waypoints


def path_metrics(waypoints: list[tuple[float, float]]) -> tuple[list[float], float]:
    cum = [0.0]
    total = 0.0
    for i in range(1, len(waypoints)):
        total += abs(waypoints[i][0] - waypoints[i - 1][0]) + abs(waypoints[i][1] - waypoints[i - 1][1])
        cum.append(total)
    return cum, total


def cell_hit_distance(
    col: int, row: int, waypoints: list[tuple[float, float]], cum: list[float]
) -> float | None:
    for i in range(1, len(waypoints)):
        x0, y0 = waypoints[i - 1]
        x1, y1 = waypoints[i]
        if abs(y0 - y1) < 1e-6 and abs(row - y0) < 1e-6:
            if min(x0, x1) - 1e-6 <= col <= max(x0, x1) + 1e-6:
                return cum[i - 1] + abs(col - x0)
        elif abs(x0 - x1) < 1e-6 and abs(col - x0) < 1e-6:
            if min(y0, y1) - 1e-6 <= row <= max(y0, y1) + 1e-6:
                return cum[i - 1] + abs(row - y0)
    return None


def segment_angle(p0: tuple[float, float], p1: tuple[float, float]) -> int:
    dx = p1[0] - p0[0]
    dy = p1[1] - p0[1]
    if abs(dx) >= abs(dy):
        return 0 if dx >= 0 else 180
    return 90 if dy >= 0 else -90


def build_pacman_svg(theme_name: str, data: dict) -> str:
    t = THEMES[theme_name]
    uid = f"pm-{theme_name}"
    grid = data["grid"]
    total_contrib = data["total_contributions"]
    peak_week = data["peak_week"]

    cell = 12.5
    gap = 3.2
    step = cell + gap  # 15.7
    grid_w = 52 * step - gap  # 813.2
    grid_x = (880.0 - grid_w) / 2.0  # 33.4
    grid_y = 42.0

    def to_px(c: float, r: float) -> tuple[float, float]:
        return (grid_x + c * step + cell / 2.0, grid_y + r * step + cell / 2.0)

    waypoints = build_pacman_path()
    cum, total_dist = path_metrics(waypoints)

    ghost_offsets_pct = [2.2, 4.2, 6.2]
    ghost_offsets_dist = [total_dist * (p / 100.0) for p in ghost_offsets_pct]
    max_lag = ghost_offsets_dist[-1]
    timeline_dist = total_dist + max_lag + 4.0

    pm_kf_lines: list[str] = []
    for i in range(len(waypoints) - 1):
        p0, p1 = waypoints[i], waypoints[i + 1]
        ang = segment_angle(p0, p1)
        t0 = (cum[i] / timeline_dist) * 100.0
        t1 = (cum[i + 1] / timeline_dist) * 100.0
        x0, y0 = to_px(p0[0], p0[1])
        x1, y1 = to_px(p1[0], p1[1])
        if i == 0:
            pm_kf_lines.append(f"0%{{transform:translate({x0:.1f}px,{y0:.1f}px) rotate({ang}deg);opacity:1}}")
        else:
            pm_kf_lines.append(f"{t0:.2f}%{{transform:translate({x0:.1f}px,{y0:.1f}px) rotate({ang}deg);opacity:1}}")
        t1_pre = max(t0 + 0.01, t1 - 0.02)
        pm_kf_lines.append(f"{t1_pre:.2f}%{{transform:translate({x1:.1f}px,{y1:.1f}px) rotate({ang}deg);opacity:1}}")

    end_pct = (total_dist / timeline_dist) * 100.0
    ex, ey = to_px(waypoints[-1][0], waypoints[-1][1])
    pm_kf_lines.append(f"{min(99.5, end_pct + 0.05):.2f}%,100%{{transform:translate({ex:.1f}px,{ey:.1f}px) rotate(0deg);opacity:0}}")

    ghost_kf_blocks: list[str] = []
    for g_idx, lag in enumerate(ghost_offsets_dist):
        g_lines: list[str] = []
        sx, sy = to_px(waypoints[0][0], waypoints[0][1])
        start_pct = (lag / timeline_dist) * 100.0
        g_lines.append(f"0%,{max(0.01, start_pct - 0.05):.2f}%{{transform:translate({sx:.1f}px,{sy:.1f}px);opacity:0}}")
        for i, wp in enumerate(waypoints):
            pct = ((cum[i] + lag) / timeline_dist) * 100.0
            px, py = to_px(wp[0], wp[1])
            g_lines.append(f"{min(99.4, pct):.2f}%{{transform:translate({px:.1f}px,{py:.1f}px);opacity:1}}")
        g_end = ((total_dist + lag) / timeline_dist) * 100.0
        g_lines.append(f"{min(99.8, g_end + 0.05):.2f}%,100%{{transform:translate({ex:.1f}px,{ey:.1f}px);opacity:0}}")
        ghost_kf_blocks.append(f"@keyframes {uid}-g{g_idx}{{{''.join(g_lines)}}}")

    base_rects: list[str] = []
    lit_rects: list[str] = []
    eat_kf_blocks: list[str] = []
    lit_idx = 0

    for col in range(52):
        rx = grid_x + col * step
        for row in range(7):
            ry = grid_y + row * step
            base_rects.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{cell}" height="{cell}" rx="2.6"/>')
            lvl, _ = grid[col][row]
            if lvl > 0:
                hit_d = cell_hit_distance(col, row, waypoints, cum)
                if hit_d is not None:
                    hit_pct = (hit_d / timeline_dist) * 100.0
                    p_before = max(0.05, hit_pct - 0.12)
                    p_after = min(97.0, hit_pct + 0.12)
                    cls = f"{uid}-e{lit_idx}"
                    eat_kf_blocks.append(
                        f"@keyframes {cls}{{0%,{p_before:.2f}%{{opacity:1}}{p_after:.2f}%,98.0%{{opacity:0}}100%{{opacity:1}}}}"
                        f".{cls}{{animation:{cls} 24s linear infinite}}"
                    )
                    lit_rects.append(
                        f'<rect class="{cls}" x="{rx:.1f}" y="{ry:.1f}" width="{cell}" height="{cell}" rx="2.6" fill="{t["levels"][lvl]}"/>'
                    )
                    lit_idx += 1

    ghost_body_path = (
        "M -5.8 5.6 L -5.8 -0.6 A 5.8 5.8 0 0 1 5.8 -0.6 L 5.8 5.6 "
        "L 3.9 3.9 L 1.9 5.6 L 0 3.9 L -1.9 5.6 L -3.9 3.9 Z"
    )
    ghost_elements: list[str] = []
    for g_idx, g_color in enumerate(t["ghosts"]):
        ghost_elements.append(
            f"""    <g class="{uid}-g{g_idx}">
      <path d="{ghost_body_path}" fill="{g_color}"/>
      <ellipse cx="-2.1" cy="-1.2" rx="1.65" ry="2.0" fill="#ffffff"/>
      <ellipse cx="2.1" cy="-1.2" rx="1.65" ry="2.0" fill="#ffffff"/>
      <circle cx="-1.5" cy="-1.2" r="0.95" fill="{t['pupil']}"/>
      <circle cx="2.7" cy="-1.2" r="0.95" fill="{t['pupil']}"/>
    </g>"""
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="880" height="168" viewBox="0 0 880 168" fill="none" role="img" aria-label="Pac-Man Contribution Arcade: {total_contrib:,} commits">
  <defs>
    <clipPath id="{uid}-playfield">
      <rect x="{grid_x - 3:.1f}" y="{grid_y - 4:.1f}" width="{grid_w + 6:.1f}" height="116" rx="4"/>
    </clipPath>
  </defs>
  <style>
    @keyframes {uid}-pm{{{''.join(pm_kf_lines)}}}
    @keyframes {uid}-top{{0%,100%{{transform:rotate(0deg)}}50%{{transform:rotate(-38deg)}}}}
    @keyframes {uid}-bot{{0%,100%{{transform:rotate(0deg)}}50%{{transform:rotate(38deg)}}}}
    {''.join(ghost_kf_blocks)}
    {''.join(eat_kf_blocks)}
    .{uid}-pm{{animation:{uid}-pm 24s linear infinite}}
    .{uid}-top{{transform-origin:0px 0px;animation:{uid}-top 0.24s ease-in-out infinite}}
    .{uid}-bot{{transform-origin:0px 0px;animation:{uid}-bot 0.24s ease-in-out infinite}}
    .{uid}-g0{{animation:{uid}-g0 24s linear infinite}}
    .{uid}-g1{{animation:{uid}-g1 24s linear infinite}}
    .{uid}-g2{{animation:{uid}-g2 24s linear infinite}}
  </style>

  <!-- Cozy Card Container -->
  <rect x="0.5" y="0.5" width="879" height="167" rx="14" fill="{t['card']}" stroke="{t['border']}" stroke-width="1"/>

  <!-- Header -->
  <text x="{grid_x:.1f}" y="26" fill="{t['text']}" font-family="{UI_FONT}" font-size="13" font-weight="700">Pac-Man Contribution Arcade</text>
  <text x="{grid_x + grid_w:.1f}" y="26" fill="{t['muted']}" font-family="{MONO_FONT}" font-size="10.5" text-anchor="end">{total_contrib:,} commits · peak {peak_week}/wk</text>

  <!-- Base 52x7 empty grid -->
  <g fill="{t['levels'][0]}">
    {''.join(base_rects)}
  </g>

  <!-- Lit contribution cells (eaten as Pac-Man passes) -->
  <g>
    {''.join(lit_rects)}
  </g>

  <!-- Animated Pac-Man & 3 Ghosts -->
  <g clip-path="url(#{uid}-playfield)">
{chr(10).join(ghost_elements)}
    <g class="{uid}-pm">
      <path class="{uid}-top" d="M 0 0 L 6.4 0 A 6.4 6.4 0 1 0 -6.4 0 Z" fill="{t['pacman']}"/>
      <path class="{uid}-bot" d="M 0 0 L 6.4 0 A 6.4 6.4 0 1 1 -6.4 0 Z" fill="{t['pacman']}"/>
    </g>
  </g>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Cozy Lo-fi Espresso & Warm Amber GitHub Profile SVGs.")
    parser.add_argument(
        "--skip-pacman",
        action="store_true",
        help="Skip generating local fallback Pac-Man SVGs (used in GitHub Actions when abozanona/pacman-contribution-graph runs).",
    )
    args = parser.parse_args()

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    data = fetch_github_data()
    lang_summary = ", ".join(f"{n} {p:.1f}%" for n, p, _ in data["top_languages"])
    print(
        f"[info] Data source: {data['source']} | "
        f"contributions={data['total_contributions']} | peak={data['peak_week']}/wk | "
        f"repos={data['public_repos']} | stars={data['total_stars']} | "
        f"longest_streak={data['longest_streak']}d ({data['active_days']}d active) | "
        f"top_languages=[{lang_summary}]"
    )

    generated: list[str] = []
    for theme in ("dark", "light"):
        hero_svg = build_hero_lofi_svg(theme)
        stats_svg = build_stats_cards_svg(theme, data)
        activity_svg = build_activity_graph_svg(theme, data)

        (ASSETS_DIR / f"hero-lofi-{theme}.svg").write_text(hero_svg, encoding="utf-8")
        (ASSETS_DIR / f"stats-cards-{theme}.svg").write_text(stats_svg, encoding="utf-8")
        (ASSETS_DIR / f"activity-graph-{theme}.svg").write_text(activity_svg, encoding="utf-8")
        generated.extend([f"hero-lofi-{theme}.svg", f"stats-cards-{theme}.svg", f"activity-graph-{theme}.svg"])

        if not args.skip_pacman:
            pacman_svg = build_pacman_svg(theme, data)
            pm_name = "pacman-contribution-graph-dark.svg" if theme == "dark" else "pacman-contribution-graph.svg"
            (ASSETS_DIR / pm_name).write_text(pacman_svg, encoding="utf-8")
            generated.append(pm_name)

    print(f"[info] Generated {len(generated)} SVGs in {ASSETS_DIR}: {', '.join(generated)}")


if __name__ == "__main__":
    main()
