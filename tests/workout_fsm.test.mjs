import assert from "node:assert/strict";
import test from "node:test";

import {TimedGesture, WorkoutFSM} from "../assets/webcam/workout_fsm.mjs";

const tracked = extra => ({
  tracked: true,
  head_visible: true,
  start_detected: false,
  x_detected: false,
  knee_angle: null,
  ...extra
});

function startWorkout(workout) {
  workout.update(tracked({start_detected: true}), 0);
  return workout.update(tracked({start_detected: true}), 1500);
}

test("gesture dwell uses elapsed milliseconds and tolerates a short tracking gap", () => {
  const gesture = new TimedGesture();
  assert.equal(gesture.update(true, 0).triggered, false);
  assert.equal(gesture.update(true, 1200).triggered, false);
  assert.equal(gesture.update(false, 1300).triggered, false);
  assert.equal(gesture.update(true, 1500).heldMs, 1300);
  assert.equal(gesture.update(true, 1700).triggered, true);
});

test("gesture dwell resets after tracking is lost longer than grace", () => {
  const gesture = new TimedGesture();
  gesture.update(true, 0);
  gesture.update(true, 500);
  gesture.update(false, 600);
  assert.equal(gesture.update(false, 851).heldMs, 0);
  assert.equal(gesture.update(true, 900).heldMs, 0);
});

test("start, completed squat, and end-set events carry semantic results", () => {
  const workout = new WorkoutFSM({
    exercises: [{name: "Squat", sets: 2, target_reps: 1, rest_seconds: 2, tracks_squat: true}]
  });
  const started = startWorkout(workout);
  assert.equal(started.events[0].type, "START_EXERCISE");
  assert.equal(started.view.phase, "ACTIVE");

  const events = [];
  for (const [index, angle] of [170, 145, 90, 120, 165].entries()) {
    events.push(...workout.update(tracked({knee_angle: angle}), 1600 + index * 100).events);
  }
  assert.deepEqual(events.filter(event => event.type === "REP_COMPLETED").map(event => event.rep_count), [1]);

  workout.update(tracked({x_detected: true}), 2200);
  const ended = workout.update(tracked({x_detected: true}), 3700);
  const endSet = ended.events.find(event => event.type === "END_SET");
  assert.equal(endSet.reps, 1);
  assert.equal(endSet.rest_seconds, 2);
  assert.equal(ended.view.phase, "RESTING");
});

test("rest completion advances the set and resets the X gesture", () => {
  const workout = new WorkoutFSM({
    exercises: [{name: "Squat", sets: 2, rest_seconds: 1, tracks_squat: true}]
  });
  startWorkout(workout);
  workout.update(tracked({x_detected: true}), 1600);
  workout.update(tracked({x_detected: true}), 3100);
  assert.equal(workout.update(tracked(), 4099).view.phase, "RESTING");
  const nextSet = workout.update(tracked(), 4100);
  assert.equal(nextSet.view.phase, "ACTIVE");
  assert.equal(nextSet.view.set_number, 2);
  assert.ok(nextSet.events.some(event => event.type === "REST_COMPLETE"));
});

test("completed exercise waits for start before the next exercise", () => {
  const workout = new WorkoutFSM({
    exercises: [
      {name: "Squat", sets: 1, rest_seconds: 1, tracks_squat: true},
      {name: "Push-up", sets: 1, rest_seconds: 1}
    ]
  });
  startWorkout(workout);
  workout.update(tracked({x_detected: true}), 1600);
  workout.update(tracked({x_detected: true}), 3100);
  const next = workout.update(tracked(), 4100);
  assert.equal(next.view.phase, "WAITING_FOR_START");
  assert.equal(next.view.exercise_name, "Push-up");
  assert.ok(next.events.some(event => event.type === "EXERCISE_READY"));
});

test("tracking loss forces the squat counter to wait for upright posture", () => {
  const workout = new WorkoutFSM({
    exercises: [{name: "Squat", sets: 1, rest_seconds: 1, tracks_squat: true}]
  });
  startWorkout(workout);
  for (const [index, angle] of [170, 145, 90].entries()) {
    workout.update(tracked({knee_angle: angle}), 1600 + index * 100);
  }
  workout.update({tracked: false}, 1900);
  workout.update(tracked({knee_angle: 165}), 2000);
  assert.equal(workout.view(2000).reps, 0);
  assert.equal(workout.view(2000).rep_state, "UP");
});

test("brief tracking flicker does not emit repeated Streamlit events", () => {
  const workout = new WorkoutFSM({
    exercises: [{name: "Squat", sets: 1, rest_seconds: 1, tracks_squat: true}]
  });
  assert.ok(workout.update(tracked(), 0).events.some(event => event.type === "TRACKING_RESTORED"));
  assert.deepEqual(workout.update({tracked: false}, 100).events, []);
  assert.deepEqual(workout.update(tracked(), 200).events, []);
  assert.ok(workout.update({tracked: false}, 300).events.length === 0);
  assert.ok(workout.update({tracked: false}, 551).events.some(event => event.type === "TRACKING_LOST"));
});
