"""Shared functions for the labs, Python side. NumPy and pandas only.

Every function here has a twin of the same name in labs/common.R, and the two
must give the same numbers: labs/compare_results.py checks it.

A lab's own script (lab.py, lab.R) reads data/ only. hidden/ is simulator truth
and is never evidence; only a lab's answer_key.py opens it.
"""
import csv
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(path):
    """A CSV from the repository, every column as text; an empty field stays ''."""
    return pd.read_csv(os.path.join(ROOT, path), dtype=str, keep_default_na=False)


def num(series):
    """Text to numbers; an empty field becomes NaN."""
    return pd.to_numeric(pd.Series(series).replace("", np.nan)).to_numpy(dtype=float)


def c_statistic(score, outcome):
    """The chance that a patient with the outcome has a higher score than one
    without it, counting a tie as one half (Mann-Whitney)."""
    ranks = pd.Series(score).rank(method="average").to_numpy()
    n1 = float(np.sum(outcome == 1))
    n0 = float(np.sum(outcome == 0))
    return (np.sum(ranks[outcome == 1]) - n1 * (n1 + 1.0) / 2.0) / (n1 * n0)


def c_statistic_se(score, outcome):
    """DeLong's standard error for the C-statistic."""
    x1, x0 = score[outcome == 1], score[outcome == 0]
    psi = (x1[:, None] > x0[None, :]) + 0.5 * (x1[:, None] == x0[None, :])
    v10, v01 = psi.mean(axis=1), psi.mean(axis=0)
    return float(np.sqrt(np.var(v10, ddof=1) / len(x1) + np.var(v01, ddof=1) / len(x0)))


def logistic(x, y, offset=None):
    """Maximum-likelihood logistic regression by Newton's method.

    `x` holds the predictors as columns, without the intercept; pass None for an
    intercept-only model. `offset` is added to the linear predictor with its
    coefficient fixed at 1. Returns (coefficients, standard errors), intercept first.
    """
    n = len(y)
    design = np.ones((n, 1)) if x is None else np.column_stack([np.ones(n), x])
    off = np.zeros(n) if offset is None else offset
    beta = np.zeros(design.shape[1])
    for _ in range(100):
        p = 1.0 / (1.0 + np.exp(-(design @ beta + off)))
        information = design.T @ (design * (p * (1.0 - p))[:, None])
        step = np.linalg.solve(information, design.T @ (y - p))
        beta = beta + step
        if np.max(np.abs(step)) < 1e-13:
            break
    p = 1.0 / (1.0 + np.exp(-(design @ beta + off)))
    information = design.T @ (design * (p * (1.0 - p))[:, None])
    return beta, np.sqrt(np.diag(np.linalg.inv(information)))


def logit(p):
    return np.log(p / (1.0 - p))


class Results:
    """Collects a lab's numbers and writes them as `statistic,value`.

    Names say how Python and R are compared: n.* are counts and must be equal;
    fit.* are fitted values and may differ by 1e-6; stat.* must agree to a
    relative 1e-8.
    """

    def __init__(self, chapter):
        self.chapter = chapter
        self.rows = []

    def put(self, name, value):
        text = str(int(value)) if name.startswith("n.") else f"{float(value):.12g}"
        self.rows.append((f"{name.split('.', 1)[0]}.{self.chapter}.{name.split('.', 1)[1]}", text))

    def write(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            writer.writerow(["statistic", "value"])
            writer.writerows(self.rows)
        print(f"{self.chapter} (Python): wrote {len(self.rows)} statistics to {path}")
