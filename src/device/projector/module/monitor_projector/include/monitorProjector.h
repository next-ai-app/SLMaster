/**
 * @file monitorProjector.h
 * @brief Monitor-as-projector backend: renders structured-light patterns
 *        fullscreen on any display. Standard lab technique — replaces the
 *        DLPC347x + Cypress stack with a plain HDMI monitor.
 *
 * Timing floor: one monitor refresh (~16.7ms @60Hz) per pattern in live
 * display mode; shorter exposures are physically meaningless on an LCD.
 *
 * Virtual mode (setVirtualDisplay(true) or SLMASTER_MONITOR_VIRTUAL=1):
 * no window is created; patterns are tracked with accurate timing — used by
 * headless tests and full-pipeline simulation.
 *
 * macOS note: Cocoa requires window operations on the main thread. Drive the
 * projector from the GUI main thread via step(), or use virtual mode.
 */
#ifndef __MONITOR_PROJECTOR_H_
#define __MONITOR_PROJECTOR_H_

#include <atomic>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include <opencv2/opencv.hpp>

#include "projector.h"
#include "typeDef.h"

namespace slmaster {
namespace device {

class DEVICE_API MonitorProjector : public Projector {
  public:
    MonitorProjector();
    ~MonitorProjector() override;

    ProjectorInfo getInfo() override;
    bool connect() override;
    bool disConnect() override;
    bool isConnect() override;
    bool populatePatternTableData(IN std::vector<PatternOrderSet> table) override;
    bool project(IN const bool isContinue) override;
    bool pause() override;
    bool stop() override;
    bool resume() override;
    bool step() override;
    bool getLEDCurrent(OUT double &r, OUT double &g, OUT double &b) override;
    bool setLEDCurrent(IN const double r, IN const double g,
                       IN const double b) override;
    int getFlashImgsNum() override;

    // --- backend-specific configuration (not part of Projector) ---
    void setVirtualDisplay(IN const bool isVirtual);
    bool isVirtualDisplay() const;
    /** Position/size of the projection window; (-1,-1) = fullscreen. */
    void setWindowGeometry(IN const int x, IN const int y, IN const int width,
                           IN const int height);
    /** Currently displayed pattern (empty when blank). Simulation hook. */
    cv::Mat currentPattern() const;
    /** Number of patterns shown since project()/step() started. */
    int projectedCount() const;

  private:
    enum class State { Idle, Projecting, Paused };

    void displayLoop_(IN const bool isContinue);
    void showPattern_(IN const size_t index);
    void showBlank_();
    static int totalExposureUs_(IN const PatternOrderSet &set);

    std::string windowName_{"SLMaster Monitor Projector"};
    std::vector<cv::Mat> patterns_;
    std::vector<int> exposureTimesUs_;
    std::thread displayThread_;
    mutable std::mutex mtx_;
    std::atomic<State> state_{State::Idle};
    std::atomic<bool> stopRequested_{false};
    std::atomic<bool> isConnected_{false};
    std::atomic<int> projectedCount_{0};
    std::atomic<size_t> currentIndex_{0};
    cv::Mat currentPattern_;
    bool isVirtual_{false};
    int windowX_{-1};
    int windowY_{-1};
    int windowWidth_{-1};
    int windowHeight_{-1};
};

} // namespace device
} // namespace slmaster

#endif // __MONITOR_PROJECTOR_H_
