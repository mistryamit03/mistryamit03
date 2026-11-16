"""
Draws contribution-grid.svg from your REAL GitHub contributions.

Runs inside GitHub Actions (.github/workflows/contribution-grid.yml),
which provides GITHUB_TOKEN and GH_USER. Every square is one real day
from the last year; nothing is invented.

Local test without a token:
    python generate_contribution_grid.py --demo sample.json
"""

import json
import os
import sys
import urllib.request
from datetime import date

USER = os.environ.get("GH_USER", "mistryamit03")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contribution-grid.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel weekday } }
      }
    }
  }
}
"""

LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
         "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
FLASH = ["#161b22", "#3dffa0", "#57ffb0", "#8dffcc", "#c8ffe8"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

SQ, GAP = 11, 3
STEP = SQ + GAP
GX, GY = 40, 32
REVEAL, HOLD = 4.5, 3.0
CYCLE = REVEAL + HOLD


def fetch_weeks():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set. Run this inside GitHub Actions, or use --demo.")
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GitHub API error: {data['errors']}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]


def build(weeks):
    n = len(weeks)
    w = GX + n * STEP + 16
    h = GY + 7 * STEP + 18
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t">',
           f'<title id="t">Real GitHub contributions of {USER} over the last year</title>',
           '<defs><filter id="glow" x="-70%" y="-70%" width="240%" height="240%">'
           '<feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/>'
           '<feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
           f'<rect width="{w}" height="{h}" rx="16" fill="#0d1117" stroke="#30363d"/>']

    last_month = None
    for i, wk in enumerate(weeks):
        m = date.fromisoformat(wk["contributionDays"][0]["date"]).month
        if m != last_month and i < n - 2:
            out.append(f'<text x="{GX + i * STEP}" y="22" fill="#8b949e" font-size="10" '
                       f'font-family="system-ui,sans-serif">{MONTHS[m - 1]}</text>')
            last_month = m
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="8" y="{GY + row * STEP + SQ - 1}" fill="#8b949e" font-size="9" '
                   f'font-family="system-ui,sans-serif">{label}</text>')

    max_diag = (n - 1) + 6 * 0.6
    for col, wk in enumerate(weeks):
        for day in wk["contributionDays"]:
            row = day["weekday"]
            lvl = LEVEL.get(day["contributionLevel"], 0)
            x, y = GX + col * STEP, GY + row * STEP
            cell = (f'<rect x="{x}" y="{y}" width="{SQ}" height="{SQ}" rx="2" '
                    f'fill="{COLORS[0]}"')
            if lvl == 0:
                out.append(cell + "/>")
                continue
            t = (col + row * 0.6) / max_diag * REVEAL
            k1 = t / CYCLE
            k2 = min((t + 0.25) / CYCLE, 0.98)
            k3 = min((t + 0.6) / CYCLE, 0.99)
            vals = f"{COLORS[0]};{COLORS[0]};{FLASH[lvl]};{COLORS[lvl]};{COLORS[lvl]}"
            keys = f"0;{k1:.4f};{k2:.4f};{k3:.4f};1"
            filt = ' filter="url(#glow)"' if lvl >= 3 else ""
            out.append(cell + f"{filt}><animate attributeName=\"fill\" values=\"{vals}\" "
                       f'keyTimes="{keys}" dur="{CYCLE}s" repeatCount="indefinite"/></rect>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--demo":
        with open(sys.argv[2]) as f:
            weeks = json.load(f)
    else:
        weeks = fetch_weeks()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(weeks))
    print(f"Wrote {OUT} ({len(weeks)} weeks)")
