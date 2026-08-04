#include <gtest/gtest.h>

#include <chrono>
#include <thread>

#include <slmaster.h>

using namespace slmaster;
using namespace slmaster::device;
using namespace std;
using namespace cv;

namespace {
// Distinct, easily-diffed patterns.
Mat makePattern(const int rows, const int cols, const uchar fill) {
    return Mat(rows, cols, CV_8UC1, Scalar(fill));
}

PatternOrderSet makeSet(const vector<Mat> &imgs, const int exposureUs) {
    PatternOrderSet set;
    set.imgs_ = imgs;
    set.patternArrayCounts_ = static_cast<int>(imgs.size());
    set.illumination_ = RGB;
    set.invertPatterns_ = false;
    set.isVertical_ = false;
    set.isOneBit_ = false;
    set.exposureTime_ = exposureUs;
    set.preExposureTime_ = 0;
    set.postExposureTime_ = 0;
    return set;
}

bool waitFor(const function<bool()> &cond, const int timeoutMs) {
    const auto deadline = std::chrono::steady_clock::now() +
                          std::chrono::milliseconds(timeoutMs);
    while (std::chrono::steady_clock::now() < deadline) {
        if (cond()) {
            return true;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    return false;
}
} // namespace

class MonitorProjectorSuit : public testing::Test {
  public:
    void SetUp() override {
        projector_.setVirtualDisplay(true); // headless: no window
        ASSERT_TRUE(projector_.connect());
        patterns_ = {makePattern(48, 64, 32), makePattern(48, 64, 128),
                     makePattern(48, 64, 255)};
    }
    void TearDown() override { projector_.disConnect(); }

    MonitorProjector projector_;
    vector<Mat> patterns_;
};

TEST_F(MonitorProjectorSuit, testFactoryCreatesBackend) {
    ProjectorFactory factory;
    Projector *proj = factory.getProjector("Monitor");
    ASSERT_NE(proj, nullptr);
}

TEST_F(MonitorProjectorSuit, testPopulate) {
    ASSERT_TRUE(projector_.populatePatternTableData({makeSet(patterns_, 2000)}));
    EXPECT_EQ(projector_.getFlashImgsNum(), 3);

    const ProjectorInfo info = projector_.getInfo();
    EXPECT_EQ(info.dlpEvmType_, "Monitor");
    EXPECT_TRUE(info.isFind_);
}

TEST_F(MonitorProjectorSuit, testProjectOnceShowsAllPatternsInOrder) {
    ASSERT_TRUE(projector_.populatePatternTableData({makeSet(patterns_, 2000)}));
    ASSERT_TRUE(projector_.project(false));

    ASSERT_TRUE(waitFor([&] { return projector_.projectedCount() >= 3; }, 5000));
    ASSERT_TRUE(projector_.stop());

    // After the pass the screen holds blank (idle state).
    const Mat shown = projector_.currentPattern();
    ASSERT_FALSE(shown.empty());
    EXPECT_EQ(countNonZero(shown), 0);
}

TEST_F(MonitorProjectorSuit, testContinuousLoopUntilStop) {
    ASSERT_TRUE(projector_.populatePatternTableData({makeSet(patterns_, 2000)}));
    ASSERT_TRUE(projector_.project(true));

    // Loop mode: count must exceed one full pass.
    ASSERT_TRUE(waitFor([&] { return projector_.projectedCount() > 3; }, 5000));
    ASSERT_TRUE(projector_.stop());
}

TEST_F(MonitorProjectorSuit, testPauseHoldsAndResumeContinues) {
    ASSERT_TRUE(projector_.populatePatternTableData({makeSet(patterns_, 50000)}));
    ASSERT_TRUE(projector_.project(true));
    ASSERT_TRUE(waitFor([&] { return projector_.projectedCount() >= 1; }, 5000));

    ASSERT_TRUE(projector_.pause());
    const int held = projector_.projectedCount();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    EXPECT_EQ(projector_.projectedCount(), held); // frozen while paused

    ASSERT_TRUE(projector_.resume());
    ASSERT_TRUE(waitFor(
        [&] { return projector_.projectedCount() > held; }, 5000));
    ASSERT_TRUE(projector_.stop());
}

TEST_F(MonitorProjectorSuit, testStepMode) {
    ASSERT_TRUE(projector_.populatePatternTableData({makeSet(patterns_, 2000)}));

    for (int i = 0; i < 4; ++i) { // 4 steps over 3 patterns -> wraps around
        ASSERT_TRUE(projector_.step());
    }
    EXPECT_EQ(projector_.projectedCount(), 4);

    Mat diff;
    absdiff(projector_.currentPattern(), patterns_[0], diff); // 4th step = idx 0
    EXPECT_EQ(countNonZero(diff), 0);
}
