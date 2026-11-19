import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import {runInNewContext} from "node:vm";

function workoutView({voices = [], sendAngle, sessionApi = {}} = {}) {
  const speech = [], cues = [], calls = [];
  const voice = {
    enabled: true,
    receive(event) { cues.push(event); },
    stop() { calls.push("stop"); },
  };
  const source = readFileSync(new URL("../frontend/js/views/workout.js", import.meta.url), "utf8")
    .replace(/^import .*;\r?$/gm, "").replace("export const WorkoutView", "const WorkoutView");
  const view = runInNewContext(source + "\nWorkoutView", {
    API: {session: {sendAngle, ...sessionApi}},
    Toast: {success() {}, error() {}},
    clearTimeout,
    clearInterval,
    structuredClone,
    document: {getElementById: () => null},
    window: {speechSynthesis: {
      getVoices: () => voices,
      cancel() { calls.push("cancel"); },
      speak(utterance) { speech.push(utterance); },
    }},
    SpeechSynthesisUtterance: class { constructor(text) { this.text = text; } },
  });
  view.voiceCoach = voice;
  return {view, speech, cues, calls};
}

test("SPA never uses the default browser voice when Vietnamese is unavailable", () => {
  const voices = [{lang: "en-US", default: true}];
  const {view, speech, cues, calls} = workoutView({voices});
  view.speak("Bắt đầu!");
  assert.equal(speech.length, 0);
  const vietnamese = {lang: "vi-VN"};
  voices.push(vietnamese);
  view.speak("Bắt đầu!");
  assert.equal(speech[0].voice, vietnamese);

  const rep = {kind: "rep", count: 2};
  view.playVoiceEvent(rep);
  assert.deepEqual(cues, [rep]);
  assert.deepEqual(calls, ["cancel"]);
});

test("SPA starts each set with the new set number and ignores feedback from the previous set", async () => {
  const requests = [];
  const {view, cues} = workoutView({
    sendAngle: (...args) => new Promise(resolve => requests.push({args, resolve})),
  });
  Object.assign(view, {
    isWorkingOut: true, sessionId: "test-session", currentSet: 1, totalSets: 2,
    updateHUDDisplay() {}, updateSetsDisplay() {}, renderUpNextListUI() {},
    startRestTimer() { this.isResting = true; },
  });
  view.dispatchAngleToFSM(170, 0);
  assert.equal(requests[0].args[4], 1);
  view.completeCurrentSet();
  assert.equal(view.currentSet, 2);
  assert.equal(view.dispatchAngleToFSM(170, 50), false);
  requests[0].resolve({rep_count: 12, voice_event: {kind: "rep", count: 12}});
  await view.poseRequest;
  assert.equal(view.repCount, 0);
  assert.equal(cues.length, 0);

  view.finishRestPeriod();
  view.dispatchAngleToFSM(170, 100);
  assert.equal(requests[1].args[4], 2);
  requests[1].resolve({rep_count: 0});
  await view.poseRequest;
});

test("SPA plays a shallow-squat event without a counted rep and ignores an old response after pausing", async () => {
  let finish;
  const {view, cues, calls} = workoutView({sendAngle: () => new Promise(resolve => { finish = resolve; })});
  view.isWorkingOut = true;
  view.sessionId = "test-session";
  view.updateHUDDisplay = () => {};
  const event = {kind: "shallow_squat"};
  assert.ok(view.dispatchAngleToFSM(165, 123));
  finish({rep_count: 0, rep_incremented: false, voice_event: event});
  await view.poseRequest;
  assert.equal(cues.length, 1);
  assert.equal(cues[0].kind, event.kind);
  assert.equal(cues[0].captured_at, 123);

  assert.ok(view.dispatchAngleToFSM(165, 200));
  const old = view.poseRequest;
  view.isWorkingOut = false;
  view.resetPoseFeedback();
  finish({rep_count: 1, rep_incremented: true, voice_event: {kind: "rep", count: 1}});
  await old;
  await new Promise(resolve => setImmediate(resolve));
  finish({rep_count: 1, state: "WAITING_FOR_UP"});
  await view.poseRequest;
  assert.equal(view.repCount, 1);
  assert.equal(cues.length, 1);
  assert.deepEqual(calls, ["stop"]);
});

test("SPA stops audio once when tracking is lost so later camera guidance can finish", async () => {
  let trackingLost = true;
  const {view, calls} = workoutView({sendAngle: async () => ({rep_count: 0, tracking_lost: trackingLost})});
  view.isWorkingOut = true;
  view.sessionId = "test-session";
  view.updateHUDDisplay = () => {};
  for (let frame = 0; frame < 3; frame++) {
    view.dispatchAngleToFSM(null, frame);
    await view.poseRequest;
  }
  assert.deepEqual(calls, ["stop"]);
  trackingLost = false;
  view.dispatchAngleToFSM(165, 4);
  await view.poseRequest;
  trackingLost = true;
  view.dispatchAngleToFSM(null, 5);
  await view.poseRequest;
  assert.deepEqual(calls, ["stop", "stop"]);
});

test("AI and manual modes keep independent sessions and counters", async () => {
  const pauses = [];
  const {view} = workoutView({sessionApi: {
    start: async (...args) => ({session_id: args[6].mode + "-session"}),
    setPaused: async (id, paused) => {
      pauses.push([id, paused]);
      return {current_set: 1, exercise_index: 0, rep_count: 6};
    },
  }});
  Object.assign(view, {
    sessionId: "ai-session", repCount: 6, currentSet: 1, isWorkingOut: true,
    stopVideoSource() { this.videoSourceType = "none"; },
    updateSetsDisplay() {}, renderUpNextListUI() {},
  });
  assert.equal(view.changeManualReps(1), false);
  assert.equal(view.repCount, 6);
  assert.equal(await view.selectWorkoutMode("manual"), true);
  assert.equal(view.sessionId, "manual-session");
  assert.equal(view.repCount, 0);
  view.isWorkingOut = true;
  assert.ok(view.changeManualReps(1));
  assert.equal(view.dispatchAngleToFSM(170, 0), false);
  assert.equal(view.repCount, 1);
  assert.equal(await view.selectWorkoutMode("ai"), true);
  assert.equal(view.sessionId, "ai-session");
  assert.equal(view.repCount, 6);
  assert.equal(await view.selectWorkoutMode("manual"), true);
  assert.equal(view.sessionId, "manual-session");
  assert.equal(view.repCount, 1);
  assert.deepEqual(pauses, [["ai-session", true], ["manual-session", true], ["ai-session", true]]);
});

test("AI needs a visible in-frame joint chain even during the warning delay", () => {
  const {view} = workoutView();
  const pose = Array(33).fill(null);
  pose[23] = {x: 0.5, y: 0.3, visibility: 0.95};
  pose[25] = {x: 0.5, y: 0.5, visibility: 0.95};
  pose[27] = {x: 0.5, y: 0.7, visibility: 0.95};
  assert.equal(view.measureTrackedAngle(pose, 640, 480, false), 180);
  pose[25].visibility = 0.4;
  assert.equal(view.measureTrackedAngle(pose, 640, 480, false), null);
  pose[25].visibility = 0.95;
  pose[27].y = 1.1;
  assert.equal(view.measureTrackedAngle(pose, 640, 480, false), null);
});

test("AI completion preview uses the server total across sets", async () => {
  const {view} = workoutView({sessionApi: {
    summary: async () => ({total_reps: 24}),
  }});
  Object.assign(view, {
    sessionId: "ai-session", repCount: 12,
    leave: async () => true,
    openRPEEvaluationModal(reps) { this.previewReps = reps; },
  });
  await view.finishWorkout();
  assert.equal(view.previewReps, 24);
});
