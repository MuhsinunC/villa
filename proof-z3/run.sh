#!/bin/sh
# Runs the whole proof on a fresh machine. With OpenCV's C++ headers present
# (villa's vc3d-deps CI image), the header is compiled against real OpenCV and
# pixel_check.cpp runs; otherwise the geometry-only stub is used for dump_rects.
set -eu
cd "$(dirname "$0")"
g++ --version | head -1
sha256sum vc/core/util/RotateFlip.hpp
if pkg-config --exists opencv4; then
    echo "OpenCV C++ $(pkg-config --modversion opencv4): compiling against the real headers"
    CV="$(pkg-config --cflags opencv4)"; LIBS="$(pkg-config --libs opencv4)"
    g++ -std=c++17 -O1 -Wall -Wextra -Werror $CV -I . pixel_check.cpp -o pixel_check $LIBS
    ./pixel_check 8
else
    echo "no OpenCV C++ headers: using the geometry-only stub"; CV="-I stub"
fi
g++ -std=c++17 -O1 -Wall -Wextra -Werror $CV -I . dump_rects.cpp -o dump_rects
./dump_rects 8 > dump.txt
python3 -m venv .venv
.venv/bin/pip install -q z3-solver==4.15.4.0 opencv-python-headless==4.10.0.84 numpy
.venv/bin/python prove.py dump.txt
