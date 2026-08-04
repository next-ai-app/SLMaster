import cv2
import numpy as np

from sl_edu import calibrate


def _render_board(K, image_size, board, rvec, tvec):
    """Project a synthetic chessboard into a virtual camera view."""
    objp = np.zeros((board[0] * board[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:board[0], 0:board[1]].T.reshape(-1, 2)
    pts, _ = cv2.projectPoints(objp * 25.0, rvec, tvec, K, np.zeros(5))
    img = np.full(image_size[::-1], 255, np.uint8)  # (H, W)
    for p in pts.reshape(-1, 2):
        cv2.circle(img, tuple(np.round(p).astype(int)), 6, 0, -1)
    return img, pts.reshape(-1, 1, 2).astype(np.float32)


def test_calibrate_camera_recovers_intrinsics():
    board = (9, 6)
    image_size = (640, 480)
    K_true = np.array([[525.0, 0, 320], [0, 525.0, 240], [0, 0, 1]])
    views = [
        (np.array([0.1, 0.1, 0.05]), np.array([0.0, 0.0, 600.0])),
        (np.array([-0.15, 0.1, 0.2]), np.array([30.0, -20.0, 650.0])),
        (np.array([0.2, -0.1, -0.15]), np.array([-40.0, 10.0, 550.0])),
        (np.array([0.0, 0.2, 0.1]), np.array([10.0, 30.0, 700.0])),
    ]
    img_points = [ _render_board(K_true, image_size, board, r, t)[1]
                   for r, t in views ]
    objp = np.zeros((board[0] * board[1], 3), np.float32)
    objp[:, :2] = np.mgrid[0:board[0], 0:board[1]].T.reshape(-1, 2)
    objp *= 25.0
    cal = calibrate.calibrate_camera(objp, img_points, image_size)
    assert cal["rms"] < 1.0
    assert abs(cal["K"][0, 0] - 525.0) < 5.0
    assert abs(cal["K"][0, 2] - 320.0) < 5.0


def test_find_corners_needs_enough_views():
    blank = [np.full((480, 640), 255, np.uint8) for _ in range(5)]
    try:
        calibrate.find_chessboard_corners(blank, (9, 6))
    except ValueError as e:
        assert "views" in str(e)
    else:
        raise AssertionError("expected ValueError on blank images")
