"""Team 17 VC Scout: Model Definition and Initial Results pipeline.

Reads the pre-cleaned ETL output (data/model_ready_valuation.csv) and runs a
tuned model comparison (OLS, Ridge, Lasso, KNN, Random Forest, Gradient
Boosting) predicting ln(Valuation). Run etl.py first to regenerate the input.
"""
import json
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import PartialDependenceDisplay, permutation_importance
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import GridSearchCV, KFold, cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
RNG = 17
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- palette
BG = "none"
CARD = "#111A2E"
INK = "#EAF2FF"
MUTED = "#9AA8C7"
GRID = "#273553"
BLUE = "#5EA1FF"
MINT = "#35E7C3"
AMBER = "#FFBE55"
PURPLE = "#9C7BFF"
CORAL = "#FF6B7A"

plt.rcParams.update({
    "figure.facecolor": "none",
    "axes.facecolor": "none",
    "savefig.facecolor": "none",
    "text.color": INK,
    "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "grid.alpha": 0.55,
    "font.family": "Arial",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.axisbelow": True,
})

# ---------------------------------------------------------------- load (ETL output)
model_df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "model_ready_valuation.csv"))
n_raw = len(model_df)
n_model = n_raw

# ---------------------------------------------------------------- features
NUM = ["ln_funding", "years_to_unicorn", "investor_count"]
CAT = ["industry_group", "continent", "era"]
X = model_df[NUM + CAT]
y = model_df["ln_valuation"]

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=RNG)
cv = KFold(n_splits=5, shuffle=True, random_state=RNG)

pre_lin = ColumnTransformer([
    ("num", StandardScaler(), NUM),
    ("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), CAT)])
pre_tree = ColumnTransformer([
    ("num", "passthrough", NUM),
    ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])

candidates = {
    "Baseline (mean)": (Pipeline([("prep", pre_lin), ("m", DummyRegressor())]), {}),
    "Linear (OLS)": (Pipeline([("prep", pre_lin), ("m", LinearRegression())]), {}),
    "Ridge": (Pipeline([("prep", pre_lin), ("m", Ridge())]),
              {"m__alpha": [0.1, 1, 3, 10, 30, 100]}),
    "Lasso": (Pipeline([("prep", pre_lin), ("m", Lasso(max_iter=20000))]),
              {"m__alpha": [0.0005, 0.001, 0.005, 0.01, 0.05]}),
    "KNN": (Pipeline([("prep", pre_lin), ("m", KNeighborsRegressor())]),
            {"m__n_neighbors": [5, 10, 15, 25, 40], "m__weights": ["uniform", "distance"]}),
    "Random Forest": (Pipeline([("prep", pre_tree),
                                ("m", RandomForestRegressor(random_state=RNG))]),
                      {"m__n_estimators": [300, 600],
                       "m__max_depth": [4, 6, 10, None],
                       "m__min_samples_leaf": [2, 5, 10]}),
    "Gradient Boosting": (Pipeline([("prep", pre_tree),
                                    ("m", GradientBoostingRegressor(random_state=RNG))]),
                          {"m__n_estimators": [200, 400, 800],
                           "m__learning_rate": [0.01, 0.03, 0.1],
                           "m__max_depth": [2, 3, 4],
                           "m__subsample": [0.8, 1.0]}),
}

results = {}
fitted = {}
for name, (pipe, grid) in candidates.items():
    if grid:
        gs = GridSearchCV(pipe, grid, cv=cv, scoring="r2", n_jobs=-1)
        gs.fit(X_tr, y_tr)
        best, params = gs.best_estimator_, gs.best_params_
    else:
        best, params = pipe.fit(X_tr, y_tr), {}
    scores = cross_val_score(best, X_tr, y_tr, cv=cv, scoring="r2", n_jobs=-1)
    pred = best.predict(X_te)
    results[name] = {
        "cv_r2_mean": float(scores.mean()),
        "cv_r2_std": float(scores.std()),
        "test_r2": float(r2_score(y_te, pred)),
        "test_mae_ln": float(mean_absolute_error(y_te, pred)),
        "test_rmse_ln": float(root_mean_squared_error(y_te, pred)),
        "median_ape_pct": float(np.median(
            np.abs(np.exp(pred) - np.exp(y_te)) / np.exp(y_te)) * 100),
        "best_params": {k.replace("m__", ""): v for k, v in params.items()},
    }
    fitted[name] = best
    print(f"{name:20s} cvR2={scores.mean():.3f}±{scores.std():.3f} "
          f"testR2={results[name]['test_r2']:.3f} params={results[name]['best_params']}")

champ_name = max((k for k in results if k != "Baseline (mean)"),
                 key=lambda k: results[k]["cv_r2_mean"])
champ = fitted[champ_name]
print("CHAMPION:", champ_name)

# ---------------------------------------------------------------- diagnostics
pred_te = champ.predict(X_te)

perm = permutation_importance(champ, X_te, y_te, n_repeats=30,
                              random_state=RNG, scoring="r2")
perm_order = np.argsort(perm.importances_mean)
feat_labels = {"ln_funding": "ln(Funding)", "years_to_unicorn": "Years to unicorn",
               "investor_count": "Investor count", "industry_group": "Industry",
               "continent": "Continent", "era": "Era (pre/2021/post)"}

# Bootstrap simulation: CI on champion test R2
rng = np.random.default_rng(RNG)
boot = []
y_te_a, pred_a = y_te.to_numpy(), pred_te
for _ in range(2000):
    idx = rng.integers(0, len(y_te_a), len(y_te_a))
    boot.append(r2_score(y_te_a[idx], pred_a[idx]))
boot_ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))

# Sensitivity: refit champion configuration on data excluding 2021 cohort
sens = {}
mask_tr = X_tr["era"] != "2021"
mask_te = X_te["era"] != "2021"
import copy
champ_no21 = copy.deepcopy(fitted[champ_name])
champ_no21.fit(X_tr[mask_tr], y_tr[mask_tr])
sens["Excluding 2021 cohort"] = float(
    r2_score(y_te[mask_te], champ_no21.predict(X_te[mask_te])))

# Sensitivity: winsorize target outliers at 1st/99th pct in training
lo, hi = y_tr.quantile([0.01, 0.99])
champ_w = copy.deepcopy(fitted[champ_name])
champ_w.fit(X_tr, y_tr.clip(lo, hi))
sens["Winsorized valuations"] = float(r2_score(y_te, champ_w.predict(X_te)))
sens["Full sample"] = results[champ_name]["test_r2"]
print("Sensitivity:", sens, "Bootstrap CI:", boot_ci)

# ---------------------------------------------------------------- charts
def style_ax(ax):
    ax.set_facecolor("none")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

# Chart 1: model comparison
order = ["Baseline (mean)", "KNN", "Lasso", "Linear (OLS)", "Ridge",
         "Random Forest", "Gradient Boosting"]
order = sorted(results, key=lambda k: results[k]["cv_r2_mean"])
fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=200)
names = order
cvm = [results[n]["cv_r2_mean"] for n in names]
cvs = [results[n]["cv_r2_std"] for n in names]
te = [results[n]["test_r2"] for n in names]
ypos = np.arange(len(names))
colors = [AMBER if n == champ_name else (GRID if n == "Baseline (mean)" else BLUE)
          for n in names]
ax.barh(ypos, cvm, xerr=cvs, color=colors, height=0.62,
        error_kw=dict(ecolor=MUTED, lw=1.2, capsize=3))
ax.scatter(te, ypos, color=MINT, zorder=5, s=48)
ax.set_yticks(ypos, names, color=INK, fontsize=11)
ax.set_xlabel("R² on ln(Valuation)   |   blue/amber bars = 5-fold CV mean ± sd,  mint dots = held-out test R²")
ax.set_xlim(-0.02, 0.6)
style_ax(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/chart_model_comparison.png", transparent=True)

# Chart 2: predicted vs actual
fig, ax = plt.subplots(figsize=(5.4, 4.6), dpi=200)
ax.scatter(np.exp(y_te), np.exp(pred_te), s=26, alpha=0.75, color=BLUE,
           edgecolors="none")
lims = [0.8, 200]
ax.plot(lims, lims, color=AMBER, lw=1.6, ls="--", label="Perfect prediction")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel("Actual valuation ($B, log scale)")
ax.set_ylabel("Predicted valuation ($B, log scale)")
ax.legend(frameon=False, labelcolor=INK, loc="upper left")
for tick_set in (ax.get_xticklabels(), ax.get_yticklabels()):
    pass
style_ax(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/chart_pred_vs_actual.png", transparent=True)

# Chart 3: permutation importance
fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=200)
labels = [feat_labels[X.columns[i]] for i in perm_order]
vals = perm.importances_mean[perm_order]
errs = perm.importances_std[perm_order]
cols = [PURPLE if v == max(vals) else BLUE for v in vals]
ax.barh(np.arange(len(vals)), vals, xerr=errs, color=cols, height=0.6,
        error_kw=dict(ecolor=MUTED, lw=1.2, capsize=3))
ax.set_yticks(np.arange(len(vals)), labels, color=INK, fontsize=11)
ax.set_xlabel("Drop in test R² when feature is shuffled (30 repeats)")
style_ax(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/chart_importance.png", transparent=True)

# Chart 4: partial dependence of ln_Funding, shown in $B space
fig, ax = plt.subplots(figsize=(5.6, 4.0), dpi=200)
grid_vals = np.linspace(X_tr["ln_funding"].quantile(0.02),
                        X_tr["ln_funding"].quantile(0.98), 40)
pd_means = []
Xg = X_tr.copy()
for g in grid_vals:
    Xg["ln_funding"] = g
    pd_means.append(champ.predict(Xg).mean())
ax.plot(np.exp(grid_vals), np.exp(pd_means), color=MINT, lw=2.6)
ax.set_xscale("log")
ax.set_xlabel("Total funding ($B, log scale)")
ax.set_ylabel("Model-average valuation ($B)")
style_ax(ax)
fig.tight_layout()
fig.savefig(f"{OUT}/chart_pdp_funding.png", transparent=True)

# Chart 5: sensitivity
fig, ax = plt.subplots(figsize=(5.8, 3.4), dpi=200)
keys = ["Full sample", "Excluding 2021 cohort", "Winsorized valuations"]
vals = [sens[k] for k in keys]
cols = [AMBER, BLUE, PURPLE]
bars = ax.bar(np.arange(3), vals, color=cols, width=0.55)
ax.set_xticks(np.arange(3), keys, color=INK, fontsize=10.5)
ax.set_ylabel("Held-out test R²")
ax.set_ylim(0, 0.8)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}",
            ha="center", color=INK, fontweight="bold", fontsize=11)
style_ax(ax)
ax.grid(axis="x", visible=False)
fig.tight_layout()
fig.savefig(f"{OUT}/chart_sensitivity.png", transparent=True)

# ---------------------------------------------------------------- ols coefficients for slide
ols = fitted["Linear (OLS)"]
enc = ols.named_steps["prep"]
coefs = ols.named_steps["m"].coef_
feat_names = list(enc.get_feature_names_out())
coef_map = dict(zip(feat_names, coefs))
ln_funding_coef = coef_map.get("num__ln_funding", np.nan)
# unstandardize: coef / sd of ln_funding
sd_lnf = X_tr["ln_funding"].std()
elasticity = float(ln_funding_coef / sd_lnf)

stats = {
    "n_raw": n_raw,
    "n_model": n_model,
    "n_train": len(X_tr),
    "n_test": len(X_te),
    "n_industries": int(model_df["industry_group"].nunique()),
    "results": results,
    "champion": champ_name,
    "boot_ci": boot_ci,
    "sensitivity": sens,
    "elasticity_ln_funding": elasticity,
    "perm_importance": {X.columns[i]: float(perm.importances_mean[i])
                        for i in range(len(X.columns))},
}
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_stats.json"), "w") as f:
    json.dump(stats, f, indent=2)
print(json.dumps({k: v for k, v in stats.items() if k != "results"}, indent=2))
