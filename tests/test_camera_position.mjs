import assert from "node:assert/strict";
import test from "node:test";
import {assessCameraPosition, createCameraPositionMonitor} from "../frontend/js/camera_position.mjs";

function pose({front = false, close = false} = {}) {
  const points = [];
  const left = front ? 0.42 : 0.49, right = front ? 0.58 : 0.51;
  const hipLeft = front ? 0.45 : 0.49, hipRight = front ? 0.55 : 0.51;
  const add = (index, x, y) => { points[index] = {x, y, visibility: 0.99}; };
  add(11, left, close ? 0.12 : 0.27);
  add(12, right, close ? 0.12 : 0.27);
  add(23, hipLeft, close ? 0.8 : 0.57);
  add(24, hipRight, close ? 0.8 : 0.57);
  for (const [index, x, y] of [[25, hipLeft, .75], [26, hipRight, .75], [27, hipLeft, .92], [28, hipRight, .92],
    [13, left, .45], [14, right, .45], [15, left, .6], [16, right, .6]]) add(index, x, y);
  return points;
}

test("distinguishes close, frontal and usable side-view framing", () => {
  assert.equal(assessCameraPosition(pose({close: true}), "squat", 640, 480), "too_close");
  assert.equal(assessCameraPosition(pose({front: true}), "squat", 640, 480), "wrong_angle");
  assert.equal(assessCameraPosition(pose(), "squat", 640, 480), null);
  assert.equal(assessCameraPosition(pose({front: true}), "calf_raise", 640, 480), null);
  assert.equal(assessCameraPosition(null, "squat", 640, 480), null);
  const missing = pose();
  missing[27].visibility = missing[28].visibility = .1;
  assert.equal(assessCameraPosition(missing, "squat", 640, 480), "incomplete");
  const upper = pose();
  delete upper[27]; delete upper[28];
  assert.equal(assessCameraPosition(upper, "wall_push_up", 640, 480), null);
  assert.equal(assessCameraPosition(upper, "squat", 640, 480), "incomplete");
});

test("handles cropped torsos and horizontal push-ups in a wide frame", () => {
  const cropped = pose();
  delete cropped[23];
  delete cropped[24];
  assert.equal(assessCameraPosition(cropped, "squat", 640, 480), "incomplete");
  cropped[11].x = .1;
  cropped[12].x = .9;
  assert.equal(assessCameraPosition(cropped, "squat", 640, 480), "too_close");

  const horizontal = pose();
  horizontal[11] = {x: .3, y: .35, visibility: .99};
  horizontal[12] = {x: .31, y: .36, visibility: .99};
  horizontal[23] = {x: .7, y: .35, visibility: .99};
  horizontal[24] = {x: .71, y: .36, visibility: .99};
  assert.equal(assessCameraPosition(horizontal, "push_up", 1920, 1080), null);
});

test("settles warnings, enforces a shared twelve-second interval, and clears after recovery", () => {
  const notices = [], reminders = [];
  let now = 0;
  const monitor = createCameraPositionMonitor({
    onChange: warning => notices.push(warning),
    remind: warning => { reminders.push([warning, now]); return true; },
  });
  function update(points, until) {
    for (; now <= until; now += 100) monitor.update(points, "squat", 640, 480, now);
  }
  update(pose({close: true}), 1400);
  assert.deepEqual(notices, []);
  update(pose({close: true}), 1500);
  assert.deepEqual(reminders, [["too_close", 1500]]);
  update(pose({front: true}), 13400);
  assert.deepEqual(notices, ["too_close", "wrong_angle"]);
  assert.equal(reminders.length, 1);
  update(pose({front: true}), 13500);
  assert.deepEqual(reminders[1], ["wrong_angle", 13500]);
  update(pose(), 14400);
  assert.equal(notices.at(-1), null);
  monitor.reset();
  update(pose({close: true}), 16400);
  assert.equal(reminders.length, 2);
});

test("retries when the speaker is available without consuming the reminder interval", () => {
  let ready = false, attempts = 0;
  const monitor = createCameraPositionMonitor({onChange() {}, remind() { attempts++; return ready; }});
  const points = pose({close: true});
  for (let now = 0; now <= 1500; now += 100) monitor.update(points, "squat", 640, 480, now);
  assert.equal(attempts, 1);
  ready = true;
  monitor.update(points, "squat", 640, 480, 1600);
  monitor.update(points, "squat", 640, 480, 1700);
  assert.equal(attempts, 2);
});
