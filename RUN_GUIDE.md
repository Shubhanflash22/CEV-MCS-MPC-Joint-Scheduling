# Reviewer guide: running and testing all three approaches

Run everything from the repo root (the folder that contains `Approach 0`, `Approach 1` and `Approach 2`). All paths below are relative to it.

```
Approach 0\   code\  data\input_data\   one-shot (OS)
Approach 1\   code\  data\input_data\   CE-MPC (point estimates)
Approach 2\   code\  data\input_data\   SB-MPC (5 fixed scenarios)
Bayesian Regression\                    soil .xlsx files, the Python regression, generate_live_powers.py, posterior plots
Results\                                saved outputs of the paper runs
Figures\                                pipeline figure
```

The three `input_data` folders must hold the same input files. The only file that exists in Approach 2 alone is `posterior_draws.csv`.

---

## 0. One-time setup

- [ ] Julia 1.12 installed (the `Manifest.toml` was generated with 1.12.6), with the packages: `using Pkg; Pkg.activate("."); Pkg.instantiate()` from the repo root (installs the versions pinned in `Project.toml` and `Manifest.toml`)
- [ ] Gurobi installed with a valid license, and the `GUROBI_HOME` environment variable set to the Gurobi install folder (for example `C:\gurobi1103\win64` on Windows or `/Library/gurobi1103/macos_universal2` on Mac) before running `Pkg.instantiate()`. Academic licenses are free: create the license on gurobi.com and activate it with `grbgetkey` while on the university network or VPN. Check with `using Gurobi; Gurobi.Env()`, which should print the license line without an error.
- [ ] Python environment that already runs the regression script (pymc, pytensor, arviz, xarray, cvxpy, scikit-learn, scipy, numpy, pandas, openpyxl, matplotlib, seaborn). Only needed for Section 3.
- [ ] The 12 soil `.xlsx` task files sit in `Bayesian Regression\` (names listed in `SOIL_FILES` in `Approach 2\code\0_Regression.jl`).

---

## 1. What changed? Find your case

| Case | What changed | Steps to do (sections below) |
|---|---|---|
| A | Nothing, just re-running | Section 4 (one approach) or Section 5 (all modes) |
| B | The day's work (`place.csv`) | Copy the same `place.csv` into all three `input_data` folders. Then Section 4 or 5. No regression rerun. |
| C | Prices, emissions, battery data, travel times, working hours (any input CSV except the power files) | Copy the same file into all three folders. Then Section 4 or 5. |
| D | Soil data, priors, `MIN_DELTA_SOC` (bucket size), battery capacity in the regression | Section 2, then 3, then 4 or 5. |
| E | Only the live data recipe (`generate_live_powers.py` settings) | Section 3, then 4 or 5. |
| F | Number of scenarios (`n_scenarios`) | It is the `n_scenarios` argument of `run_scenario_1` in Approach 2. Section 4. |
| G | Solver time limit | `time_limit_sec` in the call. Section 4. |

After any case that touches input files, do the identical-inputs check in Section 6 before trusting a comparison.

---

## 2. Regression (Julia step 0): run it in Approach 2 only

Approach 2 is the one that needs it, because it writes both `parameters.csv` and `posterior_draws.csv`.

`run_regression` flag:
- `true`: only in this step, in Approach 2, for one call.
- `false`: everywhere else, always. This includes every call in `run_all_modes.jl`. Do not set it to `true` in Approaches 0 or 1, because each refit gives slightly different decimals and the three `parameters.csv` files would drift apart.

Run step 0 alone (no optimisation, takes a few minutes):

```julia
SCENARIO1_NO_AUTORUN = true
include(joinpath("Approach 2", "code", "6_Shrinking_Horizon_main.jl"))
Regression.run_regression(_DEFAULT_REGRESSION_DATA_DIR,
    joinpath("Approach 2", "data", "input_data", "parameters.csv"))
```

Check afterwards:
- [ ] `Approach 2\data\input_data\parameters.csv` has new `p_digging`, `p_loading_swinging`, `p_traveling` and `sigma_*` rows.
- [ ] `Approach 2\data\input_data\posterior_draws.csv` exists, has about 8000 rows (4 chains x 2000), columns `dig,load,travel,idle`.
- [ ] The mean of the `dig` column matches `p_digging` in `parameters.csv` (about 4.79).

Then:
- [ ] Copy `parameters.csv` from Approach 2 into `Approach 0\data\input_data\` and `Approach 1\data\input_data\` (overwrite).
- [ ] Do not copy `posterior_draws.csv` anywhere. Only Approach 2 reads it.

---

## 3. Live data (`live_powers.csv`): needed whenever mode is `:live_data`

`live_powers.csv` must be regenerated whenever Section 2 changed the means, so that its means agree with `parameters.csv`.

1. Open `Bayesian Regression\generate_live_powers.py` and check the CONFIG block:
   - `REGRESSION_SCRIPT` and `REGRESSION_OUTPUT_CSV` are set automatically to the files next to the script in `Bayesian Regression\`. No path needs editing.
   - `RUN_REGRESSION = False` (recommended): reuses `_live_powers_target_mean.csv` as it is. Before running, paste the six values (`p_digging`, `p_loading_swinging`, `p_traveling`, `sigma_digging`, `sigma_loading_swinging`, `sigma_traveling`) from the new Approach 2 `parameters.csv` into `_live_powers_target_mean.csv`, so the live data means equal the planning means exactly.
   - `RUN_REGRESSION = True`: reruns the Python regression and overwrites `_live_powers_target_mean.csv` with its own fit, discarding pasted values. Use it only if you want the live data to follow the Python fit; the means will then differ slightly from `parameters.csv`.
   - `TARGET_DIRS` lists the folders that get a copy of `live_powers.csv`. It is set automatically to `Approach 0\data\input_data`, `Approach 1\data\input_data` and `Approach 2\data\input_data` of this repo. Folders that do not exist are skipped silently.
2. From the repo root, run it with the Python environment from Section 0: `python "Bayesian Regression/generate_live_powers.py"`.
3. Check that the means in `_live_powers_target_mean.csv` equal the values in `parameters.csv`. With the paste workflow they are identical.
4. Check that `live_powers.csv` now exists and has the same modified time in all three `input_data` folders.
5. Known caveat: the live idle mean is about 0.18 kW, while all three planners assume idle = 0.

---

## 4. Running one approach alone

Use this to run or debug one approach.

Approach 2 (the same function name `run_scenario_1` is used in Approach 1):
```julia
SCENARIO1_NO_AUTORUN = true
include(joinpath("Approach 2", "code", "6_Shrinking_Horizon_main.jl"))
res = run_scenario_1(mode = :live_data, time_limit_sec = 600.0, seed = 1,
                     run_regression = false, important_only = true)
```
Approach 1: same call, but include `joinpath("Approach 1", "code", "6_Shrinking_Horizon_main.jl")`.

Approach 0 (it has no `run_regression` argument):
```julia
SCENARIO0_NO_AUTORUN = true
include(joinpath("Approach 0", "code", "6_OneShot_main.jl"))
res = run_scenario_0(mode = :live_data, time_limit_sec = 600.0, seed = 1, detailed_output = true)
```

Modes:
- `:normal`, `:near_mean`, `:high`, `:low`, `:spread_wide`: the plant draws its power from a fitted normal with that shape. They need no `live_powers.csv`.
- `:live_data`: the plant resamples recorded values from `live_powers.csv`. Needs Section 3 done.

Do not run two approaches in the same Julia session. All three code bases define modules with the same names, so use a fresh Julia session per approach.

---

## 5. All sampling modes of one approach

Each approach has a sweep script, `code/run_all_modes.jl`, that runs it once for every mode (`:normal`, `:near_mean`, `:high`, `:low`, `:spread_wide`, `:live_data`) on the input data in its own `data/input_data`. Use a fresh Julia session per approach, then from the repo root:

```julia
include(joinpath("Approach 2", "code", "run_all_modes.jl"))
```

Outputs go to that approach's `output/sweep_output/input_<mode>_sampled/`. Make sure Sections 2 and 3 are done first if the case table says so.

Time: Approach 0 makes one solve per day. Approaches 1 and 2 make about 96 solves each, one per 15-minute interval, and each can use up to the time limit. Expect a long run and leave it alone.

---

## 6. Checks before trusting the numbers

- [ ] The input files are identical across the three approaches (compare the files in the three `data\input_data` folders). `posterior_draws.csv` (Approach 2 only) is left out of this check on purpose.
- [ ] `parameters.csv` is identical in all three folders (this is the most common mistake after a regression rerun).
- [ ] `live_powers.csv` is identical in all three folders.
- [ ] Approach 2: `A2_scenarios.csv` (in the run's output folder, e.g. `Approach 2/output/live_data/`) has 5 rows with weight 0.2 each, `idle_kW` = 0, and `work_energy_kWh` rising from scenario 1 to 5.
- [ ] Approach 2: the scenario table is printed at the top of `A2_run_log.txt` in the same folder.
- [ ] Approaches 1 and 2: `Infeasible_windows` in `*_kpi_summary.csv` is 0. A nonzero value needs investigating.
- [ ] Every approach's `*_kpi_summary.csv` exists in its output folder.
- [ ] Solver: all three use Gurobi with the same settings (8 threads, heuristic effort 0.4, MIPFocus 3, 0.1% relative MIP gap). Approach 2's early windows (from 08:00 to about 11:45) are expected to hit the 600 s limit with a larger gap (about 10% in the 08:00 window in the tuning sweep). Check the gap columns in the solve logs and flag anything much larger.
- [ ] Fixed seed 1 for all three, so reruns on unchanged inputs should repeat. All three solve with 8 threads, so tiny differences between reruns can still appear when solves stop at the gap. Solves that stop at the time limit depend on machine speed and load, so their plans can differ between runs and machines.

---

## 7. Common failures

| Message or symptom | Cause | Fix |
|---|---|---|
| `load_scenarios: .../posterior_draws.csv not found` | Step 0 never ran, or the file is in the wrong folder | Section 2 |
| `posterior_draws.csv and parameters.csv disagree on activity N` | The two files come from different step 0 runs | Rerun Section 2 and copy again, or copy both from the same run |
| Approach 2 run shows FAILED in a sweep | Same two causes above | Same fixes |
| `live_powers.csv` error about missing activities | File missing or lacks rows for dig, load, travel or idle | Section 3 |
| Approach 0 or 1 results move after a regression rerun | `parameters.csv` was not copied to their folders | Section 2, copy step |
| `live_powers.csv` is old in one folder | That folder does not exist (it is skipped silently) | Section 3, step 1 |
| Python step fails | Wrong Python environment, or a soil `.xlsx` file missing from `Bayesian Regression\` | Section 0 and Section 3 |
| Julia complains about a module already defined | Two approaches loaded in one session | Restart Julia and use a fresh session per approach |
| `XLSX.jl not installed; skipping the fit` | Package missing | `Pkg.add("XLSX")` |
| Gurobi license error when a model file loads | No valid license on this machine | Section 0: activate the license with `grbgetkey` on the university network or VPN |

---

## 8. Quick order of operations (fresh start)

1. Section 0 setup.
2. Section 2: run step 0 in Approach 2, copy `parameters.csv` to Approaches 0 and 1.
3. Section 3: generate `live_powers.csv` into all three folders.
4. Section 6: input checks.
5. Section 4 (one approach) or Section 5 (all modes), one fresh Julia session per approach.
6. Go through the Section 6 checklist on the outputs.
