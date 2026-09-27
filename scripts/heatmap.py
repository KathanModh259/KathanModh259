"""Scrape the public contribution calendar and render contrib-heatmap.svg. Stdlib only."""
import re
import sys
import urllib.request
from datetime import date, timedelta

USER = "KathanModh259"
OUT = "contrib-heatmap.svg"
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
CELL, GAP, LEFT, TOP = 12, 3, 34, 30


def fetch(user):
    req = urllib.request.Request(f"https://github.com/users/{user}/contributions",
                                 headers={"User-Agent": "profile-heatmap"})
    return urllib.request.urlopen(req, timeout=30).read().decode()


def parse(html):
    """-> {date: (count, level)}"""
    counts = {}
    for cid, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        m = re.match(r"\s*([\d,]+) contribution", text)
        counts[cid] = int(m.group(1).replace(",", "")) if m else 0
    days = {}
    for td in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", html):
        d, lvl, cid = (re.search(rf'{a}="([^"]+)"', td) for a in ("data-date", "data-level", "id"))
        if d and lvl:
            days[date.fromisoformat(d.group(1))] = (counts.get(cid.group(1), 0) if cid else 0, int(lvl.group(1)))
    if not days:
        sys.exit("no contribution cells found; GitHub markup changed?")
    return days


def streaks(days):
    cur = best = run = 0
    for d in sorted(days):
        run = run + 1 if days[d][0] else 0
        best = max(best, run)
    for d in sorted(days, reverse=True):
        if days[d][0]:
            cur += 1
        elif cur or d != max(days):  # today with 0 doesn't break the streak yet
            break
    return cur, best


def render(days, total=None):
    start = min(days)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # align to Sunday
    weeks = (max(days) - start).days // 7 + 1
    total = total if total is not None else sum(c for c, _ in days.values())
    cur, best = streaks(days)
    top_day, top = max(days.items(), key=lambda kv: kv[1][0])
    w = LEFT + weeks * (CELL + GAP) + 10
    h = TOP + 7 * (CELL + GAP) + 50
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
           'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">',
           '<style>.c{opacity:0;animation:in .35s ease-out forwards}'
           '@keyframes in{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:none}}'
           '.t{fill:#8b949e;font-size:10px}.s{fill:#c9d1d9;font-size:11px}</style>',
           f'<rect width="{w}" height="{h}" rx="8" fill="#0d1117"/>']
    for i, lbl in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text class="t" x="4" y="{TOP + i * (CELL + GAP) + 10}">{lbl}</text>')
    last_month, last_wk = None, -9
    for wk in range(weeks):
        first = start + timedelta(weeks=wk)
        if first.month != last_month:
            if wk - last_wk >= 3 and wk < weeks - 2:  # keep labels from colliding
                out.append(f'<text class="t" x="{LEFT + wk * (CELL + GAP)}" y="{TOP - 8}">{first:%b}</text>')
                last_wk = wk
            last_month = first.month
        for dow in range(7):
            d = first + timedelta(days=dow)
            if d not in days:
                continue
            count, lvl = days[d]
            lvl = 5 if count >= 20 else lvl  # neon top end for big days
            x, y = LEFT + wk * (CELL + GAP), TOP + dow * (CELL + GAP)
            out.append(f'<rect class="c" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                       f'fill="{PALETTE[lvl]}" style="animation-delay:{(wk + dow) * 0.018:.3f}s">'
                       f'<title>{count} on {d}</title></rect>')
    ly = TOP + 7 * (CELL + GAP) + 16
    out.append(f'<text class="s" x="{LEFT}" y="{ly + 9}">{total:,} contributions in the last year</text>')
    lx = w - 10 - 6 * (CELL + GAP) - 64
    out.append(f'<text class="t" x="{lx}" y="{ly + 9}">Less</text>')
    for i, col in enumerate(PALETTE):
        out.append(f'<rect x="{lx + 28 + i * (CELL + GAP)}" y="{ly}" width="{CELL}" height="{CELL}" rx="2.5" fill="{col}"/>')
    out.append(f'<text class="t" x="{lx + 32 + 6 * (CELL + GAP)}" y="{ly + 9}">More</text>')
    out.append(f'<text class="t" x="{LEFT}" y="{ly + 27}">current streak {cur}d · longest {best}d · '
               f'best day {top[0]} ({top_day:%b %d})</text>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    html = fetch(USER)
    days = parse(html)
    assert len(days) > 300, "expected ~a year of days"
    m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)  # GitHub's own headline number
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(days, int(m.group(1).replace(",", "")) if m else None))
    print(f"wrote {OUT}: {len(days)} days")
