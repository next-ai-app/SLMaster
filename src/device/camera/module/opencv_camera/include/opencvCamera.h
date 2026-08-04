/**
 * @file opencvCamera.h
 * @brief Universal camera backend on cv::VideoCapture (UVC webcam, video file,
 *        image sequence, RTSP). No proprietary SDK required.
 *        Backends: V4L2 (Linux) / AVFoundation (macOS) / MSMF (Windows).
 */
#ifndef __OPENCV_CAMERA_H_
#define __OPENCV_CAMERA_H_

#include <atomic>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>

#include <opencv2/opencv.hpp>

#include "camera.h"
#include "safeQueue.hpp"
#include "typeDef.h"

namespace slmaster {
namespace device {

/**
 * @brief Camera implementation on top of cv::VideoCapture.
 *
 * cameraUserId interpretation:
 *   - pure digits ("0", "1", ...)      -> local device index
 *   - anything else                    -> URI: video file, image sequence
 *     ("dir/%d.bmp"), rtsp://..., etc.
 *
 * Structured-light pipelines work on intensity, so frames are converted to
 * grayscale by default; disable via setBooleanAttribute("Gray Output", false).
 */
class DEVICE_API OpenCvCamera : public Camera {
  public:
    explicit OpenCvCamera(IN const std::string cameraUserId);
    ~OpenCvCamera() override;

    CameraInfo getCameraInfo() override;
    bool connect() override;
    bool disConnect() override;
    SafeQueue<cv::Mat> &getImgs() override;
    bool pushImg(IN const cv::Mat &img) override;
    cv::Mat popImg() override;
    bool clearImgs() override;
    bool isConnect() override;
    cv::Mat capture() override;
    bool start() override;
    bool pause() override;
    bool setTrigMode(IN const TrigMode trigMode) override;

    bool setEnumAttribute(IN const std::string attributeName,
                          IN const std::string val) override;
    bool setStringAttribute(IN const std::string attributeName,
                            IN const std::string val) override;
    bool setNumberAttribute(IN const std::string attributeName,
                            IN const double val) override;
    bool setBooleanAttribute(IN const std::string attributeName,
                             IN const bool val) override;
    bool getEnumAttribute(IN const std::string attributeName,
                          OUT std::string &val) override;
    bool getStringAttribute(IN const std::string attributeName,
                            OUT std::string &val) override;
    bool getNumbericalAttribute(IN const std::string attributeName,
                                OUT double &val) override;
    bool getBooleanAttribute(IN const std::string attributeName,
                             OUT bool &val) override;
    int getFps() override;

  private:
    cv::Mat grabOne_();
    void grabLoop_();
    bool isDeviceIndex_() const;

    const std::string cameraUserId_;
    cv::VideoCapture cap_;
    SafeQueue<cv::Mat> imgs_;
    std::thread grabThread_;
    std::atomic<bool> isGrabbing_{false};
    std::atomic<bool> isConnected_{false};
    std::mutex capMtx_;
    TrigMode trigMode_{trigContinous};
    bool grayOutput_{true};
    std::unordered_map<std::string, double> numbers_;
    std::unordered_map<std::string, std::string> strings_;
    std::unordered_map<std::string, std::string> enums_;
};

} // namespace device
} // namespace slmaster

#endif // __OPENCV_CAMERA_H_
