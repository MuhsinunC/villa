#!/usr/bin/env bash
# Repro: vc_render_tifxyz --rotate / --flip output compared with numpy transforms of the plain render.
# usage: reproduce.sh BIN_DIR WORK_DIR [PYTHON]
#   BIN_DIR  directory holding vc_render_tifxyz (villa main, or a build of this PR)
#   WORK_DIR empty scratch directory on disk (needs about 0.5 GB; the volume is streamed into a cache there).
#            Use a separate WORK_DIR per build: each run clears WORK_DIR/crop and WORK_DIR/full.
#   PYTHON   a python with numpy, tifffile and zarr (default: python3)
# Data (CC BY-NC, open): PHerc1447 volume 20250521151220 8.64 um, streamed; the published
# auto_grown mesh 20250703034159 on that volume (4 files, downloaded once).
# Crop 700x500 (not a multiple of 128 or 16) with both --tif-output and --zarr-output, then the
# uncropped segment with --tif-output only (the VC3D "Render Parameters" default output).
# Expected on main: no "matches" for rot90, rot180 and flip0 in the TIFF, none at all in the zarr;
#   the uncropped rot90 TIFF is all zero.
# Expected with the fix: every variant matches its numpy transform in both writers. The one
#   exception is the uncropped TIFF-only rot90, which prints "NONE (closest: rot90 ccw ..., 233 px
#   differ)": off by 1 at those pixels (see README).
# This script was run 2026-10-20 on macOS arm64 against main 8aa507c. The 2026-10-31 results in ../results came from the same
# render commands run directly in villa's CI image against main d57c28ebe (commands in ../results and ../logs).
set -u
BIN=${1:?BIN_DIR}; W=${2:?WORK_DIR}; PY=${3:-python3}
HERE=$(cd "$(dirname "$0")" && pwd)
VOL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1447/volumes/20250521151220-8.640um-1.2m-116keV-masked.zarr
MESH_URL=https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc1447/segments/20250703034159-auto_grown_20250703034159599/mesh/20250703034159-on-20250521151220-8.64um.tifxyz
SEG=$W/mesh/20250703034159.tifxyz
mkdir -p "$SEG" "$W/cache" "$W/config"
for f in meta.json x.tif y.tif z.tif; do
  [ -s "$SEG/$f" ] || curl -fsSL -o "$SEG/$f" "$MESH_URL/$f" || { echo "download failed: $f"; exit 2; }
done
# isolated VC3D config so the remote cache lands in WORK_DIR
printf '[viewer]\nremote_cache_dir=%s\n' "$W/cache" > "$W/config/VC3D.ini"
export VC3D_CONFIG_DIR=$W/config
render() { "$BIN/vc_render_tifxyz" -v "$VOL" -g 2 -s "$SEG" --cache-gb 2 --scale 1 -n 1 "$@"; }
variants() {  # name and extra args, one per line
  printf '%s\n' "base|" "rot90|--rotate 90" "rot180|--rotate 180" "flip0|--flip 0" "flip1|--flip 1"
}

echo "== crop 700x500 at 300,200, TIFF + zarr"
D=$W/crop; rm -rf "$D"; mkdir -p "$D"
variants | while IFS='|' read -r name extra; do
  # shellcheck disable=SC2086
  render --crop-x 300 --crop-y 200 --crop-width 700 --crop-height 500 $extra \
    --tif-output "$D/o-$name/tif" --zarr-output "$D/o-$name/out.zarr" > "$D/o-$name.log" 2>&1
  echo "$name exit $?"
done
"$PY" -I "$HERE/compare_orient.py" "$D" > "$D/orient-compare.json"

echo "== uncropped segment, TIFF only"
D=$W/full; rm -rf "$D"; mkdir -p "$D"
variants | while IFS='|' read -r name extra; do
  # shellcheck disable=SC2086
  render $extra --tif-output "$D/o-$name/tif" > "$D/o-$name.log" 2>&1
  echo "$name exit $?"
done
"$PY" -I "$HERE/compare_orient.py" "$D" > "$D/orient-compare.json"

echo "== summary (writer, variant: numpy transforms the output equals)"
for D in "$W/crop" "$W/full"; do
  echo "-- $(basename "$D")"
  "$PY" -I -c '
import json, sys
r = json.load(open(sys.argv[1]))
for kind, res in r.items():
    if not isinstance(res, dict):
        continue
    for name in ("rot90", "rot180", "flip0", "flip1"):
        v = res.get(name)
        if isinstance(v, dict):
            m = v["matches"]
            if not m:
                near = min((k for k in v if isinstance(v[k], dict)), key=lambda k: v[k]["n_diff"], default=None)
                m = "NONE" if near is None else "NONE (closest: %s, %d px differ)" % (near, v[near]["n_diff"])
            print(f"{kind:4} {name:6} matches={m}")
' "$D/orient-compare.json"
done
"$PY" -I -c '
import glob, sys, tifffile
f = sorted(glob.glob(sys.argv[1] + "/o-rot90/tif/*.tif"))
a = tifffile.imread(f[0]) if f else None
print("uncropped rot90 TIFF nonzero pixels:", None if a is None else int((a != 0).sum()), "of", None if a is None else a.size)
' "$W/full"
