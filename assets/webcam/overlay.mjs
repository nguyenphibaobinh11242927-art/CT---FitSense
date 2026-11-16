export const COLORS = {
  left: "#38bdf8",
  right: "#fb923c",
  center: "#e5e7eb",
  ok: "#22c55e",
  warn: "#facc15",
  bad: "#ef4444",
};

export function landmarkSide(index) {
  if (!Number.isInteger(index) || index < 0 || index < 11) return "center";
  return index % 2 === 1 ? "left" : "right";
}

export function boneColor(start, end) {
  const startSide = landmarkSide(start);
  const endSide = landmarkSide(end);
  return COLORS[startSide === endSide ? startSide : "center"];
}

export function jointZone(angle) {
  if (!Number.isFinite(angle)) return "none";
  return angle >= 160 || angle <= 90 ? "ok" : "warn";
}

export function kneeValgus(leftKnee, rightKnee, leftAnkle, rightAnkle) {
  const points = [leftKnee, rightKnee, leftAnkle, rightAnkle];
  if (points.some(point => !point || !Number.isFinite(point.x))) return false;
  const ankleDistance = Math.abs(leftAnkle.x - rightAnkle.x);
  return ankleDistance > 0 &&
    Math.abs(leftKnee.x - rightKnee.x) < 0.75 * ankleDistance;
}

export function createOneEuro({minCutoff = 1.0, beta = 3.0, dCutoff = 1.0} = {}) {
  if (![minCutoff, beta, dCutoff].every(Number.isFinite) ||
      minCutoff <= 0 || beta < 0 || dCutoff <= 0) {
    throw new RangeError("Invalid One-Euro filter parameters.");
  }
  let value, derivative = 0, lastTime;
  const alpha = (cutoff, dt) => {
    const ratio = 2 * Math.PI * cutoff * dt;
    return ratio / (ratio + 1);
  };

  return (nextValue, timeSeconds) => {
    if (!Number.isFinite(nextValue) || !Number.isFinite(timeSeconds)) {
      throw new TypeError("One-Euro filter inputs must be finite.");
    }
    if (value === undefined) {
      value = nextValue;
      lastTime = timeSeconds;
      return value;
    }

    const dt = Math.max(1e-3, timeSeconds - lastTime);
    lastTime = timeSeconds;
    const rawDerivative = (nextValue - value) / dt;
    derivative += alpha(dCutoff, dt) * (rawDerivative - derivative);
    const cutoff = minCutoff + beta * Math.abs(derivative);
    value += alpha(cutoff, dt) * (nextValue - value);
    return value;
  };
}

export function createLandmarkSmoother(options) {
  let xFilters = [], yFilters = [];
  return {
    reset() {
      xFilters = [];
      yFilters = [];
    },
    smooth(pose, timeSeconds) {
      return Array.from(pose, (point, index) => {
        if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) {
          xFilters[index] = undefined;
          yFilters[index] = undefined;
          return point;
        }
        xFilters[index] ??= createOneEuro(options);
        yFilters[index] ??= createOneEuro(options);
        return {
          ...point,
          x: xFilters[index](point.x, timeSeconds),
          y: yFilters[index](point.y, timeSeconds),
        };
      });
    },
  };
}

export function createFpsStats(size = 10) {
  if (!Number.isInteger(size) || size <= 0) {
    throw new RangeError("FPS history size must be a positive integer.");
  }
  let samples = [];
  return {
    add(fps) {
      if (!Number.isFinite(fps) || fps < 0) {
        throw new TypeError("FPS sample must be finite and non-negative.");
      }
      samples.push(fps);
      if (samples.length > size) samples.shift();
    },
    reset() {
      samples = [];
    },
    get avg() {
      return samples.length
        ? samples.reduce((sum, value) => sum + value, 0) / samples.length
        : 0;
    },
    get min() {
      return samples.length ? Math.min(...samples) : 0;
    },
  };
}

export function formatFps(stats, detectMs) {
  const detection = Number.isFinite(detectMs) ? detectMs : 0;
  return `FPS: ${stats.avg.toFixed(1)} (min ${stats.min.toFixed(1)}) · nhận diện ${detection.toFixed(0)} ms`;
}
