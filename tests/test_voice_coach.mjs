import assert from "node:assert/strict";
import test from "node:test";
import {createVoiceCoach} from "../assets/webcam/voice_coach.mjs";
import {VI_CUES} from "../assets/webcam/voice/vi_cues.mjs";

const flush = () => new Promise(resolve => setImmediate(resolve));

function setup(response) {
  const played = [], cues = [], status = [], calls = [], enabledStates = [], corrections = [];
  let now = 250;
  const coach = createVoiceCoach({
    AudioContext: class {
      state = "suspended";
      currentTime = 3;
      resume() { this.state = "running"; calls.push("resume"); }
      decodeAudioData() { calls.push("decode"); return {}; }
      createBufferSource() {
        return {
          connect() {}, disconnect() {},
          start(...args) { this.args = args; played.push(this); },
          stop() { this.stopped = true; },
        };
      }
    },
    fetchAudio: async url => {
      assert.match(url.pathname, /\/voice\/vi\.mp3$/);
      calls.push("fetch");
      return response?.() ?? {ok: true, arrayBuffer: () => new ArrayBuffer(1)};
    },
    showCue: text => cues.push(text),
    showStatus: text => status.push(text),
    onEnabledChange: enabled => enabledStates.push(enabled),
    onCorrection: (event, decision) => corrections.push([event.frame_sequence, decision]),
    now: () => now,
  });
  return {coach, played, cues, status, calls, enabledStates, corrections, advance(ms) { now += ms; }};
}

test("plays Vietnamese rep and form clips with only one audio download", async () => {
  const {coach, played, cues, status, calls} = setup();
  coach.receive({kind: "rep", count: 1});
  assert.deepEqual(cues, []);
  assert.deepEqual(calls, []);

  coach.toggle();
  assert.deepEqual(calls, ["resume", "fetch"]);
  await flush();
  assert.deepEqual(played[0].args, [3, ...VI_CUES[101]]);
  played[0].onended();

  coach.receive({kind: "rep", count: 2, captured_at: 100});
  await flush();
  assert.deepEqual(played[1].args, [3, ...VI_CUES[2]]);
  assert.match(status.at(-1), /150 ms/);
  assert.ok(cues.every(cue => cue === ""));

  coach.receive({kind: "shallow_squat"});
  await flush();
  assert.equal(played.length, 2);
  assert.equal(played[1].stopped, undefined);
  played[1].onended();
  await flush();
  assert.deepEqual(played[2].args, [3, ...VI_CUES[102]]);
  assert.match(cues.at(-1), /Hạ thấp hơn/);
  assert.deepEqual(calls, ["resume", "fetch", "decode"]);
});

test("reads counts past 100 digit by digit and stops all clips when muted", async () => {
  const {coach, played, cues} = setup();
  coach.toggle();
  await flush();
  played.shift().onended();
  coach.receive({kind: "rep", count: 105});
  await flush();
  assert.deepEqual(played.map(source => source.args.slice(1)), [VI_CUES[1], VI_CUES[0], VI_CUES[5]]);
  assert.ok(played[1].args[0] > played[0].args[0]);
  coach.toggle();
  assert.ok(played.every(source => source.stopped));
  coach.receive({kind: "rep", count: 3});
  await flush();
  assert.ok(cues.every(cue => cue === ""));
  assert.equal(played.length, 3);
});

test("finishes the current rep and keeps only the most recent pending count", async () => {
  const {coach, played} = setup();
  coach.toggle();
  await flush();
  played.shift().onended();
  coach.receive({kind: "rep", count: 1});
  await flush();
  coach.receive({kind: "shallow_squat"});
  coach.receive({kind: "rep", count: 2});
  coach.receive({kind: "rep", count: 3});
  await flush();
  assert.equal(played.length, 1);
  assert.equal(played[0].stopped, undefined);
  played[0].onended();
  await flush();
  assert.deepEqual(played[1].args, [3, ...VI_CUES[3]]);
  played[1].onended();
  await flush();
  assert.equal(played.length, 2);
});

test("shows a playback error and retries the download when re-enabled", async () => {
  let available = false;
  const {coach, played, status, calls, enabledStates} = setup(() => ({
    ok: available, arrayBuffer: () => new ArrayBuffer(1),
  }));
  coach.toggle();
  await flush();
  assert.match(status.at(-1), /Không phát được âm thanh/);
  assert.equal(coach.enabled, false);
  assert.deepEqual(enabledStates, [true, false]);
  available = true;
  coach.toggle();
  await flush();
  assert.deepEqual(enabledStates, [true, false, true]);
  assert.equal(played.length, 1);
  assert.equal(calls.filter(call => call === "fetch").length, 2);
});

test("logs each shallow squat, skips cues inside 3.5 seconds, and drops stale cues", async () => {
  const {coach, played, corrections, advance} = setup();
  coach.toggle();
  await flush();
  played.shift().onended();
  const squat = frame => coach.receive({kind: "shallow_squat", frame_sequence: frame});

  squat(1);
  await flush();
  played[0].onended();
  advance(3499);
  squat(2);
  await flush();
  assert.equal(played.length, 1);
  advance(1);
  squat(3);
  await flush();
  assert.equal(played.length, 2);
  played[1].onended();

  advance(3500);
  coach.receive({kind: "rep", count: 1});
  await flush();
  squat(4);
  advance(1000);
  played[2].onended();
  await flush();
  assert.equal(played.length, 3);
  assert.deepEqual(corrections, [
    [1, "detected"], [1, "scheduled"], [2, "detected"], [2, "cooldown"],
    [3, "detected"], [3, "scheduled"], [4, "detected"], [4, "waiting"], [4, "expired"],
  ]);
});
