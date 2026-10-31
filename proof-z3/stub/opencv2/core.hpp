// Minimal stand-in for <opencv2/core.hpp>, enough to compile RotateFlip.hpp's
// geometry (cv::Size, cv::Point, cv::Rect). The Mat/rotate/flip stubs are never
// called by dump_rects.cpp; prove.py checks the pixel semantics against real OpenCV.
#pragma once
namespace cv {
struct Size { int width = 0, height = 0; Size() = default; Size(int w, int h) : width(w), height(h) {} };
struct Point { int x = 0, y = 0; Point() = default; Point(int x_, int y_) : x(x_), y(y_) {} };
struct Rect { int x = 0, y = 0, width = 0, height = 0; Rect() = default;
              Rect(int x_, int y_, int w, int h) : x(x_), y(y_), width(w), height(h) {} };
struct Mat {};
enum RotateFlags { ROTATE_90_CLOCKWISE = 0, ROTATE_180 = 1, ROTATE_90_COUNTERCLOCKWISE = 2 };
inline void rotate(Mat&, Mat&, int) {}
inline void flip(Mat&, Mat&, int) {}
}
