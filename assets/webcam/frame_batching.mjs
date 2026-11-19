export const KNEE_CHANGE_THRESHOLD_DEGREES = 5;
export const GESTURE_SAMPLE_INTERVAL_MS = 50;
export const POSE_HEARTBEAT_INTERVAL_MS = 1000;

export function createFrameBatchFilter() {
  let lastQueuedAt = null;
  let lastKneeAngle = null;
  let lastGestureActive = false;
  let lastTracked = false;
  let lastTooClose = false;
  let lastBadAngle = false;

  return {
    shouldQueue(frame, now) {
      if (!Number.isFinite(now)) throw new TypeError("Timestamp must be finite.");
      if (lastQueuedAt === null) return true;

      const tracked = frame.head_detected === true &&
        Number.isFinite(frame.knee_angle);
      const gestureActive = frame.start_detected === true || frame.x_detected === true;
      const gestureChanged = gestureActive !== lastGestureActive;
      const trackingChanged = tracked !== lastTracked;
      const angleChanged = Number.isFinite(frame.knee_angle) &&
        Number.isFinite(lastKneeAngle) &&
        Math.abs(frame.knee_angle - lastKneeAngle) > KNEE_CHANGE_THRESHOLD_DEGREES;
      const angleTrackingChanged =
        Number.isFinite(frame.knee_angle) !== Number.isFinite(lastKneeAngle);
      const tooCloseChanged = (frame.is_too_close === true) !== lastTooClose;
      const badAngleChanged = (frame.is_bad_angle === true) !== lastBadAngle;
      const gestureNeedsSample = gestureActive &&
        now - lastQueuedAt >= GESTURE_SAMPLE_INTERVAL_MS;
      const heartbeatDue = now - lastQueuedAt >= POSE_HEARTBEAT_INTERVAL_MS;

      return gestureChanged || trackingChanged || angleChanged ||
        angleTrackingChanged || tooCloseChanged || badAngleChanged ||
        gestureNeedsSample || heartbeatDue;
    },

    noteQueued(frame, now) {
      lastQueuedAt = now;
      lastKneeAngle = Number.isFinite(frame.knee_angle) ? frame.knee_angle : null;
      lastGestureActive = frame.start_detected === true || frame.x_detected === true;
      lastTracked = frame.head_detected === true && Number.isFinite(frame.knee_angle);
      lastTooClose = frame.is_too_close === true;
      lastBadAngle = frame.is_bad_angle === true;
    },

    reset() {
      lastQueuedAt = null;
      lastKneeAngle = null;
      lastGestureActive = false;
      lastTracked = false;
      lastTooClose = false;
      lastBadAngle = false;
    },
  };
}
