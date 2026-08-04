#include "opencvCamera.h"

#include <chrono>

namespace slmaster {
namespace device {

namespace {
// Camera attribute name -> cv::VideoCapture property. Units of CAP_PROP_EXPOSURE
// are backend-dependent (log2 seconds on V4L2!) — treat as best-effort.
const std::unordered_map<std::string, int> kNumberToCapProp = {
    {"Width", cv::CAP_PROP_FRAME_WIDTH},
    {"Height", cv::CAP_PROP_FRAME_HEIGHT},
    {"FPS", cv::CAP_PROP_FPS},
    {"Exposure", cv::CAP_PROP_EXPOSURE},
    {"Gain", cv::CAP_PROP_GAIN},
    {"Auto Exposure", cv::CAP_PROP_AUTO_EXPOSURE},
    {"Brightness", cv::CAP_PROP_BRIGHTNESS},
};
} // namespace

OpenCvCamera::OpenCvCamera(IN const std::string cameraUserId)
    : cameraUserId_(cameraUserId) {}

OpenCvCamera::~OpenCvCamera() { disConnect(); }

bool OpenCvCamera::isDeviceIndex_() const {
    return !cameraUserId_.empty() &&
           std::all_of(cameraUserId_.begin(), cameraUserId_.end(), ::isdigit);
}

CameraInfo OpenCvCamera::getCameraInfo() {
    CameraInfo info;
    info.cameraKey_ = cameraUserId_;
    info.cameraUserId_ = cameraUserId_;
    info.deviceType_ = isDeviceIndex_() ? "UVC" : "URI";
    info.isFind_ = isConnected_.load(std::memory_order_acquire);
    return info;
}

bool OpenCvCamera::connect() {
    if (isConnected_.load(std::memory_order_acquire)) {
        return true;
    }
    std::lock_guard<std::mutex> lock(capMtx_);
    bool opened = isDeviceIndex_()
                      ? cap_.open(std::stoi(cameraUserId_))
                      : cap_.open(cameraUserId_);
    if (!opened) {
        return false;
    }
    // Re-apply cached numeric properties (e.g. resolution set before connect).
    for (const auto &[name, val] : numbers_) {
        const auto it = kNumberToCapProp.find(name);
        if (it != kNumberToCapProp.end()) {
            cap_.set(it->second, val);
        }
    }
    isConnected_.store(true, std::memory_order_release);
    return true;
}

bool OpenCvCamera::disConnect() {
    pause();
    std::lock_guard<std::mutex> lock(capMtx_);
    if (cap_.isOpened()) {
        cap_.release();
    }
    isConnected_.store(false, std::memory_order_release);
    return true;
}

bool OpenCvCamera::isConnect() {
    return isConnected_.load(std::memory_order_acquire);
}

cv::Mat OpenCvCamera::grabOne_() {
    std::lock_guard<std::mutex> lock(capMtx_);
    cv::Mat frame;
    if (!cap_.isOpened() || !cap_.read(frame) || frame.empty()) {
        return cv::Mat();
    }
    if (grayOutput_ && frame.channels() != 1) {
        cv::cvtColor(frame, frame, cv::COLOR_BGR2GRAY);
    }
    return frame;
}

cv::Mat OpenCvCamera::capture() { return grabOne_(); }

void OpenCvCamera::grabLoop_() {
    while (isGrabbing_.load(std::memory_order_acquire)) {
        cv::Mat frame = grabOne_();
        if (frame.empty()) {
            // EOF on a file/sequence source or transient device hiccup.
            std::this_thread::sleep_for(std::chrono::milliseconds(5));
            continue;
        }
        imgs_.push(frame);
    }
}

bool OpenCvCamera::start() {
    if (!isConnected_.load(std::memory_order_acquire) ||
        isGrabbing_.load(std::memory_order_acquire)) {
        return isConnected_.load(std::memory_order_acquire) &&
               isGrabbing_.load(std::memory_order_acquire);
    }
    // Software-trigger mode: frames are pulled via capture(); no stream thread.
    if (trigMode_ == trigSoftware) {
        return true;
    }
    isGrabbing_.store(true, std::memory_order_release);
    grabThread_ = std::thread(&OpenCvCamera::grabLoop_, this);
    return true;
}

bool OpenCvCamera::pause() {
    if (!isGrabbing_.exchange(false, std::memory_order_acq_rel)) {
        return true;
    }
    if (grabThread_.joinable()) {
        grabThread_.join();
    }
    return true;
}

SafeQueue<cv::Mat> &OpenCvCamera::getImgs() { return imgs_; }

bool OpenCvCamera::pushImg(IN const cv::Mat &img) {
    imgs_.push(img);
    return true;
}

cv::Mat OpenCvCamera::popImg() {
    cv::Mat img;
    imgs_.try_move_pop(img);
    return img;
}

bool OpenCvCamera::clearImgs() {
    SafeQueue<cv::Mat> empty;
    imgs_.swap(empty);
    return true;
}

bool OpenCvCamera::setTrigMode(IN const TrigMode trigMode) {
    trigMode_ = trigMode;
    return true;
}

bool OpenCvCamera::setNumberAttribute(IN const std::string attributeName,
                                      IN const double val) {
    numbers_[attributeName] = val;
    const auto it = kNumberToCapProp.find(attributeName);
    if (it == kNumberToCapProp.end()) {
        return true; // cached only; not a hardware property
    }
    if (!isConnected_.load(std::memory_order_acquire)) {
        return true; // applied on connect()
    }
    std::lock_guard<std::mutex> lock(capMtx_);
    return cap_.set(it->second, val);
}

bool OpenCvCamera::getNumbericalAttribute(IN const std::string attributeName,
                                          OUT double &val) {
    const auto it = kNumberToCapProp.find(attributeName);
    if (it != kNumberToCapProp.end() &&
        isConnected_.load(std::memory_order_acquire)) {
        std::lock_guard<std::mutex> lock(capMtx_);
        val = cap_.get(it->second);
        return true;
    }
    const auto cached = numbers_.find(attributeName);
    if (cached != numbers_.end()) {
        val = cached->second;
        return true;
    }
    return false;
}

bool OpenCvCamera::setBooleanAttribute(IN const std::string attributeName,
                                       IN const bool val) {
    if (attributeName == "Gray Output") {
        grayOutput_ = val;
        return true;
    }
    return setNumberAttribute(attributeName, val ? 1.0 : 0.0);
}

bool OpenCvCamera::getBooleanAttribute(IN const std::string attributeName,
                                       OUT bool &val) {
    if (attributeName == "Gray Output") {
        val = grayOutput_;
        return true;
    }
    double num = 0.0;
    if (!getNumbericalAttribute(attributeName, num)) {
        return false;
    }
    val = num != 0.0;
    return true;
}

bool OpenCvCamera::setEnumAttribute(IN const std::string attributeName,
                                    IN const std::string val) {
    enums_[attributeName] = val;
    return true;
}

bool OpenCvCamera::getEnumAttribute(IN const std::string attributeName,
                                    OUT std::string &val) {
    const auto it = enums_.find(attributeName);
    if (it == enums_.end()) {
        return false;
    }
    val = it->second;
    return true;
}

bool OpenCvCamera::setStringAttribute(IN const std::string attributeName,
                                      IN const std::string val) {
    strings_[attributeName] = val;
    return true;
}

bool OpenCvCamera::getStringAttribute(IN const std::string attributeName,
                                      OUT std::string &val) {
    const auto it = strings_.find(attributeName);
    if (it == strings_.end()) {
        return false;
    }
    val = it->second;
    return true;
}

int OpenCvCamera::getFps() {
    if (!isConnected_.load(std::memory_order_acquire)) {
        return 0;
    }
    std::lock_guard<std::mutex> lock(capMtx_);
    return static_cast<int>(cap_.get(cv::CAP_PROP_FPS));
}

} // namespace device
} // namespace slmaster
