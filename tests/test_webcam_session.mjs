import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import test from "node:test";
import {runInNewContext} from "node:vm";
import {createFrameBatchFilter} from "../assets/webcam/frame_batching.mjs";

test("webcam pauses a stalled stream and resumes with the same session sequence", async () => {
  const messages = [], heard = [];
  const parent = {postMessage(message) { messages.push(structuredClone(message)); }};
  const origin = "http://localhost:8501";
  let renderListener, animation, videoFrame, updateSpeaker, now = 0;
  const win = {parent, addEventListener(type, listener) {
    if (type === "message") renderListener = listener;
  }};
  const nodes = new Map();
  const element = id => {
    if (!nodes.has(id)) nodes.set(id, {
      style: {}, disabled: true, value: "",
      getContext: () => ({drawImage() {}, clearRect() {}, beginPath() {}, arc() {}, fill() {}}),
      appendChild: node => node,
      setAttribute(name, value) { this[name] = value; }, async play() {},
    });
    return nodes.get(id);
  };
  const video = element("input");
  Object.assign(video, {
    readyState: 2, currentTime: 0, videoWidth: 640, videoHeight: 480,
    requestVideoFrameCallback(callback) { videoFrame = callback; return 1; },
    cancelVideoFrameCallback() { videoFrame = null; },
  });
  const track = {stop() {}};
  const landmarks = [];
  landmarks[23] = {x: .5, y: .4, visibility: 1};
  landmarks[25] = {x: .5, y: .6, visibility: 1};
  landmarks[27] = {x: .5, y: .8, visibility: 1};
  const fakeMediaPipe = {
    FilesetResolver: {async forVisionTasks() {}},
    PoseLandmarker: {POSE_CONNECTIONS: [], async createFromOptions() {
      return {detectForVideo: () => ({landmarks: [landmarks]}), close() {}};
    }},
  };
  // Run the browser entry point against stand-ins for hardware and MediaPipe.
  const source = readFileSync(new URL("../assets/webcam/webcam.mjs", import.meta.url), "utf8")
    .replace(/^import \{createVoiceCoach\}[^\n]+\n/, "")
    .replace(/^import \{createFrameBatchFilter\}[^\n]+\n/, "")
    .replace('await import("./vendor/mediapipe/vision_bundle.mjs")', "fakeMediaPipe");
  runInNewContext(source, {
    window: win, parent, location: {origin, href: origin}, fakeMediaPipe,
    navigator: {mediaDevices: {addEventListener() {}, async getUserMedia() {
      return {getTracks: () => [track], getVideoTracks: () => [track]};
    }}},
    document: {getElementById: element, createElement: () => ({}), body: {}},
    createVoiceCoach: ({onEnabledChange}) => {
      updateSpeaker = onEnabledChange;
      return {supported: true, stop() { heard.push("stop"); }, receiveBatch(events) { heard.push(...events); }};
    },
    createFrameBatchFilter,
    ResizeObserver: class {observe() {}}, URL, atob, setTimeout, clearTimeout,
    performance: {now: () => now}, cancelAnimationFrame() {},
    requestAnimationFrame(callback) { animation = callback; return 1; },
  });
  const render = args => renderListener({source: parent, origin,
    data: {type: "streamlit:render", args: {session_id: "workout", ...args}}});
  const batches = () => messages.filter(message => message.type === "streamlit:setComponentValue")
    .map(message => message.value);
  const tick = (at, presentedFrames) => {
    now = at;
    video.currentTime = at / 1000;
    if (presentedFrames) videoFrame(at, {presentedFrames});
    animation(at);
  };

  render({model: "dGVzdA==", last_event_id: 8});
  updateSpeaker(true);
  assert.equal(element("voice-icon").textContent, "🔊");
  assert.equal(element("voice")["aria-pressed"], "true");
  updateSpeaker(false);
  assert.equal(element("voice-icon").textContent, "🔇");
  assert.equal(element("voice")["aria-pressed"], "false");
  await element("camera-toggle").onclick();
  const opened = batches().at(-1);
  assert.equal(opened.session_id, "workout");
  assert.equal(typeof opened.stream_id, "string");
  assert.equal(opened.sequence, 9);
  assert.equal(opened.frames[0].knee_angle, null);
  assert.equal(opened.frames[0].tracking_interrupted, true);
  assert.deepEqual(heard.splice(0), ["stop"]);
  render({last_event_id: 9});

  tick(200, 1);
  const frame = batches().at(-1);
  assert.equal(frame.sequence, 10);
  assert.equal(frame.frames.length, 1);
  assert.equal(frame.frames[0].knee_angle, 180);
  assert.equal(frame.frames[0].captured_at, 200);
  const feedback = {...frame, events: [{kind: "rep", count: 1}, {kind: "shallow_squat", frame_sequence: 10}]};
  render({last_event_id: 10, voice_feedback: {...feedback, stream_id: "previous-camera"}});
  assert.equal(heard.length, 0);
  render({last_event_id: 10, voice_feedback: feedback});
  render({last_event_id: 10, voice_feedback: feedback});
  assert.deepEqual(heard, feedback.events);

  tick(799);
  assert.equal(batches().at(-1).sequence, 10);
  tick(800);
  assert.equal(batches().at(-1).sequence, 11);
  assert.equal(batches().at(-1).frames[0].knee_angle, null);
  assert.equal(batches().at(-1).frames[0].tracking_interrupted, true);
  tick(900);
  assert.equal(batches().at(-1).sequence, 11);

  tick(1000, 2);
  const resumed = batches().at(-1);
  assert.equal(resumed.sequence, 12);
  assert.equal(resumed.stream_id, opened.stream_id);
  assert.deepEqual(resumed.frames.map(sample => sample.knee_angle), [null, 180]);

  tick(1200, 3);
  assert.equal(batches().at(-1).sequence, 12);
  render({last_event_id: 12, voice_feedback: {
    ...resumed, interrupted: true, stopped: false, events: [{kind: "rep", count: 2}],
  }});
  assert.deepEqual(heard, [...feedback.events, "stop", "stop", {kind: "rep", count: 2}]);

  tick(1400, 4);
  assert.equal(batches().at(-1).sequence, 12);
  tick(1900, 5);
  assert.equal(batches().at(-1).sequence, 12);
  tick(2000, 6);
  assert.equal(batches().at(-1).sequence, 13);
  assert.deepEqual(batches().at(-1).frames.map(sample => sample.knee_angle), [180]);
  await element("camera-toggle").onclick();
  assert.equal(batches().at(-1).sequence, 14);
  assert.equal(batches().at(-1).frames.at(-1).knee_angle, null);
  assert.equal(batches().at(-1).frames.at(-1).tracking_interrupted, true);
  assert.equal(videoFrame, null);
});
