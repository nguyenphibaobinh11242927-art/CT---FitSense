from math import atan2, degrees
from pathlib import Path
from time import monotonic_ns

import cv2
import mediapipe as mp

from config import CAMERA_INDEX

vision = mp.tasks.vision
MODEL = Path(__file__).resolve().parents[1] / "models" / "pose_landmarker_lite.task"
joint = vision.PoseLandmark
JOINTS = {
    "Left elbow": (joint.LEFT_SHOULDER, joint.LEFT_ELBOW, joint.LEFT_WRIST),
    "Right elbow": (joint.RIGHT_SHOULDER, joint.RIGHT_ELBOW, joint.RIGHT_WRIST),
    "Left knee": (joint.LEFT_HIP, joint.LEFT_KNEE, joint.LEFT_ANKLE),
    "Right knee": (joint.RIGHT_HIP, joint.RIGHT_KNEE, joint.RIGHT_ANKLE),
}


def joint_angle(a, b, c):
    """Angle ABC in degrees, using points in image pixels."""
    ux, uy = a[0] - b[0], a[1] - b[1]
    vx, vy = c[0] - b[0], c[1] - b[1]
    if (ux, uy) == (0, 0) or (vx, vy) == (0, 0):
        return None
    return degrees(atan2(abs(ux * vy - uy * vx), ux * vx + uy * vy))


def draw_pose(frame, landmarks):
    height, width = frame.shape[:2]
    points = {
        index: (round(point.x * width), round(point.y * height))
        for index, point in enumerate(landmarks)
        if point.visibility is not None and point.visibility >= 0.5
    }
    for edge in vision.PoseLandmarksConnections.POSE_LANDMARKS:
        if edge.start in points and edge.end in points:
            cv2.line(frame, points[edge.start], points[edge.end], (90, 230, 110), 2)
    for xy in points.values():
        cv2.circle(frame, xy, 4, (40, 180, 255), -1)
    return points


def main():
    options = vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_buffer=MODEL.read_bytes()),
        running_mode=vision.RunningMode.VIDEO,
    )
    mirror = True
    with vision.PoseLandmarker.create_from_options(options) as detector:
        camera = cv2.VideoCapture(CAMERA_INDEX)
        try:
            if not camera.isOpened():
                print(f"Không mở được camera số {CAMERA_INDEX}.")
                return
            window_start = monotonic_ns()
            frame_count = 0
            fps_text = "FPS: ..."
            while True:
                ok, frame = camera.read()
                if not ok:
                    print("Không đọc được hình từ camera.")
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = detector.detect_for_video(image, monotonic_ns() // 1_000_000)
                points = draw_pose(frame, result.pose_landmarks[0]) if result.pose_landmarks else {}
                if mirror:
                    frame = cv2.flip(frame, 1)
                status = "Tracking" if result.pose_landmarks else "Looking for pose"
                cv2.putText(frame, f"{status} | M: mirror | Q: quit", (12, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
                for row, (name, indices) in enumerate(JOINTS.items()):
                    angle = None
                    if all(index in points for index in indices):
                        angle = joint_angle(*(points[index] for index in indices))
                    value = "--" if angle is None else f"{angle:.0f} deg"
                    cv2.putText(frame, f"{name}: {value}", (12, 58 + row * 24),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
                frame_count += 1
                now = monotonic_ns()
                elapsed = (now - window_start) / 1_000_000_000

                if elapsed >= 1.0:
                    fps_text = f"FPS: {frame_count / elapsed:.1f}"
                    frame_count = 0
                    window_start = now

                cv2.putText(frame, fps_text, (12, frame.shape[0] - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
                cv2.imshow("FitSense", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), ord("Q")):
                    break
                if key in (ord("m"), ord("M")):
                    mirror = not mirror
        finally:
            camera.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
