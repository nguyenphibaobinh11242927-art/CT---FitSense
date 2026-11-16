import assert from "node:assert/strict";
import test from "node:test";

import {
  boneColor,
  COLORS,
  createFpsStats,
  createLandmarkSmoother,
  createOneEuro,
  formatFps,
  jointZone,
  kneeValgus,
  landmarkSide,
} from "../assets/webcam/overlay.mjs";

test("landmark sides and bones use side-specific colors", () => {
  assert.equal(landmarkSide(0), "center");
  assert.equal(landmarkSide(11), "left");
  assert.equal(landmarkSide(12), "right");
  assert.equal(boneColor(11, 13), COLORS.left);
  assert.equal(boneColor(12, 14), COLORS.right);
  assert.equal(boneColor(11, 12), COLORS.center);
});

test("joint zones identify extended/deep angles and invalid measurements", () => {
  assert.equal(jointZone(170), "ok");
  assert.equal(jointZone(90), "ok");
  assert.equal(jointZone(120), "warn");
  assert.equal(jointZone(Number.NaN), "none");
});

test("knee valgus heuristic detects inward knees relative to ankle width", () => {
  const point = x => ({x});
  assert.equal(kneeValgus(point(0.45), point(0.55), point(0.3), point(0.7)), true);
  assert.equal(kneeValgus(point(0.3), point(0.7), point(0.3), point(0.7)), false);
  assert.equal(kneeValgus(null, point(0.55), point(0.3), point(0.7)), false);
});

test("One-Euro filter damps jitter and follows a steady movement", () => {
  const filter = createOneEuro();
  const samples = [];
  for (let index = 0; index < 60; index++) {
    samples.push(filter(0.5 + (index % 2 ? 0.01 : -0.01), index / 30));
  }
  assert.ok(Math.max(...samples.slice(30)) - Math.min(...samples.slice(30)) < 0.01);

  const moving = createOneEuro();
  let value = 0;
  for (let index = 0; index < 30; index++) value = moving(index / 30, index / 30);
  assert.ok(Math.abs(value - 29 / 30) < 0.15);
});

test("landmark smoother resets a missing point before it returns", () => {
  const smoother = createLandmarkSmoother();
  const first = smoother.smooth([{x: 0.1, y: 0.2, visibility: 1}], 0);
  assert.deepEqual(first, [{x: 0.1, y: 0.2, visibility: 1}]);
  smoother.smooth([null], 0.1);
  const returned = smoother.smooth([{x: 0.9, y: 0.8, visibility: 1}], 0.2);
  assert.deepEqual(returned, [{x: 0.9, y: 0.8, visibility: 1}]);
});

test("FPS statistics keep a rolling mean and minimum", () => {
  const stats = createFpsStats(3);
  [30, 28, 29, 27].forEach(value => stats.add(value));
  assert.equal(stats.min, 27);
  assert.ok(Math.abs(stats.avg - 28) < 1e-9);
  assert.match(formatFps(stats, 23.6), /FPS: 28\.0 \(min 27\.0\).*24 ms/);
});
