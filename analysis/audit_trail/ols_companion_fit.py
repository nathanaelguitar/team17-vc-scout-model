"""Fit the interpretable OLS companion of the audited valuation benchmark.

Regresses ln(valuation, $B) on ln(audited funding, $B) plus industry, continent,
and era one-hot offsets over the 1,057 audited unicorn rows in
assets/vc_scout_unicorn_residuals_final.csv, then writes the coefficients under
the `ols_companion` key of assets/vc_scout_source_of_truth_final.json.

These are the exact coefficients the presentation deck's live explorer
(presentation/vc-scout-deck.html, slide M-11) uses to compute expected
valuations. Pure standard library; deterministic.

    python3 analysis/audit_trail/ols_companion_fit.py
"""
import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RESID = os.path.join(HERE, "assets", "vc_scout_unicorn_residuals_final.csv")
SOT = os.path.join(HERE, "assets", "vc_scout_source_of_truth_final.json")

rows = []
with open(RESID) as f:
    for r in csv.DictReader(f):
        try:
            rows.append({
                "val": float(r["valuation_b_latest"]),
                "fund": float(r["funding_audited_usd"]),
                "ind": r["industry_group"],
                "cont": r["continent"],
                "era": r["era"],
            })
        except (ValueError, KeyError):
            continue

inds = sorted({r["ind"] for r in rows})
conts = sorted({r["cont"] for r in rows})
eras = sorted({r["era"] for r in rows})


def features(r):
    x = [1.0, math.log(max(r["fund"], 1e4) / 1e9)]
    x += [1.0 if r["ind"] == i else 0.0 for i in inds[1:]]
    x += [1.0 if r["cont"] == c else 0.0 for c in conts[1:]]
    x += [1.0 if r["era"] == e else 0.0 for e in eras[1:]]
    return x


X = [features(r) for r in rows]
y = [math.log(r["val"]) for r in rows]
p = len(X[0])
XtX = [[sum(X[k][i] * X[k][j] for k in range(len(X))) for j in range(p)] for i in range(p)]
Xty = [sum(X[k][i] * y[k] for k in range(len(X))) for i in range(p)]
for i in range(p):
    XtX[i][i] += 1e-6  # ridge epsilon for numerical stability


def solve(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r2: abs(M[r2][col]))
        M[col], M[piv] = M[piv], M[col]
        d = M[col][col]
        M[col] = [v / d for v in M[col]]
        for r2 in range(n):
            if r2 != col and M[r2][col] != 0:
                fac = M[r2][col]
                M[r2] = [a - fac * b2 for a, b2 in zip(M[r2], M[col])]
    return [M[i][n] for i in range(n)]


beta = solve(XtX, Xty)
yhat = [sum(b * xi for b, xi in zip(beta, xk)) for xk in X]
ybar = sum(y) / len(y)
r2 = 1 - sum((a - b) ** 2 for a, b in zip(y, yhat)) / sum((a - ybar) ** 2 for a in y)

ols = {
    "note": "Interpretable OLS companion of the audited benchmark: ln(valuation $B) ~ ln(audited funding $B) + industry + continent + era one-hots, fit on the n=%d audited unicorn rows. The multivariable funding slope differs slightly from the univariate log-log elasticity (0.494) because the categorical offsets absorb part of the funding association. Used verbatim by the deck's live explorer (slide M-11)." % len(rows),
    "n": len(rows),
    "r2": round(r2, 3),
    "intercept": round(beta[0], 4),
    "ln_funding": round(beta[1], 4),
    "industries": {inds[0]: 0.0, **{i: round(beta[2 + k], 4) for k, i in enumerate(inds[1:])}},
    "continents": {conts[0]: 0.0, **{c: round(beta[2 + len(inds) - 1 + k], 4) for k, c in enumerate(conts[1:])}},
    "eras": {eras[0]: 0.0, **{e: round(beta[2 + len(inds) - 1 + len(conts) - 1 + k], 4) for k, e in enumerate(eras[1:])}},
}

with open(SOT) as f:
    sot = json.load(f)
sot["ols_companion"] = ols
with open(SOT, "w") as f:
    json.dump(sot, f, indent=2)

print("ols_companion written: n=%d  R2=%.3f  ln_funding=%.4f" % (len(rows), r2, beta[1]))
