import assert from "node:assert/strict";
import test from "node:test";
import {createVoiceCommands, matchVoiceCommand} from "../frontend/js/voice_commands.mjs";

test("recognizes natural Vietnamese requests with accents, without accents, and with polite phrasing", () => {
  const phrases = {
    start: [
      "Bắt đầu", "Bắt đầu đi", "Tập thôi", "Tiếp tục", "Tập tiếp",
      "FitSense ơi, mình muốn bắt đầu buổi tập nhé!", "CHO MINH TAP TIEP DI", "Vào tập nào",
      "Có thể bắt đầu lại bài tập được không?", "Bắt đầu tập luyện",
    ],
    pause: [
      "Dừng lại", "Dừng", "Ngưng", "Ngừng", "Tạm dừng", "Tạm ngưng", "Thôi tập", "FitSense, thôi",
      "Làm ơn dừng buổi tập này lại", "Tạm dừng tập một chút nhé", "Mình muốn ngưng tập",
    ],
    rest: [
      "Nghỉ hiệp", "Nghỉ giữa hiệp", "Cho nghỉ hiệp", "Cho mình nghỉ một chút nhé",
      "Vui lòng bật đồng hồ nghỉ", "Mở đồng hồ nghỉ giữa hiệp đi", "Bắt đầu nghỉ hiệp này",
      "Nghỉ xíu nha", "Cho em nghỉ một lát được không?",
    ],
    next: [
      "Bài tiếp theo", "Bài kế tiếp", "Qua bài", "Chuyển bài", "Đổi qua bài sau",
      "Giúp mình chuyển sang bài tập tiếp theo nhé", "Capy ơi, sang động tác tiếp theo",
      "Bỏ qua bài này giúp mình", "Sang bài kế nha",
    ],
  };
  for (const [command, variants] of Object.entries(phrases)) {
    for (const phrase of variants) {
      assert.equal(matchVoiceCommand(phrase.normalize("NFD")), command, phrase);
    }
  }
});

test("ignores ambiguous, negated, quoted, and combined commands", () => {
  for (const phrase of [
    "Thôi", "Nghỉ", "Tiếp", "Đừng dừng lại", "Mình chưa muốn bắt đầu",
    "Mình không muốn chuyển bài", "Đừng nghỉ giữa hiệp nhé", "Cô ấy bảo dừng",
    "Dừng hay tập tiếp?", "Nghỉ hiệp rồi qua bài", "Bỏ dở buổi tập", "Bài tiếp theo là gì?",
  ]) {
    assert.equal(matchVoiceCommand(phrase), undefined, phrase);
  }
});

function recognitionHarness() {
  const attempts = [], commands = [], statuses = [], timers = new Set();
  const controller = createVoiceCommands({
    SpeechRecognition: class {
      constructor() { attempts.push(this); }
      start() { this.onstart(); }
      abort() { this.aborted = true; }
      say(...utterances) {
        const results = utterances.map(({transcript, isFinal = true}) => ({isFinal, 0: {transcript}}));
        this.onresult({resultIndex: 0, results});
      }
    },
    onCommand: command => commands.push(command),
    onStatus: message => statuses.push(message),
    onEnabledChange() {},
    schedule(callback) { timers.add(callback); return callback; },
    cancel(callback) { timers.delete(callback); },
  });
  function runTimers() {
    for (const timer of [...timers]) {
      timers.delete(timer);
      timer();
    }
  }
  return {controller, attempts, commands, statuses, timers, runTimers};
}

test("listens after opt-in and rejects interim, late, and contradictory speech", () => {
  const {controller, attempts, commands, runTimers} = recognitionHarness();
  assert.equal(attempts.length, 0);
  controller.toggle();
  const first = attempts[0];
  assert.equal(first.lang, "vi-VN");
  assert.equal(first.interimResults, false);
  first.say({transcript: "Dừng lại", isFinal: false});
  first.say({transcript: "Dừng lại"}, {transcript: "Tập tiếp"});
  first.say({transcript: "Bắt đầu đi"});
  assert.deepEqual(commands, ["start"]);

  controller.setBlocked("FitSense đang phát âm thanh");
  assert.equal(first.aborted, true);
  first.say({transcript: "Bài tiếp theo"});
  first.onend();
  runTimers();
  assert.equal(attempts.length, 1);

  controller.setBlocked();
  assert.equal(attempts.length, 1);
  runTimers();
  assert.equal(attempts.length, 2);
  first.say({transcript: "Dừng lại"});
  attempts[1].say({transcript: "Thôi tập"});
  controller.stop();
  attempts[1].say({transcript: "Bài tiếp theo"});
  attempts[1].onend();
  runTimers();
  assert.deepEqual(commands, ["start", "pause"]);
  assert.equal(attempts.length, 2);
});

test("restarts after silence but requires opt-in after a microphone permission error", () => {
  const {controller, attempts, statuses, timers, runTimers} = recognitionHarness();
  controller.toggle();
  attempts[0].onerror({error: "no-speech"});
  attempts[0].onend();
  runTimers();
  assert.equal(attempts.length, 2);
  attempts[1].onerror({error: "not-allowed"});
  attempts[1].onend();
  assert.equal(controller.enabled, false);
  assert.match(statuses.at(-1), /cấp quyền micro/);
  assert.equal(timers.size, 0);
  controller.toggle();
  assert.equal(attempts.length, 3);
});
