import numpy as np

from sl_edu import reconstruct


def _synthetic_setup():
    """Camera at origin, 'projector' 100mm to the right, no distortion."""
    K = np.array([[800.0, 0, 320], [0, 800, 240], [0, 0, 1]])
    d = np.zeros(5)
    R = np.eye(3)
    T = np.array([100.0, 0, 0])  # stereoCalibrate convention: P_cam = R@P_proj + T
    return K, d, R, T


def test_triangulate_recovers_synthetic_points():
    K, d, R, T = _synthetic_setup()
    rng = np.random.default_rng(42)
    pts3d = np.column_stack([rng.uniform(-50, 50, 30),
                             rng.uniform(-50, 50, 30),
                             rng.uniform(400, 800, 30)])
    # project into camera and projector views
    cam_px, _ = __import__("cv2").projectPoints(pts3d, np.eye(3),
                                                np.zeros(3), K, d)
    Rp, Tp = R.T, -R.T @ T  # camera pose in projector frame
    proj_px, _ = __import__("cv2").projectPoints(pts3d, Rp, Tp, K, d)
    est = reconstruct.triangulate(cam_px.reshape(-1, 2), proj_px.reshape(-1, 2),
                                  K, d, K, d, R, T)
    rel_err = np.linalg.norm(est - pts3d, axis=1) / np.linalg.norm(pts3d, axis=1)
    assert rel_err.max() < 1e-3


def test_phase_to_col_and_depth_map():
    abs_phase = np.linspace(0, 32 * 2 * np.pi, 193)[:-1][None, :]
    cols = reconstruct.phase_to_projector_col(abs_phase, 32, 1920)
    assert np.allclose(cols[0], np.arange(192) * 10, atol=0.5)

    pts3d = np.array([[0, 0, 500.0], [10, 0, 600.0]])
    cam_px = np.array([[100.0, 80.0], [200.0, 80.0]])
    depth = reconstruct.to_depth_map(pts3d, cam_px, (240, 320))
    assert depth[80, 100] == 500.0 and depth[80, 200] == 600.0


def test_save_ply_roundtrip(tmp_path):
    import open3d as o3d

    xyz = np.random.default_rng(0).normal(size=(100, 3))
    path = reconstruct.save_ply(tmp_path / "cloud.ply", xyz)
    back = np.asarray(o3d.io.read_point_cloud(str(path)).points)
    assert np.allclose(back, xyz, atol=1e-5)
