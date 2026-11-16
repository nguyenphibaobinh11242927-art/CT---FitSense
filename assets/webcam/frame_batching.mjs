export const KNEE_CHANGE_THRESHOLD_DEGREES = 5;
export const GESTURE_SAMPLE_INTERVAL_MS = 50;
export const POSE_HEARTBEAT_INTERVAL_MS = 1000;

export function createFrameBatchFilter() {
  let lastQueuedAt = null;
  let lastKneeAngle = null;
  let lastGestureActive = false;
  let lastTracked = false;

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
      const gestureNeedsSample = gestureActive &&
        now - lastQueuedAt >= GESTURE_SAMPLE_INTERVAL_MS;
      const heartbeatDue = now - lastQueuedAt >= POSE_HEARTBEAT_INTERVAL_MS;

      return gestureChanged || trackingChanged || angleChanged ||
        angleTrackingChanged || gestureNeedsSample || heartbeatDue;
    },

    noteQueued(frame, now) {
      lastQueuedAt = now;
      lastKneeAngle = Number.isFinite(frame.knee_angle) ? frame.knee_angle : null;
      lastGestureActive = frame.start_detected === true || frame.x_detected === true;
      lastTracked = frame.head_detected === true && Number.isFinite(frame.knee_angle);
    },

    reset() {
      lastQueuedAt = null;
      lastKneeAngle = null;
      lastGestureActive = false;
      lastTracked = false;
    },
  };
}
