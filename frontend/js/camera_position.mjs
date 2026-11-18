export const POSITION_MESSAGES = {
  too_close: "Bạn đang quá gần hoặc ra sát mép hình. Hãy lùi lại để camera thấy rõ người và các khớp.",
  wrong_angle: "Hãy xoay người sang góc nhìn ngang để camera đo góc động tác rõ hơn.",
  incomplete: "Hãy điều chỉnh vị trí hoặc camera để thấy rõ vai, hông và các khớp đang tập.",
};

const STABLE_WARNING_MS = 1500;
const CLEAR_WARNING_MS = 750;
const REMINDER_INTERVAL_MS = 12000;

function visiblePoint(pose, index) {
  const point = pose?.[index];
  return point && Number.isFinite(point.x) && Number.isFinite(point.y) &&
    (point.visibility ?? 0) >= 0.6 && (point.presence ?? 1) >= 0.6 ? point : null;
}

function inFrame(point) {
  return point && point.x > 0.025 && point.x < 0.975 && point.y > 0.025 && point.y < 0.975;
}

export function assessCameraPosition(pose, exerciseId, width, height) {
  if (!Array.isArray(pose) || !pose.length || width <= 0 || height <= 0) return null;
  const shoulders = [visiblePoint(pose, 11), visiblePoint(pose, 12)];
  const hips = [visiblePoint(pose, 23), visiblePoint(pose, 24)];
  const sides = shoulders.map((shoulder, index) => {
    const hip = hips[index];
    if (!shoulder || !hip) return {pixels: 0, fraction: 0};
    const dx = shoulder.x - hip.x;
    const dy = shoulder.y - hip.y;
    return {pixels: Math.hypot(dx * width, dy * height), fraction: Math.hypot(dx, dy)};
  });
  const torso = Math.max(...sides.map(side => side.pixels));
  const torsoFraction = Math.max(...sides.map(side => side.fraction));
  const shoulderWidth = shoulders.every(Boolean) ? Math.abs(shoulders[0].x - shoulders[1].x) * width : 0;
  // Use frame fractions for proximity so a horizontal push-up in a wide video
  // is assessed against the available width as well as height.
  if (torsoFraction > 0.58 || shoulderWidth > width * 0.72 ||
      (torsoFraction > 0.38 && [...shoulders, ...hips].filter(Boolean).some(point => !inFrame(point)))) {
    return "too_close";
  }
  if (!torso) return shoulders.every(inFrame) ? "incomplete" : null;

  const exercise = exerciseId.toLowerCase();
  const upperBody = /push_?up|dip|hit_dat/.test(exercise);
  const chains = upperBody ? [[11, 13, 15, 23], [12, 14, 16, 24]] : [[11, 23, 25, 27], [12, 24, 26, 28]];
  if (!chains.some(chain => chain.every(index => inFrame(visiblePoint(pose, index))))) return "incomplete";

  // These exercises use side-view joint angles. A broad shoulder AND hip span
  // indicates a frontal view. Ratios use pixels to account for video aspect ratio.
  const needsSideView = exercise === "squat" || upperBody;
  if (needsSideView && shoulders.every(inFrame) && hips.every(inFrame)) {
    const hipWidth = Math.abs(hips[0].x - hips[1].x) * width;
    if (shoulderWidth / torso > 0.65 && hipWidth / torso > 0.35) return "wrong_angle";
  }
  return null;
}

export function createCameraPositionMonitor({onChange, remind}) {
  let candidate = null, since = 0, active = null, lastReminder = -Infinity, lastFrame = -Infinity;
  return {
    update(pose, exerciseId, width, height, now) {
      const warning = assessCameraPosition(pose, exerciseId, width, height);
      if (warning !== candidate || now - lastFrame > 1000) {
        candidate = warning;
        since = now;
      }
      lastFrame = now;
      const settle = warning ? STABLE_WARNING_MS : CLEAR_WARNING_MS;
      if (now - since < settle) return;
      if (active !== warning) {
        active = warning;
        onChange(warning);
      }
      if (active && now - lastReminder >= REMINDER_INTERVAL_MS && remind(active)) lastReminder = now;
    },
    reset() {
      candidate = active = null;
      since = 0;
      lastFrame = -Infinity;
      onChange(null);
    },
  };
}
