"""
Combined sensitivity summary (high / low / near_mean) in one HTML page.

Put this file next to summarize_results.py and run it from that folder:
    python sensitivity_summary.py "Sensitivity Analysis"
    python sensitivity_summary.py "Sensitivity Analysis" -o "Sensitivity Analysis\\sensitivity_summary.html"

For each mode it reads <root>\\<mode>\\A{0,1,2}\\seed_N\\A{a}_kpi_summary.csv
(the same files summarize_results.py reads) and writes one page with the mean
total cost of each approach and a total-cost-by-seed chart per mode.
Charts load Chart.js from a CDN, so open the HTML with an internet connection.
"""
import argparse
import html
import json
from datetime import datetime
from pathlib import Path

from summarize_results import APPROACHES, COLORS, NAMES, load, stats

MODES = ["high", "low", "near_mean"]

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MPC study results summary</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1f23;--mut:#6b7280;--line:#e5e7eb}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--card:#1c1f25;--ink:#e8eaed;--mut:#9aa1ab;--line:#2c3038}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:20px;margin:40px 0 2px}h3{font-size:17px;margin:0 0 12px}
section{border-top:1px solid var(--line);margin-top:32px}section:first-of-type{border-top:0;margin-top:8px}
.muted{color:var(--mut)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi b{display:block;font-size:22px}.kpi span{font-size:13px;color:var(--mut)}
.chart{position:relative;height:320px}
</style></head><body><main>
<h1>MPC study results summary</h1>
__SECTIONS__
</main>
<script>
const CHARTS = __DATA__;
Chart.defaults.color = getComputedStyle(document.body).color;
Chart.defaults.borderColor = getComputedStyle(document.documentElement).getPropertyValue('--line').trim() || '#ddd';
CHARTS.forEach(c => {
  const many = c.seeds.length > 30;
  new Chart(document.getElementById(c.id), {type:'line',
    data:{labels:c.seeds, datasets:c.series.map(s => ({label:s.name, data:s.data, borderColor:s.color,
      backgroundColor:s.color, tension:0, borderWidth:2, pointRadius: many ? 0 : 3, spanGaps:false}))},
    options:{responsive:true, maintainAspectRatio:false, interaction:{mode:'index', intersect:false},
      plugins:{legend:{position:'bottom'}},
      scales:{x:{title:{display:true,text:'Seed'}, ticks:{maxTicksLimit:20}},
              y:{title:{display:true,text:'Total cost (USD)'}}}}});
});
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="Sensitivity Analysis")
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit(f"Folder not found: {root.resolve()}")
    out = Path(args.out) if args.out else root / "sensitivity_summary.html"
    when = datetime.now().strftime("%Y-%m-%d %H:%M")

    sections, charts = [], []
    for i, mode in enumerate(MODES):
        mdir = root / mode
        if not mdir.is_dir():
            print(f"  skipped {mode}: folder not found")
            continue
        data = load(mdir)
        seeds = sorted(set().union(*[set(data[a]) for a in APPROACHES]))
        if not seeds:
            print(f"  skipped {mode}: no finished runs")
            continue

        kpis = []
        for a in APPROACHES:
            s = stats([v["total"] for v in data[a].values() if "total" in v])
            if s:
                ci = "" if s["n"] < 2 else ", 95% CI ±{:,.2f}".format(s["half"])
                body = "<b>${:,.2f}</b><span>{} mean total cost, n={}{}</span>".format(
                    s["mean"], NAMES[a], s["n"], ci)
            else:
                body = "<b>–</b><span>{}: no runs yet</span>".format(NAMES[a])
            kpis.append(f"<div class='kpi' style='border-top:4px solid {COLORS[a]}'>{body}</div>")
        done = sum(len(data[a]) for a in APPROACHES)
        kpis.append(f"<div class='kpi'><b>{done} / {3 * max(seeds)}</b>"
                    f"<span>finished runs (seeds 1&ndash;{max(seeds)})</span></div>")

        sections.append(
            f"<section><h2>{html.escape(mode)}</h2>"
            f"<div class='muted'>Generated {when} from <code>{html.escape(str(mdir))}</code></div>"
            f"<div class='kpis'>{''.join(kpis)}</div>"
            f"<div class='card'><h3>Total cost by seed</h3>"
            f"<div class='chart'><canvas id='c{i}'></canvas></div></div></section>")
        charts.append({
            "id": f"c{i}", "seeds": seeds,
            "series": [{"name": NAMES[a], "color": COLORS[a],
                        "data": [data[a].get(s, {}).get("total") for s in seeds]}
                       for a in APPROACHES]})
        print(f"  {mode}: " + ", ".join(f"{NAMES[a]} {len(data[a])} seeds" for a in APPROACHES))

    if not sections:
        raise SystemExit("No mode folders with finished runs found.")
    page = (TEMPLATE.replace("__SECTIONS__", "\n".join(sections))
                    .replace("__DATA__", json.dumps(charts)))
    out.write_text(page, encoding="utf-8")
    print(f"Wrote {out.resolve()}")


if __name__ == "__main__":
    main()
