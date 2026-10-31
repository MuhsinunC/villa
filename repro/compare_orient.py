"""C2 step 3: compare --rotate/--flip renders against numpy transforms of the baseline render.

For each of tif and zarr (level 0) outputs: array_equal against np.rot90 / np.flip of o-base, and if
not equal, the shape and where they differ. Tries both rotation senses and both flip axes, so the
report says which transform (if any) the writer actually applied.

usage: python -I compare_orient.py RUN_DIR
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import tifffile
import zarr

R = Path(sys.argv[1])


def load_tif(name):
    files = sorted(glob.glob(str(R / name / "tif" / "*.tif")))
    return tifffile.imread(files[0]) if files else None


def load_zarr(name):
    p = R / name / "out.zarr"
    if not p.exists():
        return None
    g = zarr.open(str(p), mode="r")
    a = g["0"] if "0" in g else g
    a = np.asarray(a[:])
    return a[0] if a.ndim == 3 else a


CANDIDATES = {
    "rot90": {"rot90 ccw (np.rot90 k=1)": lambda b: np.rot90(b, 1), "rot90 cw (np.rot90 k=-1)": lambda b: np.rot90(b, -1)},
    "rot180": {"np.rot90 k=2": lambda b: np.rot90(b, 2)},
    "flip0": {"np.flip axis 0 (vertical)": lambda b: np.flip(b, 0), "np.flip axis 1": lambda b: np.flip(b, 1)},
    "flip1": {"np.flip axis 1 (horizontal)": lambda b: np.flip(b, 1), "np.flip axis 0": lambda b: np.flip(b, 0)},
}
EXPECTED = {"rot90": None, "rot180": "np.rot90 k=2", "flip0": "np.flip axis 0 (vertical)", "flip1": "np.flip axis 1 (horizontal)"}


def diff_info(a, b):
    if a.shape != b.shape:
        return {"shape_out": list(a.shape), "shape_expected": list(b.shape)}
    d = a != b
    ys, xs = np.nonzero(d)
    return {"n_diff": int(d.sum()), "frac": round(float(d.mean()), 6),
            "rows": [int(ys.min()), int(ys.max())] if len(ys) else None,
            "cols": [int(xs.min()), int(xs.max())] if len(xs) else None}


report = {}
for kind, loader in (("tif", load_tif), ("zarr", load_zarr)):
    base = loader("o-base")
    if base is None:
        report[kind] = "no baseline output"
        continue
    report[kind] = {"base_shape": list(base.shape), "base_dtype": str(base.dtype)}
    for name, cands in CANDIDATES.items():
        out = loader(f"o-{name}")
        if out is None:
            report[kind][name] = "missing output"
            continue
        res = {}
        for label, fn in cands.items():
            exp = np.ascontiguousarray(fn(base))
            eq = out.shape == exp.shape and np.array_equal(out, exp)
            res[label] = True if eq else diff_info(out, exp)
        res["matches"] = [k for k, v in res.items() if v is True]
        res["shape"] = list(out.shape)
        report[kind][name] = res
print(json.dumps(report, indent=1))
