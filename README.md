# Evidence for the vc_render_tifxyz --rotate / --flip fix

Evidence for the PR from branch `vc-render-rotate-flip` (fix commit 6f7fa1541 on villa main d57c28ebe). It is kept on its own branch so the PR diff stays code-only.

- `images/`: before/after renders on PHerc1447 20250521151220 (8.64 um, CC BY-NC 4.0, Vesuvius Challenge), mesh 20250703034159, 700x500 crop.
  - `evidence-tif-base-vs-head.png` and `evidence-zarr-base-vs-head.png`: numpy reference, main, and this PR.
  - `orient-crop-montage-{base,head}.png`: all five orientations, TIFF over zarr L0.
  - `terminal-*.png`: the captured terminal output of each run, rendered as an image.
- `results/`: per-variant pixel comparisons (`orient-compare-*.json`, `maxabs-crop.md`), the no-rotation byte-identity checks (`norot-*.json`), `-n 5` (`n5-compare.json`), and band-vs-tile (`bandtile-*.json`).
- `logs/`: the configure command, the CLI test on the PR build, on main and on a sabotaged build, and the targeted and full vc-core ctest runs.
- `repro/reproduce.sh BIN_DIR WORK_DIR`: downloads the mesh, streams the volume, renders each option and prints which numpy transform each output matches.
- `proof-z3/`: a z3 proof that `srcRectForDst` is correct for every image size; `sh run.sh` (about 15 s).

Everything was built and run in villa's CI image, `ghcr.io/scrollprize/vc3d-deps/linux:sha-0c371b1d472c5281b703d65517e980d945da693f`.
