"""Triangulation and point-cloud reconstruction.

The calibrated pipeline: absolute phase -> projector column -> stereo
correspondence (camera pixel, projector column) -> 3D points -> depth map ->
point cloud.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def phase_to_projector_col(absolute_phase: np.ndarray, n_periods: int,
                           projector_width: int) -> np.ndarray:
    """Map absolute phase (rad, [0, 2*pi*n_periods]) to projector column."""
    px_per_period = projector_width / n_periods
    return absolute_phase / (2 * np.pi) * px_per_period


def triangulate(cam_points: np.ndarray, proj_points: np.ndarray,
                cam_K: np.ndarray, cam_d: np.ndarray,
                proj_K: np.ndarray, proj_d: np.ndarray,
                R: np.ndarray, T: np.ndarray) -> np.ndarray:
    """Stereo triangulation treating the projector as a second camera.

    cam_points/proj_points: (N,2) corresponding pixels. R, T follow the
    cv2.stereoCalibrate convention: P_cam = R @ P_proj + T. Returns (N,3)
    points in the camera frame.
    """
    pts1 = cv2.undistortPoints(cam_points.reshape(-1, 1, 2), cam_K, cam_d)
    pts2 = cv2.undistortPoints(proj_points.reshape(-1, 1, 2), proj_K, proj_d)
    P1 = np.hstack([np.eye(3), np.zeros((3, 1))])
    # Projector projection FROM the camera (world) frame: invert the extrinsic
    P2 = np.hstack([R.T, (-R.T @ T).reshape(3, 1)])
    homog = cv2.triangulatePoints(P1, P2, pts1, pts2)
    return (homog[:3] / homog[3]).T


def to_depth_map(points3d: np.ndarray, cam_points: np.ndarray,
                 shape: tuple[int, int]) -> np.ndarray:
    """Scatter (N,3) camera-frame points back to a (H,W) z-depth map."""
    depth = np.zeros(shape, np.float32)
    px = np.round(cam_points).astype(int)
    inside = (px[:, 0] >= 0) & (px[:, 0] < shape[1]) & \
             (px[:, 1] >= 0) & (px[:, 1] < shape[0])
    depth[px[inside, 1], px[inside, 0]] = points3d[inside, 2].astype(np.float32)
    return depth


def save_ply(path: str | Path, xyz: np.ndarray,
             colors: np.ndarray | None = None) -> Path:
    """Save (N,3) points (+ optional (N,3) RGB) via open3d."""
    import open3d as o3d

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(xyz.astype(np.float64))
    if colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(colors.astype(np.float64) / 255)
    path = Path(path)
    o3d.io.write_point_cloud(str(path), pcd)
    return path
