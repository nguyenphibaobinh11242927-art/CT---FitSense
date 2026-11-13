import assert from "node:assert/strict";
import test from "node:test";

import {createFrameBatchFilter} from "../assets/webcam/frame_batching.mjs";

const standing = {head_detected: true, knee_angle: 170, start_detected: false, x_detected: false};

test("sends an initial frame, then batches only meaningful knee movement", () => {
  const filter = createFrameBatchFilter();
  assert.equal(filter.shouldQueue(standing, 0), true);
  filter.noteQueued(standing, 0);

  assert.equal(filter.shouldQueue({...standing, knee_angle: 166}, 50), false);
  assert.equal(filter.shouldQueue({...standing, knee_angle: 165}, 100), false);
  assert.equal(filter.shouldQueue({...standing, knee_angle: 164.9}, 150), true);
});

test("samples active gestures and sends one immediate gesture transition", () => {
  const filter = createFrameBatchFilter();
  filter.noteQueued(standing, 0);
  const handRaised = {...standing, start_detected: true};

  assert.equal(filter.shouldQueue(handRaised, 25), true);
  filter.noteQueued(handRaised, 25);
  assert.equal(filter.shouldQueue(handRaised, 74), false);
  assert.equal(filter.shouldQueue(handRaised, 75), true);
  filter.noteQueued(handRaised, 75);
  assert.equal(filter.shouldQueue(standing, 80), true);
});

test("heartbeat and tracking transitions are sent even without pose movement", () => {
  const filter = createFrameBatchFilter();
  filter.noteQueued(standing, 0);
  assert.equal(filter.shouldQueue(standing, 999), false);
  assert.equal(filter.shouldQueue(standing, 1000), true);
  filter.noteQueued(standing, 1000);
  assert.equal(filter.shouldQueue({...standing, knee_angle: null}, 1050), true);
});
