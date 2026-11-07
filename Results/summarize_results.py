"""
Summarize the MPC study results into one HTML report.

Usage (from MPC_Final):
    python summarize_results.py                       # reads .\results, writes results_summary.html
    python summarize_results.py results -o report.html

Needs only Python 3 (no extra packages). The charts load Chart.js from a CDN,
so open the HTML with an internet connection.

It finds the seeds itself (every results/A{0,1,2}/seed_N folder that has a
KPI file), so it works unchanged for 10 seeds, 100 seeds, or a partial run.
"""
import argparse
import csv
import html
import json
import math
import re
import statistics as st
from datetime import datetime
from pathlib import Path

APPROACHES = ["0", "1", "2"]
NAMES = {"0": "A0 one-shot", "1": "A1 closed-loop MPC", "2": "A2 stochastic MPC"}
COLORS = {"0": "#4c78a8", "1": "#f58518", "2": "#54a24b"}

# key, label, unit, KPI names in the files (first that exists is used)
METRICS = [
    ("total", "Total cost", "USD", ["Total_Cost_USD"]),
    ("energy", "Energy cost", "USD", ["Total_Energy_Cost_USD"]),
    ("co2cost", "CO2 cost", "USD", ["Total_CO2_Cost_USD"]),
    ("ncd", "Non-coincident demand charge", "USD", ["NC_demand_charge_USD"]),
    ("opd", "On-peak demand charge", "USD", ["OP_demand_charge_USD"]),
    ("missedcost", "Missed work penalty", "USD", ["Missed_Work_Penalty_USD"]),
    ("labour", "Towing labour", "USD", ["Travel_Labour_USD"]),
    ("shortcost", "Terminal shortfall penalty", "USD", ["Terminal_Shortfall_Penalty_USD"]),
    ("kwh", "Grid energy", "kWh", ["Total_Grid_Energy_kWh"]),
    ("co2kg", "CO2 emissions", "kg", ["Total_CO2_Emissions_kg"]),
    ("ncpeak", "Non-coincident peak", "kW", ["NCD_Peak_kW"]),
    ("oppeak", "On-peak demand peak", "kW", ["OPD_Peak_kW"]),
    ("missedh", "Missed work", "h", ["Missed_Work_hour"]),
    ("transit", "MCS transit time", "h", ["MCS_Transit_hour"]),
    ("shortkwh", "Terminal SOE shortfall", "kWh", ["Terminal_SOE_Shortfall_kWh"]),
    ("infeas", "Infeasible windows", "count", ["Infeasible_windows"]),
    ("solve", "Total solve time", "s", ["Total_solve_time_s", "Solve_time_s"]),
]
KEYS = [m[0] for m in METRICS]
LABEL = {m[0]: m[1] for m in METRICS}
UNIT = {m[0]: m[2] for m in METRICS}
COMPONENTS = ["energy", "co2cost", "ncd", "opd", "missedcost", "labour", "shortcost"]

T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,
        9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080, 22: 2.074,
        23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042}


def tcrit(df):
    if df <= 30:
        return T975[df]
    return 2.0 if df <= 60 else (1.98 if df <= 120 else 1.96)


def to_float(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def read_kpi(path):
    """Read one A*_kpi_summary.csv (columns Metric, Value) into {key: float}."""
    raw = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    for r in rows[1:]:
        if len(r) >= 2:
            raw[r[0].strip()] = to_float(r[1])
    out = {}
    for key, _, _, names in METRICS:
        for n in names:
            if n in raw and raw[n] is not None:
                out[key] = raw[n]
                break
    return out


def load(root):
    data = {a: {} for a in APPROACHES}  # data[a][seed] = {key: value}
    for a in APPROACHES:
        for d in sorted((root / f"A{a}").glob("seed_*")):
            m = re.fullmatch(r"seed_(\d+)", d.name)
            f = d / f"A{a}_kpi_summary.csv"
            if m and f.is_file() and f.stat().st_size > 0:
                try:
                    data[a][int(m.group(1))] = read_kpi(f)
                except Exception as e:  # unreadable file: skip, but say so
                    print(f"  skipped {f}: {e}")
    return data


def stats(vals):
    n = len(vals)
    if n == 0:
        return None
    mean = st.fmean(vals)
    sd = st.stdev(vals) if n > 1 else 0.0
    half = tcrit(n - 1) * sd / math.sqrt(n) if n > 1 else 0.0
    return dict(n=n, mean=mean, sd=sd, lo=min(vals), hi=max(vals), med=st.median(vals), half=half)


def fmt(x, digits=2):
    if x is None:
        return "–"
    if abs(x) >= 1000:
        return f"{x:,.0f}"
    return f"{x:,.{digits}f}"


def series(data, a, key, seeds):
    return [data[a].get(s, {}).get(key) for s in seeds]


def build_tables(data):
    # Per-approach statistics
    rows = []
    for key in KEYS:
        cells = []
        any_data = False
        for a in APPROACHES:
            vals = [v[key] for v in data[a].values() if key in v]
            s = stats(vals)
            if s:
                any_data = True
                cells.append(
                    f"<td class='num'>{fmt(s['mean'])}<div class='sub'>± {fmt(s['sd'])} sd</div></td>"
                    f"<td class='num sub2'>{fmt(s['lo'])} – {fmt(s['hi'])}</td>"
                    f"<td class='num sub2'>±{fmt(s['half'])}</td>")
            else:
                cells.append("<td class='num'>–</td><td class='num'>–</td><td class='num'>–</td>")
        if any_data:
            hl = " class='hl'" if key == "total" else ""
            rows.append(f"<tr{hl}><th>{html.escape(LABEL[key])} <span class='unit'>{UNIT[key]}</span></th>{''.join(cells)}</tr>")
    head = ("<tr><th rowspan='2'>Metric</th>" +
            "".join(f"<th colspan='3' style='border-bottom:3px solid {COLORS[a]}'>{NAMES[a]} <span class='unit'>(n={len(data[a])})</span></th>" for a in APPROACHES) +
            "</tr><tr>" + "<th>mean</th><th>min – max</th><th>95% CI</th>" * 3 + "</tr>")
    stats_table = f"<table>{head}{''.join(rows)}</table>"

    # Paired comparison against A0 on seeds both have
    prow = []
    for a in ["1", "2"]:
        for key in ["total", "energy", "ncd", "opd", "missedcost", "co2kg", "solve"]:
            seeds = sorted(set(data["0"]) & set(data[a]))
            diffs = [data[a][s][key] - data["0"][s][key]
                     for s in seeds if key in data[a][s] and key in data["0"][s]]
            if not diffs:
                continue
            s_ = stats(diffs)
            base = st.fmean([data["0"][s][key] for s in seeds if key in data["0"][s]])
            pct_txt = f"{100 * s_['mean'] / base:+.1f}%" if base else "–"
            lower = sum(1 for d in diffs if d < -1e-9)
            higher = sum(1 for d in diffs if d > 1e-9)
            tie = len(diffs) - lower - higher
            sig = "yes" if s_["n"] > 1 and abs(s_["mean"]) > s_["half"] else "no"
            cls = "good" if s_["mean"] < 0 else ("bad" if s_["mean"] > 0 else "")
            prow.append(
                f"<tr><th>{NAMES[a]} − A0</th><td>{html.escape(LABEL[key])} <span class='unit'>{UNIT[key]}</span></td>"
                f"<td class='num {cls}'>{s_['mean']:+,.2f}</td><td class='num {cls}'>{pct_txt}</td>"
                f"<td class='num sub2'>±{fmt(s_['half'])}</td><td class='num'>{lower} / {tie} / {higher}</td>"
                f"<td class='num'>{sig}</td><td class='num sub2'>{s_['n']}</td></tr>")
    paired = ("<table><tr><th>Comparison</th><th>Metric</th><th>Mean diff</th><th>% of A0</th>"
              "<th>95% CI</th><th>lower / equal / higher</th><th>CI excludes 0</th><th>seeds</th></tr>"
              + "".join(prow) + "</table>") if prow else "<p class='muted'>Not enough overlapping seeds yet.</p>"

    # Flags
    flags = []
    for a in APPROACHES:
        for s in sorted(data[a]):
            v = data[a][s]
            notes = []
            if v.get("infeas", 0) > 0:
                notes.append(f"{v['infeas']:.0f} infeasible windows")
            if v.get("missedh", 0) > 1e-9:
                notes.append(f"{v['missedh']:.2f} h missed work")
            if v.get("shortkwh", 0) > 1e-6:
                notes.append(f"{v['shortkwh']:.2f} kWh terminal SOE shortfall")
            if notes:
                flags.append(f"<tr><td>{NAMES[a]}</td><td class='num'>{s}</td><td>{'; '.join(notes)}</td></tr>")
    flag_tbl = ("<table><tr><th>Approach</th><th>Seed</th><th>Note</th></tr>" + "".join(flags) + "</table>"
                if flags else "<p class='muted'>No infeasible windows, missed work or terminal shortfall in any finished run.</p>")
    return stats_table, paired, flag_tbl


def per_seed_table(data, seeds):
    head = "<tr><th>Seed</th>" + "".join(f"<th>{NAMES[a]}</th>" for a in APPROACHES) + "</tr>"
    rows = []
    for s in seeds:
        cells = "".join(
            f"<td class='num'>{fmt(data[a][s]['total'])}</td>" if s in data[a] and "total" in data[a][s]
            else "<td class='num muted'>–</td>" for a in APPROACHES)
        rows.append(f"<tr><td class='num'>{s}</td>{cells}</tr>")
    return f"<table class='narrow'>{head}{''.join(rows)}</table>"


def chart_data(data):
    seeds = sorted(set().union(*[set(data[a]) for a in APPROACHES]))
    out = {"seeds": seeds, "approaches": [], "metrics": [], "components": [], "diff": [], "running": []}
    for a in APPROACHES:
        out["approaches"].append({"id": a, "name": NAMES[a], "color": COLORS[a]})
    for key, label, unit, _ in METRICS:
        out["metrics"].append({"key": key, "label": label, "unit": unit,
                               "series": {a: series(data, a, key, seeds) for a in APPROACHES}})
    # running mean of total cost, in seed order, for seeds where the approach has a value
    run = {}
    for a in APPROACHES:
        acc, vals = 0.0, []
        for s in seeds:
            v = data[a].get(s, {}).get("total")
            if v is None:
                vals.append(None)
                continue
            acc += v
            k = sum(1 for x in vals if x is not None) + 1
            vals.append(acc / k)
        run[a] = vals
    out["running"] = run
    # paired difference vs A0
    diffs = {}
    for a in ["1", "2"]:
        diffs[a] = []
        for s in seeds:
            v, b = data[a].get(s, {}).get("total"), data["0"].get(s, {}).get("total")
            diffs[a].append(None if v is None or b is None else v - b)
    out["diff"] = diffs
    # component means per approach
    comp = {}
    for a in APPROACHES:
        comp[a] = {}
        for k in COMPONENTS:
            vals = [v[k] for v in data[a].values() if k in v]
            comp[a][k] = st.fmean(vals) if vals else 0.0
    out["components"] = {"keys": COMPONENTS, "labels": [LABEL[k] for k in COMPONENTS], "means": comp}
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MPC study results summary</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1f23;--mut:#6b7280;--line:#e5e7eb;--good:#15803d;--bad:#b91c1c;--hl:#f1f5f9}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--card:#1c1f25;--ink:#e8eaed;--mut:#9aa1ab;--line:#2c3038;--good:#4ade80;--bad:#f87171;--hl:#232832}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:0 0 12px}
.muted,.sub,.sub2,.unit{color:var(--mut)}.sub{font-size:12px}.sub2{font-size:13px}.unit{font-size:12px;font-weight:400}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi b{display:block;font-size:22px}.kpi span{font-size:13px;color:var(--mut)}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:6px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-weight:600}td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.hl{background:var(--hl)}.good{color:var(--good)}.bad{color:var(--bad)}
table.narrow{width:auto;min-width:420px}
.chart{position:relative;height:320px}
select{font:inherit;padding:4px 8px;border-radius:6px;border:1px solid var(--line);background:var(--card);color:var(--ink)}
details summary{cursor:pointer;font-weight:600}
</style></head><body><main>
<h1>MPC study results summary</h1>
<div class="muted">Generated __WHEN__ from <code>__ROOT__</code></div>

<div class="kpis">__KPIS__</div>

<div class="card"><h2>Total cost by seed</h2>
<div class="chart"><canvas id="c_total"></canvas></div></div>

<div class="grid">
<div class="card"><h2>Running average of total cost</h2>
<div class="muted sub">Mean over seeds 1..k. A flat line means more seeds will not change the average much.</div>
<div class="chart"><canvas id="c_run"></canvas></div></div>
<div class="card"><h2>Cost difference from A0, per seed</h2>
<div class="muted sub">Below zero means cheaper than the one-shot plan on the same seed.</div>
<div class="chart"><canvas id="c_diff"></canvas></div></div>
</div>

<div class="grid">
<div class="card"><h2>Average cost breakdown</h2>
<div class="chart"><canvas id="c_comp"></canvas></div></div>
<div class="card"><h2>Explore any metric by seed</h2>
<select id="sel"></select>
<div class="chart"><canvas id="c_any"></canvas></div></div>
</div>

<div class="card"><h2>Summary statistics</h2>
<div class="scroll">__STATS__</div></div>

<div class="card"><h2>Paired comparison against A0</h2>
<div class="muted sub">Same seed, same inputs. "lower / equal / higher" counts seeds where the approach beat, tied, or lost to A0 (lower cost is better for cost metrics).</div>
<div class="scroll">__PAIRED__</div></div>

<div class="card"><h2>Runs worth a look</h2>__FLAGS__</div>

<div class="card"><details><summary>Total cost for every seed</summary>__PERSEED__</details></div>

</main>
<script>
const D = __DATA__;
const ink = getComputedStyle(document.documentElement).getPropertyValue('--ink').trim() || '#222';
const grid = getComputedStyle(document.documentElement).getPropertyValue('--line').trim() || '#ddd';
Chart.defaults.color = getComputedStyle(document.body).color;
Chart.defaults.borderColor = grid;
const many = D.seeds.length > 30;
function lineSet(series, extra){
  return D.approaches.map(a => Object.assign({
    label: a.name, data: series[a.id], borderColor: a.color, backgroundColor: a.color,
    tension: 0, borderWidth: 2, pointRadius: many ? 0 : 3, spanGaps: false}, extra||{}));
}
function opts(ytitle){
  return {responsive:true, maintainAspectRatio:false, interaction:{mode:'index', intersect:false},
    plugins:{legend:{position:'bottom'}},
    scales:{x:{title:{display:true,text:'Seed'}, ticks:{maxTicksLimit: 20}}, y:{title:{display:!!ytitle,text:ytitle||''}}}};
}
const total = D.metrics.find(m => m.key==='total');
new Chart(c_total, {type:'line', data:{labels:D.seeds, datasets:lineSet(total.series)}, options:opts('Total cost (USD)')});
new Chart(c_run, {type:'line', data:{labels:D.seeds, datasets:lineSet(D.running, {pointRadius:0})}, options:opts('Running mean (USD)')});
new Chart(c_diff, {type:'bar', data:{labels:D.seeds, datasets:D.approaches.filter(a=>a.id!=='0').map(a=>({
  label:a.name+' − A0', data:D.diff[a.id], backgroundColor:a.color}))}, options:opts('USD')});
new Chart(c_comp, {type:'bar', data:{labels:D.approaches.map(a=>a.name), datasets:D.components.keys.map((k,i)=>({
  label:D.components.labels[i], data:D.approaches.map(a=>D.components.means[a.id][k]),
  backgroundColor:['#4c78a8','#9ecae9','#f58518','#ffbf79','#e45756','#54a24b','#b279a2'][i%7]}))},
  options:Object.assign(opts('USD (mean over seeds)'), {scales:{x:{stacked:true},y:{stacked:true,title:{display:true,text:'USD (mean over seeds)'}}}})});
const sel = document.getElementById('sel');
D.metrics.forEach(m => sel.add(new Option(m.label + ' (' + m.unit + ')', m.key)));
sel.value = 'ncd';
let anyChart = null;
function drawAny(){
  const m = D.metrics.find(x => x.key===sel.value);
  if (anyChart) anyChart.destroy();
  anyChart = new Chart(c_any, {type:'line', data:{labels:D.seeds, datasets:lineSet(m.series)}, options:opts(m.label + ' (' + m.unit + ')')});
}
sel.onchange = drawAny; drawAny();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="results")
    ap.add_argument("-o", "--out", default="results_summary.html")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit(f"Folder not found: {root.resolve()}")

    data = load(root)
    seeds = sorted(set().union(*[set(data[a]) for a in APPROACHES]))
    if not seeds:
        raise SystemExit("No finished runs (no *_kpi_summary.csv files) found.")

    stats_t, paired_t, flags_t = build_tables(data)
    cd = chart_data(data)

    kpis = []
    for a in APPROACHES:
        vals = [v["total"] for v in data[a].values() if "total" in v]
        s = stats(vals)
        if s:
            ci_txt = "" if s["n"] < 2 else ", 95% CI ±{:,.2f}".format(s["half"])
            body = "<b>${:,.2f}</b><span>{} mean total cost, n={}{}</span>".format(
                s["mean"], NAMES[a], s["n"], ci_txt)
        else:
            body = "<b>–</b><span>{}: no runs yet</span>".format(NAMES[a])
        kpis.append(f"<div class='kpi' style='border-top:4px solid {COLORS[a]}'>{body}</div>")
    done = sum(len(data[a]) for a in APPROACHES)
    kpis.append(f"<div class='kpi'><b>{done} / {3 * max(seeds)}</b><span>finished runs (seeds 1–{max(seeds)})</span></div>")

    page = (TEMPLATE
            .replace("__WHEN__", datetime.now().strftime("%Y-%m-%d %H:%M"))
            .replace("__ROOT__", html.escape(str(root)))
            .replace("__KPIS__", "".join(kpis))
            .replace("__STATS__", stats_t)
            .replace("__PAIRED__", paired_t)
            .replace("__FLAGS__", flags_t)
            .replace("__PERSEED__", per_seed_table(data, seeds))
            .replace("__DATA__", json.dumps(cd)))
    Path(args.out).write_text(page, encoding="utf-8")
    print(f"Wrote {Path(args.out).resolve()}")
    for a in APPROACHES:
        print(f"  {NAMES[a]}: {len(data[a])} seeds")


if __name__ == "__main__":
    main()
