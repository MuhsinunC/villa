// Prints rotatedSize and srcRectForDst from the real RotateFlip.hpp for every
// source size up to N x N, every rotate/flip value, and every destination rect.
#include <cstdio>
#include <cstdlib>
#include "vc/core/util/RotateFlip.hpp"
int main(int argc, char** argv) {
    const int N = argc > 1 ? std::atoi(argv[1]) : 8;
    for (int W = 1; W <= N; ++W) for (int H = 1; H <= N; ++H)
    for (int rq = -1; rq <= 3; ++rq) for (int fl = -1; fl <= 2; ++fl) {
        const cv::Size out = vc::rotatedSize(cv::Size(W, H), rq);
        std::printf("S %d %d %d %d %d %d\n", W, H, rq, fl, out.width, out.height);
        for (int y = 0; y < out.height; ++y) for (int x = 0; x < out.width; ++x)
        for (int h = 1; y + h <= out.height; ++h) for (int w = 1; x + w <= out.width; ++w) {
            const cv::Rect s = vc::srcRectForDst(cv::Rect(x, y, w, h), cv::Size(W, H), rq, fl);
            std::printf("R %d %d %d %d %d %d %d %d %d %d %d %d\n", W, H, rq, fl, x, y, w, h, s.x, s.y, s.width, s.height);
        }
    }
}
