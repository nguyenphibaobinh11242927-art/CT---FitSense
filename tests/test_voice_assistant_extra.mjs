import assert from "node:assert/strict";
import test from "node:test";
import {CUES, VoiceAssistant, cleanForSpeech, pickVoice, splitSentences} from "../frontend/js/components/voice_assistant.js";

function make(opts = {}) {
  const log = {statuses: [], transcripts: [], interims: [], listening: [], speaking: [], latencies: [], muted: []};
  const utterances = [], oscillators = [];
  const calls = {cancel: 0, abort: 0, stop: 0};
  let clock = 0;
  class Rec {
    start() { this.onstart?.(); }
    stop() { calls.stop += 1; this.onend?.(); }
    abort() { calls.abort += 1; }
  }
  const synthesis = {
    voices: opts.voices ?? [{lang: "vi-VN"}],
    getVoices() { return this.voices; },
    cancel() { calls.cancel += 1; },
    speak(u) { utterances.push(u); },
  };
  class Utt { constructor(text) { this.text = text; } }
  class Ctx {
    constructor() { this.currentTime = 1; this.state = "suspended"; this.destination = {}; this.baseLatency = 0.01; this.outputLatency = 0.02; }
    resume() { this.state = "running"; }
    close() { this.closed = true; }
    createOscillator() {
      const o = {frequency: {value: 0}, connect: (x) => x, start(t) { o.startAt = t; }, stop(t) { o.stopAt = t; }};
      oscillators.push(o);
      return o;
    }
    createGain() { return {gain: {setValueAtTime() {}, exponentialRampToValueAtTime() {}}, connect: (x) => x}; }
  }
  const store = opts.store ?? new Map();
  const storage = {getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, v)};
  const assistant = new VoiceAssistant({
    Recognition: Rec, synthesis, Utterance: Utt, storage, now: () => clock,
    AudioContext: opts.noAudio ? null : Ctx,
    interimResults: opts.interimResults, maxListenMs: opts.maxListenMs,
    onTranscript: (t) => log.transcripts.push(t),
    onInterim: (t) => log.interims.push(t),
    onStatus: (t) => log.statuses.push(t),
    onListeningChange: (v) => log.listening.push(v),
    onMuteChange: (v) => log.muted.push(v),
    onSpeakingChange: (v) => log.speaking.push(v),
    onLatency: (v) => log.latencies.push(v),
  });
  return {assistant, log, utterances, oscillators, calls, synthesis, store, setClock: (v) => { clock = v; }};
}

test("announces listening and tells the user when nothing was recognised", () => {
  const {assistant, log} = make();
  assistant.toggleListening();
  assert.match(log.statuses.at(-1), /Đang nghe/);
  assistant.recognition.onend();
  assert.match(log.statuses.at(-1), /Chưa nhận được câu nào/);
});

test("a recognised sentence is not followed by the nothing-recognised message", () => {
  const {assistant, log} = make();
  assistant.toggleListening();
  assistant.recognition.onresult({resultIndex: 0, results: [Object.assign([{transcript: "mở lịch tập"}], {isFinal: true})]});
  assistant.recognition.onend();
  assert.match(log.statuses.at(-1), /Đã nhận dạng/);
});

test("joins final results and normalises Unicode and spaces", () => {
  const {assistant, log} = make();
  assistant.recognition.onresult({resultIndex: 0, results: [[{transcript: "  đổi lịch "}], [{transcript: `${"ngày".normalize("NFD")}   mai `}]]});
  assert.deepEqual(log.transcripts, ["đổi lịch ngày mai"]);
  assert.equal(log.transcripts[0], log.transcripts[0].normalize("NFC"));
});

test("interim results stay separate from final transcripts", () => {
  const {assistant, log} = make({interimResults: true});
  assert.equal(assistant.recognition.interimResults, true);
  assistant.recognition.onresult({resultIndex: 0, results: [Object.assign([{transcript: " mở kế"}], {isFinal: false})]});
  assert.deepEqual(log.interims, ["mở kế"]);
  assert.deepEqual(log.transcripts, []);
  assistant.recognition.onresult({resultIndex: 0, results: [Object.assign([{transcript: "mở kế hoạch"}], {isFinal: true})]});
  assert.deepEqual(log.transcripts, ["mở kế hoạch"]);
});

test("reports microphone errors and keeps them after onend", () => {
  const expected = {
    "not-allowed": /cấp quyền micro/, "audio-capture": /Không tìm thấy micro/, "no-speech": /Chưa nghe thấy/,
    network: /Internet/, "language-not-supported": /tiếng Việt/, other: /gặp lỗi/,
  };
  for (const [code, pattern] of Object.entries(expected)) {
    const {assistant, log} = make();
    assistant.toggleListening();
    assistant.recognition.onerror({error: code});
    assistant.recognition.onend();
    assert.match(log.statuses.at(-1), pattern, code);
  }
});

test("InvalidStateError and insecure context are reported", () => {
  const {assistant, log} = make();
  assistant.recognition.start = () => { const e = new Error("x"); e.name = "InvalidStateError"; throw e; };
  assert.equal(assistant.toggleListening(), false);
  assert.match(log.statuses.at(-1), /vừa dừng|đang khởi động/);

  const a = make();
  globalThis.isSecureContext = false;
  try {
    assert.equal(a.assistant.toggleListening(), false);
    assert.match(a.log.statuses.at(-1), /HTTPS hoặc localhost/);
  } finally { delete globalThis.isSecureContext; }
});

test("stops listening automatically after maxListenMs", async () => {
  const {assistant, calls} = make({maxListenMs: 20});
  assistant.toggleListening();
  await new Promise((resolve) => setTimeout(resolve, 60));
  assert.equal(calls.stop, 1);
  assert.equal(assistant.listening, false);
});

test("barge-in prevents microphone and TTS echo", () => {
  const a = make();
  a.assistant.speak("Xin chào bạn");
  a.utterances[0].onstart();
  assert.equal(a.assistant.speaking, true);
  const before = a.calls.cancel;
  a.assistant.toggleListening();
  assert.ok(a.calls.cancel > before);
  assert.equal(a.assistant.speaking, false);
  assert.equal(a.assistant.listening, true);
  a.assistant.speak("Capy trả lời");
  assert.equal(a.calls.abort, 1);
  assert.equal(a.assistant.listening, false);
});

test("speech text is cleaned", () => {
  const {assistant, utterances} = make();
  assistant.speak("Xin chào 🔥 **bạn** [xem lịch](https://x.vn/a) đạt 85% rồi!");
  assert.equal(utterances[0].text, "Xin chào bạn xem lịch đạt 85 phần trăm rồi!");
});

test("long answers are split into ordered chunks", () => {
  const {assistant, utterances} = make();
  const text = Array.from({length: 40}, (_, i) => `Đây là câu số ${i + 1} của câu trả lời khá dài.`).join(" ");
  assistant.speak(text);
  assert.ok(utterances.length > 3);
  assert.ok(utterances.every((u) => u.text.length <= 180));
  assert.ok(utterances[0].onstart && !utterances[1].onstart);
  assert.ok(utterances.at(-1).onend && !utterances[0].onend);
});

test("falls back to language tag when voice list is empty", () => {
  const {assistant, utterances} = make({voices: []});
  assert.equal(assistant.speak("Xin chào"), true);
  assert.equal(utterances[0].lang, "vi-VN");
  assert.equal(utterances[0].voice, undefined);
});

test("measures TTS latency and median", () => {
  const a = make();
  for (const [t0, t1] of [[100, 130], [200, 260], [300, 320]]) {
    a.setClock(t0);
    a.assistant.speak("Xin chào");
    a.setClock(t1);
    a.utterances.at(-1).onstart();
  }
  assert.deepEqual(a.log.latencies, [30, 60, 20]);
  assert.deepEqual(a.assistant.latencyStats(), {count: 3, last: 20, median: 30, max: 60});
});

test("uses the conventional average for an even-numbered latency median", () => {
  const {assistant} = make();
  [10, 20, 30, 40].forEach((latency) => assistant._recordLatency(latency));
  assert.equal(assistant.latencyStats().median, 25);
});

test("ignores stale callbacks after cancellation", () => {
  const a = make();
  a.assistant.speak("Câu thứ nhất");
  const old = a.utterances[0];
  a.assistant.speak("Câu thứ hai");
  old.onstart();
  assert.equal(a.assistant.speaking, false);
  a.utterances[1].onstart();
  assert.equal(a.assistant.speaking, true);
  a.utterances[1].onend();
  assert.equal(a.assistant.speaking, false);
});

test("real synthesis errors are reported but interrupted is ignored", () => {
  const a = make();
  a.assistant.speak("Xin chào");
  a.utterances[0].onerror({error: "interrupted"});
  assert.doesNotMatch(a.log.statuses.at(-1), /Không thể phát/);
  a.utterances[0].onerror({error: "synthesis-failed"});
  assert.match(a.log.statuses.at(-1), /Không thể phát/);
});

test("mute is persisted and restored", () => {
  const store = new Map();
  const first = make({store});
  first.assistant.toggleMute();
  assert.equal(store.get("capy.voice.muted"), "1");
  const second = make({store});
  assert.equal(second.assistant.muted, true);
  assert.equal(second.assistant.speak("Xin chào"), false);
  assert.equal(second.assistant.playCue("schedule_done"), false);
});

test("broken storage and missing WebAudio degrade gracefully", () => {
  const assistant = new VoiceAssistant({
    Recognition: null, synthesis: null, Utterance: null, AudioContext: null,
    storage: {getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); }},
  });
  assert.equal(assistant.toggleMute(), true);
  const a = make({noAudio: true});
  assert.equal(a.assistant.playCue("schedule_done"), false);
  assert.equal(a.assistant.cueLatencyMs(), null);
  a.assistant.unlockAudio();
});

test("audio cue schedules notes and reports local output latency", () => {
  const a = make();
  assert.equal(a.assistant.playCue("schedule_done"), true);
  assert.equal(a.oscillators.length, CUES.schedule_done.length);
  assert.deepEqual(a.oscillators.map((o) => o.frequency.value), CUES.schedule_done.map((n) => n[0]));
  assert.equal(a.assistant.cueLatencyMs(), 30);
  assert.equal(a.assistant.playCue("khong-ton-tai"), false);
});

test("dispose stops voice and recognition", () => {
  const a = make();
  a.assistant.toggleListening();
  a.assistant.dispose();
  assert.equal(a.calls.abort, 1);
  assert.equal(a.assistant.listening, false);
  assert.equal(a.assistant._audio, null);
});

test("cleanForSpeech handles Markdown, tables, symbols and truncation", () => {
  assert.equal(cleanForSpeech("# Tiêu đề\n- ý một\n- ý hai\n```js\nx=1\n```\nHết"), "Tiêu đề. ý một. ý hai. Hết");
  assert.equal(cleanForSpeech("Gối 90° → đứng lên ✅"), "Gối 90 độ, đứng lên");
  assert.equal(cleanForSpeech("| a | b |\n|---|---|\n| 1 | 2 |"), "a, b, 1, 2");
  assert.equal(cleanForSpeech("   "), "");
  assert.equal(cleanForSpeech(null), "");
});

test("splitSentences preserves sentence order and size", () => {
  assert.deepEqual(splitSentences("Một. Hai! Ba?"), ["Một.", "Hai!", "Ba?"]);
  assert.deepEqual(splitSentences(""), []);
});

test("pickVoice prefers exact Vietnamese voice and local service", () => {
  const remote = {lang: "vi-VN", localService: false, name: "Google"};
  const local = {lang: "vi-VN", localService: true, name: "Microsoft An"};
  const android = {lang: "vi_VN", localService: true};
  assert.equal(pickVoice([{lang: "en-US"}, remote, local]), local);
  assert.equal(pickVoice([{lang: "en-US"}, android]), android);
  assert.equal(pickVoice([{lang: "en-US"}, {lang: "fr-FR"}]), null);
});

test("debug report exposes selected voice, mute, speaking and latency fields", () => {
  const a = make({voices: [{lang: "en-US"}, {name: "Mai", lang: "vi-VN", localService: true}]});
  a.assistant.speak("Xin chào");
  a.utterances[0].onstart();
  const report = a.assistant.debugReport();
  assert.equal(report.language, "vi-VN");
  assert.equal(report.selectedVoice.name, "Mai");
  assert.equal(report.selectedVoice.localService, true);
  assert.equal(report.speaking, true);
  assert.equal(report.muted, false);
  assert.ok("ttsLatencyMs" in report);
  assert.ok("cueLatencyMs" in report);
});

test("a denied Permissions API state blocks recognition with recovery guidance", async () => {
  let startCount = 0;
  class Rec {
    start() { startCount += 1; }
    stop() {}
  }
  const statuses = [];
  const permissionStatus = {
    state: "denied",
    addEventListener() {},
    removeEventListener() {},
  };
  const assistant = new VoiceAssistant({
    Recognition: Rec,
    synthesis: null,
    Utterance: null,
    AudioContext: null,
    browserNavigator: {permissions: {query: async () => permissionStatus}},
    onStatus: (text) => statuses.push(text),
  });
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(assistant.microphonePermission, "denied");
  assert.equal(assistant.toggleListening(), false);
  assert.equal(startCount, 0);
  assert.match(statuses.at(-1), /Quyền micro đang bị chặn/);
});

test("unsupported microphone permission queries do not block Web Speech recognition", async () => {
  let started = false;
  class Rec { start() { started = true; this.onstart?.(); } stop() {} }
  const assistant = new VoiceAssistant({
    Recognition: Rec,
    synthesis: null,
    Utterance: null,
    AudioContext: null,
    browserNavigator: {permissions: {query: async () => { throw new Error("unsupported"); }}},
  });
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(assistant.microphonePermission, "unavailable");
  assert.equal(assistant.toggleListening(), true);
  assert.equal(started, true);
});
