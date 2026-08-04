"""Camera and projector calibration helpers.

Thin, readable wrappers over cv2.calibrateCamera / cv2.stereoCalibrate,
with the structured-light twist: the projector is calibrated AS a camera by
decoding which projector column lit each chessboard corner.
"""
from __future__ import annotations

import cv2
import numpy as np


def find_chessboard_corners(images: list[np.ndarray],
                            board_size: tuple[int, int],
                            subpix_win: int = 11):
    """Return (obj_point, img_points, used_idx) or raise if <3 views found."""
    objp = np.zeros((board_size[0] * board_size[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:board_size[0], 0:board_size[1]].T.reshape(-1, 2)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3)
    img_points, used = [], []
    for i, img in enumerate(images):
        ok, corners = cv2.findChessboardCorners(img, board_size)
        if not ok:
            continue
        corners = cv2.cornerSubPix(img, corners, (subpix_win, subpix_win),
                                   (-1, -1), criteria)
        img_points.append(corners)
        used.append(i)
    if len(img_points) < 3:
        raise ValueError(f"chessboard found in only {len(img_points)} views")
    return objp, img_points, used


def calibrate_camera(obj_points, img_points, image_size) -> dict:
    """Monocular calibration. obj_points repeated per view."""
    objp = [obj_points] * len(img_points)
    rms, K, dist, _, _ = cv2.calibrateCamera(objp, img_points, image_size,
                                             None, None)
    return {"K": K, "dist": dist, "rms": float(rms)}


def calibrate_stereo(obj_points, cam_points, proj_points, cam_cal: dict,
                     proj_cal: dict, image_size) -> dict:
    """Stereo calibration with fixed intrinsics -> R, T between camera and
    projector(-as-camera)."""
    objp = [obj_points] * len(cam_points)
    flags = cv2.CALIB_FIX_INTRINSIC
    rms, K1, d1, K2, d2, R, T, _, _ = cv2.stereoCalibrate(
        objp, cam_points, proj_points, cam_cal["K"], cam_cal["dist"],
        proj_cal["K"], proj_cal["dist"], image_size, flags=flags)
    return {"K1": K1, "d1": d1, "K2": K2, "d2": d2, "R": R, "T": T,
            "rms": float(rms)}
