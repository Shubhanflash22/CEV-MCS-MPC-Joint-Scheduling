# MPC for Mobile Charging Station Dispatch (Construction EVs)

One mobile charging station (MCS) has to keep construction electric vehicles (CEVs) charged and working through the day, without knowing exactly how much power each activity will draw. Every 15 minutes the controller decides where the MCS charges, how much it delivers to which CEV, when it drives between sites, and what each CEV is doing. The goal is to minimize electricity cost, carbon, demand charges, missed work, and towing labour.

This code accompanies the paper **"Probabilistic Power Estimation and MPC-based Scheduling of Construction Electric Vehicles Supported by Mobile Charging Stations"** by Shubhan Mital, Avik Ghosh, Daniela Rojas, Sujit Dey and Yuanyuan Shi, submitted to the 2027 IEEE Power & Energy Society General Meeting (PESGM).

This repo holds three controllers for that same problem, written in Julia (JuMP + Gurobi). They share the same MILP, the same input data, and the same stochastic simulated plant. Only the way the plan is built and used changes.
<!-- ![Overview of the proposed methodology](Figures/mcs-pipeline.jpg) -->
[Overview of the proposed methodology (PDF)](https://github.com/Shubhanflash22/CEV-MCS-MPC-Joint-Scheduling/blob/main/Figures/mcs-pipeline-v3.pdf)

## Posterior distribution of the subactivity powers

Bayesian linear regression on the field data gives the posterior of the mean power of each CEV subactivity (soil work). CE-MPC plans with the posterior mean and SB-MPC builds its scenarios from the draws.

![Posterior distributions of subactivity power](Bayesian%20Regression/posterior/posterior_all.png)

| Subactivity | Mean (kW) | Std (kW) |
|---|---|---|
| Digging | 4.77 | 0.21 |
| Loading + swinging | 3.17 | 0.18 |
| Traveling | 4.65 | 0.39 |
| Idling | 0.07 | 0.05 |

Individual plots, the full summary table (with 95% intervals) and the raw draws are in [`Bayesian Regression/posterior/`](Bayesian%20Regression/posterior/README.md).

## The three approaches

| | Approach 0 | Approach 1 | Approach 2 |
|---|---|---|---|
| Name | One-shot baseline | Certainty Equivalent MPC | Scenario-based stochastic MPC |
| Planning | Solves the whole day once | Re-solves every 15 min from the real state | Re-solves every 15 min from the real state |
| Power assumption | Mean power | Mean power (certainty-equivalent) | Several sampled power scenarios at once |
| Reacts to surprises | No, runs open-loop | Yes, after the fact | Yes, and hedges before they happen |
| Solves per day | 1 | 96 | 96 (each one larger) |
| Entry function | `run_scenario_0` | `run_scenario_1` | `run_scenario_1` |
| Driver | `6_OneShot_main.jl` | `6_Shrinking_Horizon_main.jl` | `6_Shrinking_Horizon_main.jl` |
| Output prefix | `A0_` | `A1_` | `A2_` |

- **A0** commits to a full-day plan and hopes reality matches it. It is the floor the other two are measured against.
- **A1** plans against the average power and fixes mistakes once it re-measures.
- **A2** plans against a handful of possible power draws and only commits to a next move that is feasible in all of them.

## Layout

```
Approach 0/          code/  data/input_data/  README.md
Approach 1/          code/  data/input_data/  README.md
Approach 2/          code/  data/input_data/  README.md
Bayesian Regression/ field task files, regression scripts (step 0), posterior plots
Results/             saved outputs of the paper runs
Figures/             pipeline figure
RUN_GUIDE.md         step-by-step guide for running and checking all three approaches
Project.toml, Manifest.toml
```

Each approach is self-contained: `code/`, `data/input_data/` (the same 8 CSVs in all three) and `output/` sit side by side.

## How to run

1. Install Julia from julialang.org/downloads, and Gurobi with a valid license (free for academics from gurobi.com; activate it with `grbgetkey` while on the university network or VPN).
2. From the repo root, install the pinned packages once:
   ```julia
   using Pkg; Pkg.activate("."); Pkg.instantiate()
   ```
3. Run an approach with its defaults (about the same steps for all three):
   ```julia
   include("Approach 1/code/6_Shrinking_Horizon_main.jl")   # or Approach 0 / 2 and their driver
   ```
   Results are written to that approach's `output/normal/`.
4. To run one approach on all six sampling modes, include its `code/run_all_modes.jl`.

By default every run reads the committed `parameters.csv`. Approaches 1 and 2 can refit it first from `Bayesian Regression/` with `run_regression = true` (needs XLSX.jl). That fit currently overwrites `parameters.csv`, so use it deliberately.

Each approach's README has the input and output file formats, every run option, and implementation notes. `RUN_GUIDE.md` covers the full workflow (regression, live data, checks).

## Comparing the approaches

- Use the same `seed` and `plant` setting across approaches, or the realized power draws will differ.
- `plant = :mean` is a sanity check, not a result. A0 and A1 should give a terminal shortfall of exactly 0. A2 should give 0 or very close to it, with no infeasible windows.
- All three run Gurobi with the same settings (8 threads), so solve times are comparable.
- A2 uses `n_scenarios = 5` by default. Results for other scenario counts are not directly comparable.
- All three add a terminal shortfall penalty to total cost, so compare approaches on the reported total cost.

## Citation

If you use this code, please cite:

> S. Mital, A. Ghosh, D. Rojas, S. Dey, and Y. Shi, "Probabilistic Power Estimation and MPC-based Scheduling of Construction Electric Vehicles Supported by Mobile Charging Stations," submitted to the 2027 IEEE Power & Energy Society General Meeting (PESGM).
