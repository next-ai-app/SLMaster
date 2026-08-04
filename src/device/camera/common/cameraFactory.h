/**
 * @file cameraFactory.h
 * @author Evans Liu (1369215984@qq.com)
 * @brief
 * @version 0.1
 * @date 2024-03-19
 *
 * @copyright Copyright (c) 2024
 *
 */

#ifndef __CAMERA_FACTORY_H_
#define __CAMERA_FACTORY_H_

#include "typeDef.h"
#include "camera.h"

#include <string>
#include <unordered_map>

#ifdef WITH_HUARAY_CAMERA
#include "huarayCamera.h"
#endif

#ifdef WITH_OPENCV_CAMERA
#include "opencvCamera.h"
#endif

/** @brief slmaster **/
namespace slmaster {
/** @brief 设备库 **/
namespace device {
/** @brief 相机工厂类 **/
class DEVICE_API CameraFactory {
  public:
    /** @brief 相机厂商 **/
    enum CameraManufactor { Huaray = 0, Halcon, OpenCV };

    /** @brief Map config string to manufactor enum ("Huaray"/"Halcon"/"OpenCV"). */
    static CameraManufactor manufactorFromString(const std::string &name) {
        if (name == "Huaray") {
            return Huaray;
        }
        if (name == "OpenCV") {
            return OpenCV;
        }
        return Halcon; // historical fallback branch
    }

    Camera *getCamera(std::string cameraUserId, CameraManufactor manufactor) {
        Camera *camera = nullptr;

        if (cameras_.count(cameraUserId)) {
            return cameras_[cameraUserId];
        } else {
#ifdef WITH_HUARAY_CAMERA
            if (Huaray == manufactor) {
                camera = new HuarayCammera(cameraUserId);
                cameras_[cameraUserId] = camera;
            }
            // TODO@Evans Liu:增加海康相机支持
            else if (Halcon == manufactor) {
                camera = new HuarayCammera(cameraUserId);
                cameras_[cameraUserId] = camera;
            }
#else
            (void)manufactor; // no camera backend compiled in on this platform
#endif
#ifdef WITH_OPENCV_CAMERA
            if (OpenCV == manufactor) {
                camera = new OpenCvCamera(cameraUserId);
                cameras_[cameraUserId] = camera;
            }
#endif
        }

        return camera;
    }

  private:
    std::unordered_map<std::string, Camera *> cameras_;
}; // class CameraFactory
} // namespace device
} // namespace slmaster

#endif //__CAMERA_FACTORY_H_
