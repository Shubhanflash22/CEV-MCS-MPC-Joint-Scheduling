# Posterior distribution of subactivity power (soil)

Posterior of the mean power of each CEV subactivity from the Bayesian linear regression (8000 draws, PyMC NUTS), the posterior reported in the paper. The draws are in `Bayesian Regression/posterior/posterior_draws.csv` (one column per subactivity, in kW).

| Subactivity | Mean (kW) | Std (kW) | 2.5% (kW) | Median (kW) | 97.5% (kW) |
|---|---|---|---|---|---|
| Digging | 4.771 | 0.207 | 4.360 | 4.770 | 5.178 |
| Loading + swinging | 3.167 | 0.182 | 2.821 | 3.166 | 3.525 |
| Traveling | 4.647 | 0.389 | 3.871 | 4.647 | 5.406 |
| Idling | 0.068 | 0.052 | 0.003 | 0.058 | 0.195 |

![Posterior of all subactivities](posterior_all.png)

Individual plots: [Digging](posterior_dig.png), [Loading + swinging](posterior_load.png), [Traveling](posterior_travel.png), [Idling](posterior_idle.png).

Regenerate with `python "Bayesian Regression/posterior_plots.py"` from the repo root.
