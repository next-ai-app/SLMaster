#include "monitorProjector.h"

#include <chrono>
#include <cstdio>
#include <cstdlib>

namespace slmaster {
namespace device {

namespace {
constexpr int kDefaultExposureUs = 20000; // 20ms ~= one 60Hz refresh
constexpr int kMinLiveExposureUs = 16667; // LCD refresh floor
} // namespace

MonitorProjector::MonitorProjector() {
    const char *env = std::getenv("SLMASTER_MONITOR_VIRTUAL");
    if (env && env[0] == '1') {
        isVirtual_ = true;
    }
}

MonitorProjector::~MonitorProjector() { disConnect(); }

ProjectorInfo MonitorProjector::getInfo() {
    ProjectorInfo info;
    info.dlpEvmType_ = "Monitor";
    info.width_ = windowWidth_ > 0 ? windowWidth_ : 1920;
    info.height_ = windowHeight_ > 0 ? windowHeight_ : 1080;
    info.isFind_ = isConnected_.load(std::memory_order_acquire);
    return info;
}

bool MonitorProjector::connect() {
    if (isConnected_.load(std::memory_order_acquire)) {
        return true;
    }
    if (!isVirtual_) {
        try {
            cv::namedWindow(windowName_, cv::WINDOW_NORMAL);
            if (windowX_ >= 0 && windowY_ >= 0) {
                cv::moveWindow(windowName_, windowX_, windowY_);
            }
            if (windowWidth_ <= 0) {
                cv::setWindowProperty(windowName_, cv::WND_PROP_FULLSCREEN,
                                      cv::WINDOW_FULLSCREEN);
            } else {
                cv::resizeWindow(windowName_, windowWidth_, windowHeight_);
            }
        } catch (const cv::Exception &e) {
            // Headless environment (no X11/Wayland/Cocoa): degrade to virtual.
            std::fprintf(stderr,
                         "[MonitorProjector] window creation failed (%s); "
                         "falling back to virtual display\n",
                         e.what());
            isVirtual_ = true;
        }
    }
    isConnected_.store(true, std::memory_order_release);
    showBlank_();
    return true;
}

bool MonitorProjector::disConnect() {
    stop();
    if (!isVirtual_ && isConnected_.load(std::memory_order_acquire)) {
        try {
            cv::destroyWindow(windowName_);
            cv::waitKey(1);
        } catch (const cv::Exception &) {
        }
    }
    isConnected_.store(false, std::memory_order_release);
    return true;
}

bool MonitorProjector::isConnect() {
    return isConnected_.load(std::memory_order_acquire);
}

int MonitorProjector::totalExposureUs_(IN const PatternOrderSet &set) {
    const int total =
        set.preExposureTime_ + set.exposureTime_ + set.postExposureTime_;
    return total > 0 ? total : kDefaultExposureUs;
}

bool MonitorProjector::populatePatternTableData(
    IN std::vector<PatternOrderSet> table) {
    if (state_.load(std::memory_order_acquire) != State::Idle) {
        return false; // don't rewrite the table mid-projection
    }
    std::lock_guard<std::mutex> lock(mtx_);
    patterns_.clear();
    exposureTimesUs_.clear();
    for (const auto &set : table) {
        const int exposureUs = totalExposureUs_(set);
        for (const auto &img : set.imgs_) {
            if (img.empty()) {
                continue;
            }
            patterns_.push_back(img.clone());
            exposureTimesUs_.push_back(exposureUs);
        }
    }
    return !patterns_.empty();
}

void MonitorProjector::showPattern_(IN const size_t index) {
    cv::Mat img;
    {
        std::lock_guard<std::mutex> lock(mtx_);
        img = patterns_[index];
        currentPattern_ = img;
    }
    if (!isVirtual_) {
        try {
            cv::imshow(windowName_, img);
            cv::waitKey(1);
        } catch (const cv::Exception &) {
        }
    }
    currentIndex_.store(index, std::memory_order_release);
    projectedCount_.fetch_add(1, std::memory_order_acq_rel);
}

void MonitorProjector::showBlank_() {
    ProjectorInfo info = getInfo();
    cv::Mat black = cv::Mat::zeros(info.height_, info.width_, CV_8UC1);
    {
        std::lock_guard<std::mutex> lock(mtx_);
        currentPattern_ = black;
    }
    if (!isVirtual_ && isConnected_.load(std::memory_order_acquire)) {
        try {
            cv::imshow(windowName_, black);
            cv::waitKey(1);
        } catch (const cv::Exception &) {
        }
    }
}

void MonitorProjector::displayLoop_(IN const bool isContinue) {
    bool warnedFloor = false;
    do {
        const size_t count = patterns_.size();
        for (size_t i = 0; i < count; ++i) {
            if (stopRequested_.load(std::memory_order_acquire)) {
                break;
            }
            while (state_.load(std::memory_order_acquire) == State::Paused &&
                   !stopRequested_.load(std::memory_order_acquire)) {
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
            }
            if (stopRequested_.load(std::memory_order_acquire)) {
                break;
            }
            int exposureUs = exposureTimesUs_[i];
            if (!isVirtual_ && exposureUs < kMinLiveExposureUs) {
                if (!warnedFloor) {
                    std::fprintf(stderr,
                                 "[MonitorProjector] exposure < %dus is below "
                                 "the LCD refresh floor; clamping\n",
                                 kMinLiveExposureUs);
                    warnedFloor = true;
                }
                exposureUs = kMinLiveExposureUs;
            }
            showPattern_(i);
            std::this_thread::sleep_for(std::chrono::microseconds(exposureUs));
        }
    } while (isContinue && !stopRequested_.load(std::memory_order_acquire));

    state_.store(State::Idle, std::memory_order_release);
    showBlank_();
}

bool MonitorProjector::project(IN const bool isContinue) {
    if (!isConnected_.load(std::memory_order_acquire)) {
        return false;
    }
    {
        std::lock_guard<std::mutex> lock(mtx_);
        if (patterns_.empty()) {
            return false;
        }
    }
    State expected = State::Idle;
    if (!state_.compare_exchange_strong(expected, State::Projecting,
                                        std::memory_order_acq_rel)) {
        return false; // already projecting / paused
    }
    stopRequested_.store(false, std::memory_order_release);
    projectedCount_.store(0, std::memory_order_release);
    if (displayThread_.joinable()) {
        displayThread_.join();
    }
    displayThread_ = std::thread(&MonitorProjector::displayLoop_, this,
                                 isContinue);
    return true;
}

bool MonitorProjector::pause() {
    State expected = State::Projecting;
    return state_.compare_exchange_strong(expected, State::Paused,
                                          std::memory_order_acq_rel);
}

bool MonitorProjector::resume() {
    State expected = State::Paused;
    return state_.compare_exchange_strong(expected, State::Projecting,
                                          std::memory_order_acq_rel);
}

bool MonitorProjector::stop() {
    const State cur = state_.load(std::memory_order_acquire);
    if (cur == State::Idle) {
        return true;
    }
    stopRequested_.store(true, std::memory_order_release);
    // Unstick a paused loop.
    state_.store(State::Projecting, std::memory_order_release);
    if (displayThread_.joinable()) {
        displayThread_.join();
    }
    stopRequested_.store(false, std::memory_order_release);
    state_.store(State::Idle, std::memory_order_release);
    return true;
}

bool MonitorProjector::step() {
    if (!isConnected_.load(std::memory_order_acquire)) {
        return false;
    }
    if (state_.load(std::memory_order_acquire) != State::Idle) {
        return false; // step mode only when not free-running
    }
    size_t index;
    {
        std::lock_guard<std::mutex> lock(mtx_);
        if (patterns_.empty()) {
            return false;
        }
        index = currentIndex_.load(std::memory_order_acquire);
    }
    showPattern_(index);
    currentIndex_.store((index + 1) % patterns_.size(),
                        std::memory_order_release);
    return true;
}

bool MonitorProjector::getLEDCurrent(OUT double &, OUT double &, OUT double &) {
    return false; // no LED on a monitor
}

bool MonitorProjector::setLEDCurrent(IN const double, IN const double,
                                     IN const double) {
    return false;
}

int MonitorProjector::getFlashImgsNum() {
    std::lock_guard<std::mutex> lock(mtx_);
    return static_cast<int>(patterns_.size());
}

void MonitorProjector::setVirtualDisplay(IN const bool isVirtual) {
    if (state_.load(std::memory_order_acquire) == State::Idle) {
        isVirtual_ = isVirtual;
    }
}

bool MonitorProjector::isVirtualDisplay() const { return isVirtual_; }

void MonitorProjector::setWindowGeometry(IN const int x, IN const int y,
                                         IN const int width,
                                         IN const int height) {
    windowX_ = x;
    windowY_ = y;
    windowWidth_ = width;
    windowHeight_ = height;
}

cv::Mat MonitorProjector::currentPattern() const {
    std::lock_guard<std::mutex> lock(mtx_);
    return currentPattern_.clone();
}

int MonitorProjector::projectedCount() const {
    return projectedCount_.load(std::memory_order_acquire);
}

} // namespace device
} // namespace slmaster
