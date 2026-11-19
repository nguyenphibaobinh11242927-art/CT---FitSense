export const TOO_CLOSE_DEBOUNCE_MS = 1100;
const MAX_CONTINUOUS_GAP_MS = 250;
const VISIBILITY_THRESHOLD = 0.5;

function isVisible(pose, index) {
  const point = pose?.[index];
  return Boolean(
    point &&
    Number.isFinite(point.x) &&
    Number.isFinite(point.y) &&
    (point.visibility ?? 0) >= VISIBILITY_THRESHOLD
  );
}

export function getPoseDiagnostics(pose, exerciseType = "squat", frameWidth = 1) {
  if (!Number.isFinite(frameWidth) || frameWidth <= 0) {
    throw new RangeError("Frame width must be a positive finite number.");
  }
  const visible = index => isVisible(pose, index);
  const upperBodyVisible = [0, 11, 12].some(visible);
  const lowerBodyVisible = [25, 26, 27, 28].some(visible);
  const shoulderWidthRatio = visible(11) && visible(12)
    ? Math.abs(pose[11].x - pose[12].x)
      / frameWidth
    : 0;
  const tooCloseCandidate = upperBodyVisible &&
    (!lowerBodyVisible || shoulderWidthRatio > 0.4);

  const sides = exerciseType === "push_up"
    ? [[11, 13, 15], [12, 14, 16]]
    : [[23, 25, 27], [24, 26, 28]];
  const hasCompleteSide = sides.some(side => side.every(visible));
  const personVisible = [
    0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28,
  ].some(visible);

  return {
    tooCloseCandidate,
    isBadAngle: personVisible && !hasCompleteSide,
  };
}

export function createTooCloseDebouncer(durationMs = TOO_CLOSE_DEBOUNCE_MS) {
  if (!Number.isFinite(durationMs) || durationMs <= 0) {
    throw new RangeError("Too-close debounce duration must be positive.");
  }
  let candidateSince = null;
  let lastCandidateAt = null;

  return {
    update(candidate, now) {
      if (typeof candidate !== "boolean" || !Number.isFinite(now)) {
        throw new TypeError("Too-close debounce requires a boolean and finite timestamp.");
      }
      if (!candidate) {
        this.reset();
        return false;
      }
      if (lastCandidateAt === null || now - lastCandidateAt > MAX_CONTINUOUS_GAP_MS) {
        candidateSince = now;
      }
      lastCandidateAt = now;
      return now - candidateSince >= durationMs;
    },
    reset() {
      candidateSince = null;
      lastCandidateAt = null;
    },
  };
}
