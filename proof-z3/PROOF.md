# srcRectForDst: proof for every image size

What it proves, for the `RotateFlip.hpp` in this PR's fix (sha256 `699f95e3c1991ddf27c437b16301123831cbbc4dbffe0e325a96e5b1351e95f8`, as in this PR):
for every source size W x H with 1 <= W, H <= INT_MAX, every `rotQuad` in {-1, 0, 1, 2, 3}, every `flipAxis` in {-1, 0, 1, 2}, and every destination rect D inside the rotated output, the rect S = `srcRectForDst(D, ...)`:

1. lies inside the source image and is not empty;
2. `rotatedSize` equals the real output size of `rotateFlipIfNeeded`;
3. after `rotateFlipIfNeeded`, the crop of S has exactly D's size;
4. pixel (u, v) of the transformed crop of S equals pixel (D.x+u, D.y+v) of the transformed full image, for every (u, v) in D. So rendering S and then rotating/flipping it gives the same pixels as cropping D out of the rotated/flipped full render;
5. needs no int arithmetic that overflows 32 bits.

The proof runs in three steps, and each step backs the next one:

- `pixel_check.cpp` compiles the real header against villa's own OpenCV (4.10.0, in the `vc3d-deps/linux` CI image). It checks claim 4 on real `cv::Mat` data for every size up to 8 x 8, every rotate/flip value and every destination rect (288,000 rects, 0 failures).
- `prove.py` part A builds OpenCV's rotate and flip from OpenCV's own definitions (`cv::rotate` is a transpose plus a flip) and checks that model against `cv2` 4.10.0 on every size up to 7 x 7 (18,816 pixels).
- Part B checks a line-by-line Python transcription of `srcRectForDst` against the compiled header's output on every size up to 8 x 8 and every destination rect (288,000 rects).
- Part C has z3 4.15.4 prove claims 1-5 for the transcription and the OpenCV model at every size, one query per rotate/flip pair (20 queries, all UNSAT for the negation). Two deliberately broken versions of the helper come back SAT with a counterexample, which shows the proof can fail.

It doesn't cover the gen() block alignment in the renderer (the CLI test covers that end to end), or how the renderer tiles the output into destination rects.

Run it: `sh run.sh` in any Linux box with g++ and Python 3. In villa's CI image it takes about 15 s. Result from 2026-10-31, on a Linux x86_64 machine in `ghcr.io/scrollprize/vc3d-deps/linux:sha-0c371b1d...`: `RESULT-2026-10-31.log`.
