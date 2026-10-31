// End-to-end check of the real header on real OpenCV: for every source size up to
// N x N, every rotate/flip value and every destination rect, rotating/flipping the
// cropped source rect gives exactly the same pixels as cropping the rotated/flipped image.
#include <cstdio>
#include <cstdlib>
#include <opencv2/core.hpp>
#include "vc/core/util/RotateFlip.hpp"
int main(int argc, char** argv) {
    const int N = argc > 1 ? std::atoi(argv[1]) : 8;
    long checks = 0, fails = 0;
    for (int W = 1; W <= N; ++W) for (int H = 1; H <= N; ++H) {
        cv::Mat src(H, W, CV_32SC1);
        for (int y = 0; y < H; ++y) for (int x = 0; x < W; ++x) src.at<int>(y, x) = y * W + x;
        for (int rq = -1; rq <= 3; ++rq) for (int fl = -1; fl <= 2; ++fl) {
            cv::Mat expected = src.clone();
            vc::rotateFlipIfNeeded(expected, rq, fl);
            const cv::Size out = vc::rotatedSize(src.size(), rq);
            if (expected.size() != out) { std::printf("size mismatch W=%d H=%d rq=%d fl=%d\n", W, H, rq, fl); return 1; }
            for (int y = 0; y < out.height; ++y) for (int x = 0; x < out.width; ++x)
            for (int h = 1; y + h <= out.height; ++h) for (int w = 1; x + w <= out.width; ++w) {
                const cv::Rect dst(x, y, w, h);
                const cv::Rect s = vc::srcRectForDst(dst, src.size(), rq, fl);
                ++checks;
                if ((s & cv::Rect(0, 0, W, H)) != s) { ++fails; continue; }
                cv::Mat got = src(s).clone();
                vc::rotateFlipIfNeeded(got, rq, fl);
                if (got.size() != dst.size() || cv::countNonZero(got != expected(dst)) != 0) ++fails;
            }
        }
    }
    std::printf("pixel_check: OpenCV %s, sizes 1..%d, %ld rects, %ld failures: %s\n",
                CV_VERSION, N, checks, fails, fails ? "FAIL" : "PASS");
    return fails ? 1 : 0;
}
