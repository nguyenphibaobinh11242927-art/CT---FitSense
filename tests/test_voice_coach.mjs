import assert from "node:assert/strict";
import test from "node:test";
import {createVoiceCoach} from "../assets/webcam/voice_coach.mjs";

const vietnamese = {lang: "vi-VN", localService: true};

function setup(voices = [vietnamese]) {
  const spoken = [], cues = [], status = [];
  let cancellations = 0;
  const coach = createVoiceCoach({
    synthesis: {
      getVoices: () => voices,
      speak: utterance => spoken.push(utterance),
      cancel: () => { cancellations++; },
    },
    Utterance: class { constructor(text) { this.text = text; } },
    showCue: text => cues.push(text),
    showStatus: text => status.push(text),
    now: () => 250,
  });
  return {coach, spoken, cues, status, cancelled: () => cancellations};
}

test("reads reps and corrections immediately using the local Vietnamese voice", () => {
  const {coach, spoken, cues, status, cancelled} = setup([
    {lang: "en-US", localService: true}, {lang: "vi-VN", localService: false}, vietnamese,
  ]);
  coach.receive({kind: "rep", count: 1});
  assert.deepEqual(cues, ["Một"]);
  assert.equal(spoken.length, 0);

  coach.toggle();
  coach.receive({kind: "rep", count: 2, captured_at: 100});
  assert.equal(spoken[1].text, "Hai");
  assert.equal(spoken[1].voice, vietnamese);
  spoken[1].onstart();
  assert.match(status.at(-1), /150 ms/);

  coach.receive({kind: "shallow_squat"});
  assert.match(spoken[2].text, /Hạ thấp hơn/);
  assert.equal(cancelled(), 2);
  coach.stop();
  assert.equal(cancelled(), 3);
  coach.toggle();
  coach.receive({kind: "rep", count: 3});
  assert.equal(spoken.length, 3);
});

test("shows cues and an explanation when Vietnamese speech is unavailable", () => {
  const {coach, spoken, cues, status} = setup([{lang: "en-US"}]);
  coach.toggle();
  coach.receive({kind: "rep", count: 3});
  coach.receive({kind: "rep", count: 0});
  assert.deepEqual(cues, ["Ba"]);
  assert.equal(spoken.length, 0);
  assert.match(status.at(-1), /Chưa có giọng tiếng Việt/);
});
