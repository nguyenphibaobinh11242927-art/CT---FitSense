import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import {runInNewContext} from "node:vm";

function workoutView({voices = [], sendAngle} = {}) {
  const speech = [], cues = [], calls = [];
  const voice = {
    enabled: true,
    receive(event) { cues.push(event); },
    stop() { calls.push("stop"); },
  };
  const source = readFileSync(new URL("../frontend/js/views/workout.js", import.meta.url), "utf8")
    .replace(/^import .*;\r?$/gm, "").replace("export const WorkoutView", "const WorkoutView");
  const view = runInNewContext(source + "\nWorkoutView", {
    API: {session: {sendAngle}},
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
