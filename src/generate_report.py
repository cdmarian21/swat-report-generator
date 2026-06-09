"""Generate a self-contained static HTML report of SWaT attack behaviour.

Reads a SWaT historian CSV (mock data in CI, the real file swapped in locally),
then for each labelled attack compares its target sensors/actuators inside the
attack window against the normal first-4-hours baseline, and renders a single
self-contained HTML file: inline CSS, no external assets, no JavaScript.

Every text value interpolated into the HTML is escaped with html.escape(), so a
field value can never inject markup into the report.

Run from the repo root:
    python src/generate_report.py --input data/mock_swat.csv --output output/report.html
"""

import argparse
import html
from collections import Counter
from datetime import datetime, time
from pathlib import Path

import pandas as pd

from attacks import ATTACKS, PUMP_OVERRIDE, SENSOR_SPOOFING, VALVE_MANIPULATION
from schema import TIMESTAMP_COL

# First 4 hours (09:00-13:00) are normal operation -> the comparison baseline.
BASELINE_END = time(13, 0, 0)
# |Delta%| at or above this is flagged as a clear deviation in the report.
DEVIATION_THRESHOLD_PCT = 10.0
# Fixed display order for category summaries.
CATEGORY_ORDER = [SENSOR_SPOOFING, VALVE_MANIPULATION, PUMP_OVERRIDE]


def load_data(path):
    df = pd.read_csv(path)
    if TIMESTAMP_COL not in df.columns:
        raise SystemExit(f"Input CSV is missing the '{TIMESTAMP_COL}' column: {path}")
    # Flexible parse so the same code handles the mock and the real file even if
    # their timestamp formatting differs slightly.
    df["_ts"] = pd.to_datetime(df[TIMESTAMP_COL])
    return df


def baseline_frame(df):
    return df[df["_ts"].dt.time < BASELINE_END]


def attack_frame(df, attack):
    run_date = df["_ts"].iloc[0].date()
    start = datetime.combine(run_date, datetime.strptime(attack["start"], "%H:%M:%S").time())
    end = datetime.combine(run_date, datetime.strptime(attack["end"], "%H:%M:%S").time())
    return df[(df["_ts"] >= start) & (df["_ts"] <= end)]


def summarize_target(base_df, window_df, col):
    b_mean = base_df[col].mean()
    w_mean = window_df[col].mean()
    delta_pct = (w_mean - b_mean) / b_mean * 100.0 if b_mean != 0 else float("nan")
    return {
        "column": col,
        "baseline_mean": b_mean,
        "window_mean": w_mean,
        "window_min": window_df[col].min(),
        "window_max": window_df[col].max(),
        "delta_pct": delta_pct,
    }


def build_summaries(df):
    base = baseline_frame(df)
    summaries = []
    for attack in ATTACKS:
        window = attack_frame(df, attack)
        summaries.append({
            "attack": attack,
            "rows_in_window": len(window),
            "targets": [summarize_target(base, window, c) for c in attack["targets"]],
        })
    return summaries


def _fmt(x):
    return "n/a" if pd.isna(x) else f"{x:,.3f}"


def _fmt_pct(x):
    return "n/a" if pd.isna(x) else f"{x:+.1f}%"


def _slug(category):
    return category.lower().replace(" ", "-")


STYLE = """
* { box-sizing: border-box; }
body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       margin: 0; color: #1b1f24; background: #f6f8fa; }
header { background: #0b2545; color: #fff; padding: 28px 32px; }
header h1 { margin: 0 0 4px; font-size: 24px; }
.sub { margin: 0; color: #cdd9e5; }
.meta { color: #8b98a5; font-size: 13px; }
header .meta { color: #9fb3c8; }
code { background: rgba(255,255,255,.12); padding: 1px 5px; border-radius: 4px; }
section { padding: 20px 32px; }
h2 { font-size: 18px; border-bottom: 2px solid #e1e4e8; padding-bottom: 6px; }
h3 { font-size: 15px; margin: 22px 0 2px; }
.cards { display: flex; gap: 14px; flex-wrap: wrap; }
.card { background: #fff; border: 1px solid #e1e4e8; border-radius: 8px; padding: 14px 18px; min-width: 130px; }
.card .num { font-size: 26px; font-weight: 700; }
.card .lbl { font-size: 12px; color: #586069; text-transform: uppercase; letter-spacing: .04em; }
table { border-collapse: collapse; width: 100%; background: #fff; font-size: 13px; margin-top: 6px; }
th, td { border: 1px solid #e1e4e8; padding: 7px 10px; text-align: left; }
th { background: #f1f3f5; }
.tags { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; }
tr.flag { background: #fff5f5; }
tr.flag td:last-child { color: #cf222e; font-weight: 700; }
.cat { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.cat-sensor-spoofing { background: #fde2e1; color: #b42318; }
.cat-valve-manipulation { background: #dbeafe; color: #1d4ed8; }
.cat-pump-override { background: #fef3c7; color: #92590a; }
footer { padding: 18px 32px; color: #8b98a5; font-size: 12px; }
"""


def render_html(summaries, source_name):
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    counts = Counter(s["attack"]["category"] for s in summaries)
    parts = [f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SWaT Attack Report</title>
<style>{STYLE}</style>
</head>
<body>
<header>
  <h1>SWaT Attack Report</h1>
  <p class="sub">Secure Water Treatment (SWaT.A12, Mar 2026) ICS testbed &mdash; attack-window behaviour vs. normal baseline</p>
  <p class="meta">Source data: <code>{html.escape(source_name)}</code> &middot; Generated {generated}</p>
</header>"""]

    # Summary cards
    parts.append('<section class="cards">')
    parts.append(f'<div class="card"><div class="num">{len(summaries)}</div>'
                 f'<div class="lbl">Labelled attacks</div></div>')
    for cat in CATEGORY_ORDER:
        parts.append(f'<div class="card"><div class="num">{counts.get(cat, 0)}</div>'
                     f'<div class="lbl">{html.escape(cat)}</div></div>')
    parts.append('</section>')

    # Timeline
    parts.append('<section><h2>Attack timeline</h2>'
                 '<table><thead><tr><th>#</th><th>Start</th><th>End</th>'
                 '<th>Attack</th><th>Category</th><th>Primary targets</th></tr></thead><tbody>')
    for s in summaries:
        a = s["attack"]
        tags = ", ".join(html.escape(t) for t in a["targets"])
        parts.append(
            f'<tr><td>{a["id"]}</td><td>{html.escape(a["start"])}</td>'
            f'<td>{html.escape(a["end"])}</td><td>{html.escape(a["name"])}</td>'
            f'<td><span class="cat cat-{_slug(a["category"])}">{html.escape(a["category"])}</span></td>'
            f'<td class="tags">{tags}</td></tr>'
        )
    parts.append('</tbody></table></section>')

    # Per-attack detail
    parts.append('<section><h2>Sensor &amp; actuator behaviour during attack windows</h2>')
    for s in summaries:
        a = s["attack"]
        parts.append(f'<h3>#{a["id"]} &mdash; {html.escape(a["name"])}</h3>')
        parts.append(
            f'<p class="meta">{html.escape(a["start"])}&ndash;{html.escape(a["end"])} '
            f'&middot; {html.escape(a["category"])} &middot; {s["rows_in_window"]} rows in window</p>'
        )
        parts.append('<table><thead><tr><th>Target column</th><th>Baseline mean</th>'
                     '<th>Window mean</th><th>Window min</th><th>Window max</th>'
                     '<th>&Delta; vs baseline</th></tr></thead><tbody>')
        for t in s["targets"]:
            flagged = (not pd.isna(t["delta_pct"])) and abs(t["delta_pct"]) >= DEVIATION_THRESHOLD_PCT
            row_cls = ' class="flag"' if flagged else ''
            parts.append(
                f'<tr{row_cls}><td class="tags">{html.escape(t["column"])}</td>'
                f'<td>{_fmt(t["baseline_mean"])}</td><td>{_fmt(t["window_mean"])}</td>'
                f'<td>{_fmt(t["window_min"])}</td><td>{_fmt(t["window_max"])}</td>'
                f'<td>{_fmt_pct(t["delta_pct"])}</td></tr>'
            )
        parts.append('</tbody></table>')
    parts.append('</section>')

    parts.append('<footer><p>Generated by the SWaT Attack Report Generator pipeline. '
                 'Values shown reflect the supplied source dataset.</p></footer>')
    parts.append('</body></html>')
    return "\n".join(parts)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/mock_swat.csv",
                        help="Path to the SWaT CSV (default: data/mock_swat.csv)")
    parser.add_argument("--output", default="output/report.html",
                        help="Path to write the HTML report (default: output/report.html)")
    return parser.parse_args()


def main():
    args = parse_args()
    df = load_data(args.input)
    summaries = build_summaries(df)
    report = render_html(summaries, Path(args.input).name)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"Wrote report ({len(summaries)} attacks) -> {out}")


if __name__ == "__main__":
    main()
