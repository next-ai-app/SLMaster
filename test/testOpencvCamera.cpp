#include <gtest/gtest.h>

#include <chrono>
#include <thread>

#include <slmaster.h>

using namespace slmaster;
using namespace slmaster::device;
using namespace std;
using namespace cv;

// Image-sequence "camera": cv::VideoCapture reads 0.bmp..8.bmp as frames.
// Exercises the full backend with zero hardware.
const string seqPath = "../../data/shiftGraycode/%d.bmp";

class OpenCvCameraSuit : public testing::Test {
  public:
    void SetUp() override {
        reference_ = imread("../../data/shiftGraycode/0.bmp", 0);
        ASSERT_FALSE(reference_.empty());
    }
    Mat reference_;
};

TEST_F(OpenCvCameraSuit, testFactoryCreatesBackend) {
    CameraFactory factory;
    Camera *cam = factory.getCamera("factory-seq", CameraFactory::OpenCV);
    ASSERT_NE(cam, nullptr);
}

TEST_F(OpenCvCameraSuit, testConnectAndInfo) {
    OpenCvCamera cam(seqPath);
    ASSERT_TRUE(cam.connect());
    ASSERT_TRUE(cam.isConnect());

    const CameraInfo info = cam.getCameraInfo();
    EXPECT_EQ(info.cameraUserId_, seqPath);
    EXPECT_EQ(info.deviceType_, "URI");
    EXPECT_TRUE(info.isFind_);

    ASSERT_TRUE(cam.disConnect());
    EXPECT_FALSE(cam.isConnect());
}

TEST_F(OpenCvCameraSuit, testCaptureFrameMatchesData) {
    OpenCvCamera cam(seqPath);
    ASSERT_TRUE(cam.connect());

    const Mat frame = cam.capture();
    ASSERT_FALSE(frame.empty());
    EXPECT_EQ(frame.cols, reference_.cols);
    EXPECT_EQ(frame.rows, reference_.rows);
    EXPECT_EQ(frame.channels(), 1); // gray output is the default

    ASSERT_TRUE(cam.disConnect());
}

TEST_F(OpenCvCameraSuit, testSequenceAdvances) {
    OpenCvCamera cam(seqPath);
    ASSERT_TRUE(cam.connect());

    const Mat first = cam.capture();
    Mat later;
    for (int i = 0; i < 7; ++i) {
        later = cam.capture();
    }
    ASSERT_FALSE(first.empty());
    ASSERT_FALSE(later.empty());
    // Frames 0 and 7 of a pattern sequence must differ.
    Mat diff;
    absdiff(first, later, diff);
    EXPECT_GT(countNonZero(diff), 0);

    ASSERT_TRUE(cam.disConnect());
}

TEST_F(OpenCvCameraSuit, testContinuousStreamFillsQueue) {
    OpenCvCamera cam(seqPath);
    ASSERT_TRUE(cam.connect());
    ASSERT_TRUE(cam.start());

    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    ASSERT_TRUE(cam.pause());

    EXPECT_GT(cam.getImgs().size(), 0u);
    while (cam.getImgs().size()) {
        EXPECT_FALSE(cam.popImg().empty());
    }
    EXPECT_TRUE(cam.clearImgs());

    ASSERT_TRUE(cam.disConnect());
}

TEST_F(OpenCvCameraSuit, testNumberAttributeRoundTrip) {
    OpenCvCamera cam(seqPath);
    // Cached before connect (applied on connect for hardware properties).
    ASSERT_TRUE(cam.setNumberAttribute("Exposure", 10000.0));
    double val = 0.0;
    ASSERT_TRUE(cam.getNumbericalAttribute("Exposure", val));
    EXPECT_DOUBLE_EQ(val, 10000.0);
}
