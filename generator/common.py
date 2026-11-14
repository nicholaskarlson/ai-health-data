"""Shared helpers for the Tonmick Health generator.

Rules that keep every output byte-identical across machines (brief B6, DESIGN D4):
  * one PCG64 stream per block, seeded from ROOT_SEED and the block ID;
  * no global NumPy RNG, no Python `random`, no clock, no string hashing;
  * in the data path only + - * /, sqrt, floor, comparisons, sorting, cumsum,
    searchsorted, the det_* functions below, and the Generator methods random,
    integers and permutation; no np.exp or np.log (their last bit depends on
    the CPU), no built-in distributions (they call the C library's exp and
    log); no BLAS or LAPACK (no `@`, np.dot or np.linalg);
  * a sum or mean of floats that feeds the data or CHECKS.md goes through
    det_sum or det_mean (math.fsum, which is correctly rounded), never np.sum;
  * every float column is written with a fixed number of decimals from spec.FILES.

Standard library plus NumPy and pandas only.
"""
import json
import math
import os

import numpy as np
import pandas as pd

from spec import BLOCK_IDS, DUMMY_DRAWS, DUMMY_ENV_VAR, ROOT_SEED, expand_files


# ------------------------------------------------------------------ randomness
def rng(block):
    """The block's own random stream. `block` is a name in spec.BLOCK_IDS."""
    seq = np.random.SeedSequence(ROOT_SEED, spawn_key=(BLOCK_IDS[block],))
    return np.random.Generator(np.random.PCG64(seq))


def draw_dummy_block():
    """Append-only test hook. Draws from the dummy block when the variable is "1".

    Called right after the network block. Because every block has its own
    stream, these draws must not change any output file.
    """
    if os.environ.get(DUMMY_ENV_VAR) == "1":
        return rng("dummy").normal(size=DUMMY_DRAWS)
    return None


# ------------------------------------------------------------------ small maths
def plogis(x):
    """Logistic function, elementwise. For checks only; the data path uses det_plogis."""
    return 1.0 / (1.0 + np.exp(-x))


def logit(p):
    """For checks only; the data path uses det_log."""
    return np.log(p / (1.0 - p))


def normal_cdf(x):
    """Standard normal CDF via math.erf. For checks and cross-checks only:
    math.erf is kept out of the data path (DESIGN D4)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ------------------------------------------------------------------ deterministic maths
# The Milestone 1 platform probe showed that np.exp and np.log differ in the last
# bit between machines: NumPy uses different code on CPUs with and without AVX-512.
# The functions below use only operations that IEEE 754 defines exactly (+ - * /,
# sqrt, floor, frexp, ldexp, comparisons) and uniform draws, so they give the same
# bits everywhere. tests/test_spec.py asserts their output bit for bit.
# The data path uses these; np.exp, np.log and Generator.normal are for checks only.
_LN2_HI = 6.93147180369123816490e-01     # high part of ln 2; k * _LN2_HI is exact for |k| < 2048
_LN2_LO = 1.90821492927058770002e-10     # low part of ln 2
_LN2 = 0.6931471805599453
_INV_LN2 = 1.44269504088896338700e+00
_SQRT_HALF = 0.7071067811865476
_EXP_COEF = [1.0 / math.factorial(n) for n in range(14, -1, -1)]    # 1/14! ... 1/0!
_LOG_COEF = [1.0 / n for n in range(27, 0, -2)]                     # 1/27, 1/25 ... 1/1


def det_exp(x):
    """exp(x), elementwise, identical on every machine. Accurate to a few parts in 1e16.

    Needs x <= 709 (above that the result would overflow). Below -745 it returns 0.
    """
    x = np.asarray(x, dtype=np.float64)
    if np.any(~(x <= 709.0)):
        raise ValueError("det_exp needs x <= 709")
    xc = np.maximum(x, -745.0)
    k = np.floor(xc * _INV_LN2 + 0.5)
    r = (xc - k * _LN2_HI) - k * _LN2_LO         # |r| <= 0.347
    p = np.full_like(r, _EXP_COEF[0])
    for c in _EXP_COEF[1:]:                      # Taylor series by Horner's rule
        p = p * r + c
    return np.where(x < -745.0, 0.0, np.ldexp(p, k.astype(np.int32)))


def det_log(x):
    """Natural log, elementwise, for x > 0, identical on every machine."""
    x = np.asarray(x, dtype=np.float64)
    if np.any(~(x > 0.0)):
        raise ValueError("det_log needs x > 0")
    m, e = np.frexp(x)                           # x = m * 2**e with 0.5 <= m < 1, exact
    low = m < _SQRT_HALF
    m = np.where(low, m * 2.0, m)                # now sqrt(1/2) <= m < sqrt(2)
    e = e.astype(np.float64) - low
    s = (m - 1.0) / (m + 1.0)                    # log(m) = 2 atanh(s), |s| <= 0.172
    z = s * s
    p = np.full_like(z, _LOG_COEF[0])
    for c in _LOG_COEF[1:]:
        p = p * z + c
    return e * _LN2 + 2.0 * s * p


def det_plogis(x):
    """Logistic function built on det_exp; never overflows."""
    x = np.asarray(x, dtype=np.float64)
    ex = det_exp(-np.abs(x))
    return np.where(x >= 0.0, 1.0 / (1.0 + ex), ex / (1.0 + ex))


def det_normal(r, size):
    """`size` standard normal draws from Generator `r`, identical on every machine.

    Marsaglia's polar method on uniform draws: only sqrt, det_log and exact
    arithmetic. It uses a variable but reproducible number of uniforms.
    """
    chunks, need = [], int(size)
    while need > 0:
        m = int(need * 1.4) + 16
        u = r.random((m, 2))
        v1 = 2.0 * u[:, 0] - 1.0
        v2 = 2.0 * u[:, 1] - 1.0
        s = v1 * v1 + v2 * v2
        ok = (s < 1.0) & (s > 0.0)
        s, v1 = s[ok], v1[ok]
        z = (v1 * np.sqrt(-2.0 * det_log(s) / s))[:need]
        chunks.append(z)
        need -= len(z)
    return np.concatenate(chunks) if chunks else np.empty(0)


def det_sum(x):
    """Sum of floats, correctly rounded (math.fsum), so the same on every machine.

    NumPy's own sum adds in an order that its build chooses. It has matched across
    machines so far, but nothing promises that; this does not depend on the order.
    """
    return math.fsum(np.asarray(x, dtype=np.float64).ravel().tolist())


def det_mean(x):
    """Mean of floats built on det_sum."""
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        raise ValueError("det_mean of an empty array")
    return det_sum(x) / x.size


def solve_intercept(f, target, lo=-15.0, hi=15.0):
    """Bisection for an intercept a with mean(f(a)) == target (f increasing in a).

    Up to 200 iterations, as in tonmick-world. The loop stops early once the
    interval can no longer shrink, which gives the same answer as running all
    200. The mean is det_mean, so the answer is the same on every machine.
    Solved values are stored in hidden/calibrated_intercepts.json and listed in
    PROVENANCE.md.
    """
    for _ in range(200):
        mid = (lo + hi) / 2
        if mid == lo or mid == hi:
            break
        if det_mean(f(mid)) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------ deterministic draws
# Added in Milestone 2. Each is built on Generator.random and the det_* maths
# above, and each is asserted bit for bit in tests/test_spec.py.
def det_exponential(r, size):
    """`size` standard exponential draws (mean 1). One uniform each."""
    return -det_log(1.0 - r.random(int(size)))


def det_gamma(r, shape, size):
    """`size` gamma draws with the given shape (a scalar > 0) and scale 1.

    Marsaglia and Tsang's method on det_normal and uniform draws. For a shape
    below 1 it draws at shape + 1 and multiplies by u ** (1 / shape), written
    as det_exp(det_log(u) / shape). The number of uniforms used varies but is
    reproducible.
    """
    shape = float(shape)
    if not shape > 0.0:
        raise ValueError("det_gamma needs shape > 0")
    size = int(size)
    a = shape if shape >= 1.0 else shape + 1.0
    d = a - 1.0 / 3.0
    c = 1.0 / math.sqrt(9.0 * d)
    chunks, need = [], size
    while need > 0:
        m = int(need * 1.1) + 16
        x = det_normal(r, m)
        u = 1.0 - r.random(m)                    # in (0, 1]
        t = 1.0 + c * x
        ok = t > 0.0
        v = np.where(ok, t * t * t, 1.0)
        ok &= det_log(u) < 0.5 * x * x + d - d * v + d * det_log(v)
        g = (d * v[ok])[:need]
        chunks.append(g)
        need -= len(g)
    out = np.concatenate(chunks) if chunks else np.empty(0)
    if shape < 1.0:
        out = out * det_exp(det_log(1.0 - r.random(size)) / shape)
    return out


def poisson_from_uniform(u, lam):
    """Poisson value for each uniform in `u` by inversion, with mean `lam` (an array
    of the same length, 0 <= lam <= 500). Returns int64.

    For one uniform the value never falls when `lam` rises, so two calls with the
    same `u` give a paired draw: the world with an effect and the world without.
    """
    u = np.asarray(u, dtype=np.float64)
    lam = np.asarray(lam, dtype=np.float64)
    if np.any(~((lam >= 0.0) & (lam <= 500.0))):
        raise ValueError("poisson_from_uniform needs 0 <= lam <= 500")
    p = det_exp(-lam)
    cdf = p.copy()
    k = np.zeros(lam.size, dtype=np.int64)
    limit = lam + 40.0 * np.sqrt(lam) + 60.0     # far beyond any reachable value
    active = u > cdf
    while active.any():
        k[active] += 1
        p[active] = p[active] * lam[active] / k[active]
        cdf[active] += p[active]
        active = (u > cdf) & (k < limit)
    return k


def det_poisson(r, lam, size=None):
    """Poisson draws by inversion. One uniform each.

    `lam` is a scalar (give `size`) or an array (one draw per element), with
    0 <= lam <= 500. Returns int64.
    """
    lam = np.asarray(lam, dtype=np.float64)
    if size is not None:
        lam = np.full(int(size), float(lam))
    shape = lam.shape
    lam = lam.ravel()
    if np.any(~((lam >= 0.0) & (lam <= 500.0))):
        raise ValueError("det_poisson needs 0 <= lam <= 500")
    return poisson_from_uniform(r.random(lam.size), lam).reshape(shape)


def categorical_from_uniform(u, probs):
    """Category index for each uniform in `u`.

    `probs` is 1-D (the same weights for every draw) or 2-D (one row of weights
    per draw). Weights need not sum to 1. Cumulative sums run in index order,
    so the result is the same on every machine.
    """
    u = np.asarray(u, dtype=np.float64)
    probs = np.asarray(probs, dtype=np.float64)
    if probs.ndim == 1:
        cum = np.cumsum(probs)
        idx = np.searchsorted(cum, u * cum[-1], side="right")
        return np.minimum(idx, len(probs) - 1).astype(np.int64)
    cum = np.cumsum(probs, axis=1)
    idx = (u[:, None] * cum[:, -1:] >= cum).sum(axis=1)
    return np.minimum(idx, probs.shape[1] - 1).astype(np.int64)


def det_categorical(r, probs, size=None):
    """Category draws. One uniform each. See categorical_from_uniform."""
    probs = np.asarray(probs, dtype=np.float64)
    n = int(size) if probs.ndim == 1 else probs.shape[0]
    return categorical_from_uniform(r.random(n), probs)


def gauss_jordan_solve(a, b):
    """Solve a x = b for a small square system, in pure Python.

    `a` is a list of rows, `b` a list. Gauss-Jordan elimination with partial
    pivoting. Used for the normal equations in iteratively reweighted least
    squares, so that no BLAS or LAPACK routine touches the data path.
    """
    n = len(b)
    m = [[float(a[i][j]) for j in range(n)] + [float(b[i])] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if m[pivot][col] == 0.0:
            raise ValueError("singular system")
        m[col], m[pivot] = m[pivot], m[col]
        d = m[col][col]
        m[col] = [v / d for v in m[col]]
        for r in range(n):
            if r != col:
                factor = m[r][col]
                if factor != 0.0:
                    m[r] = [vr - factor * vc for vr, vc in zip(m[r], m[col])]
    return [m[i][n] for i in range(n)]


# ------------------------------------------------------------------ output
def format_float(value, decimals):
    """Fixed-decimal text for one float. Python's own formatting, which is
    correctly rounded and the same on every platform. Negative zero prints as zero."""
    text = f"{value:.{decimals}f}"
    if text.startswith("-") and float(text) == 0.0:
        text = text[1:]
    return text


def _is_missing(value):
    return value is None or value is pd.NA or (isinstance(value, float) and value != value)


def _format_cell(value, col_type, decimals):
    if _is_missing(value):
        return ""
    if col_type == "float":
        return format_float(float(value), decimals)
    if col_type in ("int", "flag"):
        return str(int(value))
    return str(value)


def write_csv(df, outdir, path):
    """Write one table exactly as spec.FILES declares it.

    Columns must match the declared names and order. Rows are sorted by the
    declared ID columns. Floats get their fixed decimals, missing values are
    empty fields, line endings are LF, encoding is UTF-8 with no BOM.
    """
    meta = expand_files()[path]
    names = [c[0] for c in meta["columns"]]
    if list(df.columns) != names:
        raise ValueError(f"{path}: columns {list(df.columns)} do not match spec {names}")
    df = df.sort_values(meta["sort_by"], kind="mergesort")
    out = {}
    for name, col_type, decimals, _range, _meaning in meta["columns"]:
        out[name] = [_format_cell(v, col_type, decimals) for v in df[name].tolist()]
    full = os.path.join(outdir, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    pd.DataFrame(out, columns=names).to_csv(
        full, index=False, lineterminator="\n", encoding="utf-8")
    return full


def write_json(obj, outdir, path):
    """Write one JSON file: sorted keys, two-space indent, LF, UTF-8, final newline."""
    full = os.path.join(outdir, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n")
    return full
