import assert from "node:assert/strict";
import test from "node:test";

import {
  createTooCloseDebouncer,
  getPoseDiagnostics,
  TOO_CLOSE_DEBOUNCE_MS,
} from "../assets/webcam/pose_diagnostics.mjs";

function pose() {
  const points = [];
  const add = (index, x, y = 0.5, visibility = 1) => {
    points[index] = {x, y, visibility};
  };
  add(0, 0.5, 0.1);
  add(11, 0.4);
  add(12, 0.6);
  add(23, 0.4);
  add(24, 0.6);
  add(25, 0.4);
  add(26, 0.6);
  add(27, 0.4);
  add(28, 0.6);
  add(13, 0.4);
  add(14, 0.6);
  add(15, 0.4);
  add(16, 0.6);
  return points;
}

test("too-close candidate detects cropped lower body or shoulder span over 40 percent", () => {
  const cropped = pose();
  for (const index of [25, 26, 27, 28]) cropped[index].visibility = 0.49;
  assert.equal(getPoseDiagnostics(cropped).tooCloseCandidate, true);

  const wide = pose();
  wide[11].x = 0.29;
  wide[12].x = 0.71;
  assert.equal(getPoseDiagnostics(wide).tooCloseCandidate, true);

  const normal = pose();
  normal[11].visibility = normal[12].visibility = 0.5;
  assert.equal(getPoseDiagnostics(normal).tooCloseCandidate, false);
  assert.equal(getPoseDiagnostics([]).tooCloseCandidate, false);
});

test("bad-angle flag requires at least one full joint chain on either side", () => {
  const squat = pose();
  for (const index of [23, 24, 25, 26, 27, 28]) squat[index].visibility = 0.49;
  assert.equal(getPoseDiagnostics(squat, "squat").isBadAngle, true);
  squat[23].visibility = squat[25].visibility = squat[27].visibility = 1;
  assert.equal(getPoseDiagnostics(squat, "squat").isBadAngle, false);

  const pushup = pose();
  assert.equal(getPoseDiagnostics(pushup, "push_up").isBadAngle, false);
  pushup[13].visibility = pushup[14].visibility = 0.49;
  assert.equal(getPoseDiagnostics(pushup, "push_up").isBadAngle, true);
});

test("too-close debounce requires continuous pose evidence for 1.1 seconds", () => {
  const debounce = createTooCloseDebouncer();
  assert.equal(TOO_CLOSE_DEBOUNCE_MS, 1100);
  assert.equal(debounce.update(true, 0), false);
  assert.equal(debounce.update(true, 200), false);
  assert.equal(debounce.update(true, 400), false);
  assert.equal(debounce.update(true, 600), false);
  assert.equal(debounce.update(true, 800), false);
  assert.equal(debounce.update(true, 1000), false);
  assert.equal(debounce.update(true, 1100), true);
  assert.equal(debounce.update(false, 1133), false);
  assert.equal(debounce.update(true, 1200), false);
  assert.equal(debounce.update(true, 1400), false);
  assert.equal(debounce.update(true, 1600), false);
  assert.equal(debounce.update(true, 1800), false);
  assert.equal(debounce.update(true, 2000), false);
  assert.equal(debounce.update(true, 2200), false);
  assert.equal(debounce.update(true, 2300), true);
  assert.equal(debounce.update(true, 3401), false);
});
