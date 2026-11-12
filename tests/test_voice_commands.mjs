import assert from "node:assert/strict";
import test from "node:test";
import {createVoiceCommands, matchVoiceCommand} from "../assets/webcam/voice_commands.mjs";

test("recognizes Vietnamese variants as whole utterances", () => {
  for (const [command, phrases] of Object.entries({
    start: ["Bắt đầu", "Bắt đầu đi", "Tập thôi", "Tiếp tục", "Tập tiếp"],
    pause: ["Dừng lại", "Dừng", "Ngưng", "Ngừng", "Tạm dừng", "Tạm ngưng", "Thôi tập", "FitSense, thôi", "Fit Sense, thôi"],
    rest: ["Nghỉ hiệp", "Nghỉ giữa hiệp", "Cho nghỉ hiệp"],
    next: ["Bài tiếp theo", "Bài kế tiếp", "Qua bài", "Chuyển bài"],
  })) {
    for (const phrase of phrases) {
      assert.equal(matchVoiceCommand(`  ${phrase.toUpperCase().normalize("NFD")}! `), command, phrase);
    }
  }
  for (const phrase of ["Thôi", "Nghỉ", "Tiếp", "Đừng dừng lại", "Nó bảo dừng", "Dừng hay tập tiếp?"]) {
    assert.equal(matchVoiceCommand(phrase), undefined, phrase);
  }
});

function recognitionHarness() {
  const attempts = [], commands = [], status = [], enabled = [], timers = new Set();
  const controller = createVoiceCommands({
    SpeechRecognition: class {
      constructor() { attempts.push(this); }
      start() { this.onstart(); }
      abort() { this.aborted = true; }
      say(transcript, isFinal = true) {
        this.onresult({resultIndex: 0, results: [{isFinal, 0: {transcript}}]});
      }
    },
    onCommand: command => commands.push(command),
    onStatus: message => status.push(message),
    onEnabledChange: active => enabled.push(active),
    schedule(callback) { timers.add(callback); return callback; },
    cancel(callback) { timers.delete(callback); },
  });
  return {controller, attempts, commands, status, enabled, timers};
}

test("listens after opt-in and discards partial or late speech during coach playback", () => {
  const {controller, attempts, commands, enabled} = recognitionHarness();
  assert.equal(attempts.length, 0);
  controller.toggle();
  const first = attempts[0];
  assert.equal(first.lang, "vi-VN");
  assert.equal(first.interimResults, false);
  first.say("Dừng lại", false);
  first.say("Bắt đầu đi");

  controller.setPlaybackActive(true);
  assert.ok(first.aborted);
  first.say("Dừng lại");
  first.onend();
  assert.equal(attempts.length, 1);
  controller.setPlaybackActive(false);
  assert.equal(attempts.length, 2);
  first.say("Ngưng");
  attempts[1].say("Thôi tập");
  controller.stop();
  attempts[1].say("Bài tiếp theo");
  assert.deepEqual(commands, ["start", "pause"]);
  assert.deepEqual(enabled, [true, false]);
});

test("restarts after silence and turns off after a permission error", () => {
  const {controller, attempts, status, enabled, timers} = recognitionHarness();
  controller.toggle();
  attempts[0].onerror({error: "no-speech"});
  attempts[0].onend();
  const [restart] = timers;
  timers.delete(restart);
  restart();
  attempts[1].onerror({error: "not-allowed"});
  attempts[1].onend();
  assert.deepEqual(enabled, [true, false]);
  assert.match(status.at(-1), /cấp quyền micro/);
  assert.equal(timers.size, 0);
  controller.toggle();
  assert.equal(attempts.length, 3);
});
