"""Proof that vc::srcRectForDst (RotateFlip.hpp) is correct for every image size.

Claim. For every source size W x H (1 <= W, H <= INT_MAX), every rotQuad in
{-1, 0, 1, 2, 3}, every flipAxis in {-1, 0, 1, 2}, and every destination rect
D inside rotatedSize(W x H), the rect S = srcRectForDst(D, W x H, rot, flip)
satisfies:
  1. S lies inside the source image and is non-empty;
  2. rotatedSize(W x H) is the real output size of rotateFlipIfNeeded;
  3. rotateFlipIfNeeded(src(S)) has exactly D's size;
  4. pixel (u, v) of rotateFlipIfNeeded(src(S)) is pixel (D.x+u, D.y+v) of
     rotateFlipIfNeeded(src), for every (u, v) in D, i.e. the crop-then-transform
     the renderer does equals the transform-then-crop the user asked for;
  5. no int arithmetic in srcRectForDst overflows 32 bits.

Three parts, each needed for the next:
  A. An OpenCV model built from OpenCV's own definitions (cv::rotate is
     transpose + flip; cv::flip codes 0, 1, -1) is checked against real OpenCV
     (cv2) on every size up to 7 x 7 and every rotate/flip value.
  B. A Python transcription of srcRectForDst is checked against the compiled
     header (dump_rects, built against a geometry-only cv stub) on every source
     size up to 8 x 8, every rotate/flip value and every destination rect.
  C. z3 proves claims 1-5 for the transcription and the model, for all sizes,
     by showing that the negation is unsatisfiable. Two sabotaged
     transcriptions must come back SAT, so the proof can fail.

Usage: python3 prove.py DUMP_FILE   (DUMP_FILE = output of ./dump_rects 8)
"""
import sys
import numpy as np
import cv2
import z3

INT_MAX = 2**31 - 1
INT_MIN = -(2**31)
ROTS = (-1, 0, 1, 2, 3)
FLIPS = (-1, 0, 1, 2)


def is_z3(v):
    return isinstance(v, z3.ExprRef)


def vmin(a, b):
    return z3.If(a <= b, a, b) if (is_z3(a) or is_z3(b)) else min(a, b)


def vmax(a, b):
    return z3.If(a >= b, a, b) if (is_z3(a) or is_z3(b)) else max(a, b)


# ---------------------------------------------------------------- OpenCV model
# An op takes the input size (w, h) and returns (out_w, out_h, src) where
# src(x, y) is the input pixel that lands on output pixel (x, y).

def transpose(w, h):
    return h, w, lambda x, y: (y, x)


def flip(code):
    def op(w, h):
        if code == 0:
            return w, h, lambda x, y: (x, h - 1 - y)
        if code == 1:
            return w, h, lambda x, y: (w - 1 - x, y)
        return w, h, lambda x, y: (w - 1 - x, h - 1 - y)  # code -1
    return op


def chain(ops, w, h):
    """Apply ops left to right; returns the output size and the composed src map."""
    maps = []
    for op in ops:
        w, h, m = op(w, h)
        maps.append(m)

    def src(x, y):
        for m in reversed(maps):
            x, y = m(x, y)
        return x, y
    return w, h, src


# OpenCV's cv::rotate (core/src/matrix_transform.cpp):
#   ROTATE_90_CLOCKWISE        = transpose, then flip(1)
#   ROTATE_180                 = flip(-1)
#   ROTATE_90_COUNTERCLOCKWISE = transpose, then flip(0)
CV_ROTATE = {
    'cw': [transpose, flip(1)],
    '180': [flip(-1)],
    'ccw': [transpose, flip(0)],
}


def model_ops(rq, fl):
    """rotateFlipIfNeeded as OpenCV ops: rotQuad 1 = CCW, 2 = 180, 3 = CW; then the flip."""
    ops = []
    if rq == 1:
        ops += CV_ROTATE['ccw']
    elif rq == 2:
        ops += CV_ROTATE['180']
    elif rq == 3:
        ops += CV_ROTATE['cw']
    if fl == 0:
        ops.append(flip(0))
    elif fl == 1:
        ops.append(flip(1))
    elif fl == 2:
        ops.append(flip(-1))
    return ops


def cv2_rotate_flip(m, rq, fl):
    """Line-for-line Python mirror of vc::rotateFlipIfNeeded, on real OpenCV."""
    if rq == 1:
        m = cv2.rotate(m, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif rq == 2:
        m = cv2.rotate(m, cv2.ROTATE_180)
    elif rq == 3:
        m = cv2.rotate(m, cv2.ROTATE_90_CLOCKWISE)
    if fl == 0:
        m = cv2.flip(m, 0)
    elif fl == 1:
        m = cv2.flip(m, 1)
    elif fl == 2:
        m = cv2.flip(m, -1)
    return m


# ------------------------------------------------- srcRectForDst transcription

def rotated_size(w, h, rq):
    return (h, w) if rq in (1, 3) else (w, h)


def src_rect(dx, dy, dw, dh, W, H, rq, fl, trace=None, mutant=None):
    """Transcription of vc::srcRectForDst. trace collects every int the C++ computes."""
    t = trace if trace is not None else []
    outW, outH = rotated_size(W, H, rq)

    def source_point(x, y):
        if fl in (1, 2):
            x = outW - 1 - x
            t.append(outW - 1); t.append(x)
        if fl in (0, 2):
            # mutant 'flip-uses-src-size': flip y against the source height instead of the output height
            y = (H if mutant == 'flip-uses-src-size' else outH) - 1 - y
            t.append(outH - 1); t.append(y)
        if rq == 1:
            # mutant 'ccw-uses-height': W - 1 - y written as H - 1 - y
            p = ((H if mutant == 'ccw-uses-height' else W) - 1 - y, x)
            t.append(W - 1)
        elif rq == 2:
            p = (W - 1 - x, H - 1 - y)
            t.extend([W - 1, H - 1])
        elif rq == 3:
            p = (y, H - 1 - x)
            t.append(H - 1)
        else:
            p = (x, y)
        t.extend(list(p))
        return p

    xe = dx + dw
    ye = dy + dh
    t.extend([xe, xe - 1, ye, ye - 1])
    p0 = source_point(dx, dy)
    p1 = source_point(xe - 1, dy)
    p2 = source_point(dx, ye - 1)
    p3 = source_point(xe - 1, ye - 1)
    x0 = vmin(vmin(p0[0], p1[0]), vmin(p2[0], p3[0]))
    y0 = vmin(vmin(p0[1], p1[1]), vmin(p2[1], p3[1]))
    x1 = vmax(vmax(p0[0], p1[0]), vmax(p2[0], p3[0]))
    y1 = vmax(vmax(p0[1], p1[1]), vmax(p2[1], p3[1]))
    t.extend([x1 - x0, x1 - x0 + 1, y1 - y0, y1 - y0 + 1])
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1


# ------------------------------------------------------------------- part A

def part_a(n=7):
    checks = 0
    for W in range(1, n + 1):
        for H in range(1, n + 1):
            img = np.arange(W * H, dtype=np.int32).reshape(H, W)
            for prim, ops in (('transpose', [transpose]), ('flip0', [flip(0)]),
                              ('flip1', [flip(1)]), ('flip-1', [flip(-1)])):
                ref = {'transpose': lambda m: cv2.transpose(m), 'flip0': lambda m: cv2.flip(m, 0),
                       'flip1': lambda m: cv2.flip(m, 1), 'flip-1': lambda m: cv2.flip(m, -1)}[prim](img)
                ow, oh, src = chain(ops, W, H)
                assert ref.shape == (oh, ow), (prim, W, H)
                for y in range(oh):
                    for x in range(ow):
                        sx, sy = src(x, y)
                        assert ref[y, x] == img[sy, sx], (prim, W, H, x, y)
                        checks += 1
            for rq in ROTS:
                for fl in FLIPS:
                    out = cv2_rotate_flip(img, rq, fl)
                    ow, oh, src = chain(model_ops(rq, fl), W, H)
                    assert out.shape == (oh, ow), (W, H, rq, fl)
                    for y in range(oh):
                        for x in range(ow):
                            sx, sy = src(x, y)
                            assert out[y, x] == img[sy, sx], (W, H, rq, fl, x, y)
                            checks += 1
    print(f"A  OpenCV model == cv2 {cv2.__version__}: {checks} pixel checks, sizes 1..{n} x 1..{n}, all rotate/flip values: PASS")


# ------------------------------------------------------------------- part B

def part_b(dump_path):
    sizes = rects = 0
    with open(dump_path) as f:
        for line in f:
            tag, *v = line.split()
            v = list(map(int, v))
            if tag == 'S':
                W, H, rq, fl, ow, oh = v
                assert rotated_size(W, H, rq) == (ow, oh), line
                sizes += 1
            else:
                W, H, rq, fl, x, y, w, h, sx, sy, sw, sh = v
                assert src_rect(x, y, w, h, W, H, rq, fl) == (sx, sy, sw, sh), line
                rects += 1
    assert sizes == 8 * 8 * 5 * 4 and rects > 0, (sizes, rects)
    print(f"B  transcription == compiled RotateFlip.hpp: {sizes} rotatedSize and {rects} srcRectForDst results: PASS")


# ------------------------------------------------------------------- part C

def prove_one(rq, fl, mutant=None):
    W, H, dx, dy, dw, dh, u, v = z3.Ints('W H dx dy dw dh u v')
    outW, outH = rotated_size(W, H, rq)
    pre = [W >= 1, W <= INT_MAX, H >= 1, H <= INT_MAX,
           dx >= 0, dy >= 0, dw >= 1, dh >= 1, dx + dw <= outW, dy + dh <= outH,
           u >= 0, u < dw, v >= 0, v < dh]
    trace = []
    sx, sy, sw, sh = src_rect(dx, dy, dw, dh, W, H, rq, fl, trace, mutant)
    oW, oH, full = chain(model_ops(rq, fl), W, H)
    lW, lH, local = chain(model_ops(rq, fl), sw, sh)
    fx, fy = full(dx + u, dy + v)
    lx, ly = local(u, v)
    claim = z3.And(
        sx >= 0, sy >= 0, sw >= 1, sh >= 1, sx + sw <= W, sy + sh <= H,  # 1
        oW == outW, oH == outH,                                           # 2
        lW == dw, lH == dh,                                               # 3
        fx == sx + lx, fy == sy + ly,                                     # 4
        *[z3.And(e >= INT_MIN, e <= INT_MAX) for e in trace if is_z3(e)],  # 5
    )
    s = z3.Solver()
    s.add(*pre)
    s.add(z3.Not(claim))
    r = s.check()
    return r, (s.model() if r == z3.sat else None)


def part_c():
    for rq in ROTS:
        for fl in FLIPS:
            r, _ = prove_one(rq, fl)
            assert r == z3.unsat, f"COUNTEREXAMPLE rot={rq} flip={fl}: {r}"
    print(f"C  z3 {z3.get_version_string()}: claims 1-5 hold for all 1 <= W, H <= INT_MAX, "
          f"all {len(ROTS) * len(FLIPS)} rotate/flip pairs (negation UNSAT each): PROVED")
    for mutant, rq, fl in (('ccw-uses-height', 1, -1), ('flip-uses-src-size', 1, 0)):
        r, m = prove_one(rq, fl, mutant)
        assert r == z3.sat, f"sabotage {mutant} was not caught"
        cex = {k: m[z3.Int(k)] for k in ('W', 'H', 'dx', 'dy', 'dw', 'dh', 'u', 'v')}
        print(f"C  sabotage '{mutant}' (rot={rq} flip={fl}): SAT as expected, counterexample {cex}")


if __name__ == '__main__':
    part_a()
    part_b(sys.argv[1])
    part_c()
    print("ALL PARTS PASS")
