"""
Posterior distribution of the soil subactivity powers: summary table, plots, README.

Run from the repo root (the folder that contains "Approach 2" and "Bayesian Regression"):
    python "Bayesian Regression\\posterior_plots.py"

Reads   Bayesian Regression\\posterior\\posterior_draws.csv   (columns dig, load, travel, idle; kW)
Writes  Bayesian Regression\\posterior\\
            posterior_summary.csv
            posterior_all.png            (all four subactivities)
            posterior_<subactivity>.png  (one per subactivity)
            README.md
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

LABELS = {
    "dig": "Digging",
    "load": "Loading + swinging",
    "travel": "Traveling",
    "idle": "Idling",
}
COLORS = {"dig": "#4c78a8", "load": "#f58518", "travel": "#54a24b", "idle": "#9aa1ab"}


def draw(ax, name, x):
    mean, sd = x.mean(), x.std(ddof=1)
    lo, hi = np.percentile(x, [2.5, 97.5])
    if sd == 0:
        ax.axvline(mean, color=COLORS[name], lw=3)
        ax.text(0.5, 0.5, f"fixed at {mean:.2f} kW\n(no spread in the draws)",
                transform=ax.transAxes, ha="center", va="center")
    else:
        ax.hist(x, bins=50, density=True, color=COLORS[name], alpha=0.85)
        ax.axvspan(lo, hi, color="black", alpha=0.08, label="95% interval")
        ax.axvline(mean, color="black", lw=1.5, label=f"mean {mean:.2f} kW")
        ax.legend(frameon=False, fontsize=8)
    ax.set_title(f"{LABELS[name]}  (mean {mean:.2f}, sd {sd:.2f} kW)", fontsize=10)
    ax.set_xlabel("Power (kW)")
    ax.set_ylabel("Posterior density")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", default=str(Path("Bayesian Regression") / "posterior" / "posterior_draws.csv"))
    ap.add_argument("--out", default=str(Path("Bayesian Regression") / "posterior"))
    args = ap.parse_args()

    d = pd.read_csv(args.draws)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    names = [c for c in ["dig", "load", "travel", "idle"] if c in d.columns]

    rows = []
    for n in names:
        x = d[n].to_numpy()
        lo, med, hi = np.percentile(x, [2.5, 50, 97.5])
        rows.append({"subactivity": LABELS[n], "mean_kW": x.mean(), "std_kW": x.std(ddof=1),
                     "p2.5_kW": lo, "median_kW": med, "p97.5_kW": hi, "n_draws": len(x)})
    summ = pd.DataFrame(rows)
    summ.to_csv(out / "posterior_summary.csv", index=False, float_format="%.4f")

    fig, axes = plt.subplots(2, 2, figsize=(9, 6.5))
    for ax, n in zip(axes.ravel(), names):
        draw(ax, n, d[n].to_numpy())
    for ax in axes.ravel()[len(names):]:
        ax.axis("off")
    fig.suptitle("Posterior distribution of subactivity power (soil)")
    fig.tight_layout()
    fig.savefig(out / "posterior_all.png", dpi=200)
    plt.close(fig)

    for n in names:
        fig, ax = plt.subplots(figsize=(4.5, 3.2))
        draw(ax, n, d[n].to_numpy())
        fig.tight_layout()
        fig.savefig(out / f"posterior_{n}.png", dpi=200)
        plt.close(fig)

    table = ["| Subactivity | Mean (kW) | Std (kW) | 2.5% (kW) | Median (kW) | 97.5% (kW) |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        table.append(f"| {r['subactivity']} | {r['mean_kW']:.3f} | {r['std_kW']:.3f} | "
                     f"{r['p2.5_kW']:.3f} | {r['median_kW']:.3f} | {r['p97.5_kW']:.3f} |")
    md = [
        "# Posterior distribution of subactivity power (soil)",
        "",
        f"Posterior of the mean power of each CEV subactivity from the Bayesian linear regression "
        f"({len(d)} draws, PyMC NUTS), the posterior reported in the paper. The draws are in "
        f"`Bayesian Regression/posterior/posterior_draws.csv` (one column per subactivity, in kW).",
        "",
        *table,
        "",
        "![Posterior of all subactivities](posterior_all.png)",
        "",
        "Individual plots: " + ", ".join(f"[{LABELS[n]}](posterior_{n}.png)" for n in names) + ".",
        "",
        "Regenerate with `python \"Bayesian Regression/posterior_plots.py\"` from the repo root.",
        "",
    ]
    (out / "README.md").write_text("\n".join(md), encoding="utf-8")
    print(summ.to_string(index=False))
    print(f"Wrote {out.resolve()}")


if __name__ == "__main__":
    main()
