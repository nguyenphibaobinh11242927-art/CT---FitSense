import assert from "node:assert/strict";
import test from "node:test";
import {VoiceAssistant} from "../frontend/js/components/voice_assistant.js";

function setup({Recognition = class {}, voices = [{lang: "vi-VN"}], supportedSynthesis = true} = {}) {
  const statuses = [], transcripts = [], listening = [], muted = [], utterances = [];
  const recognitionInstances = [];
  const RecognitionConstructor = class extends Recognition {
    constructor() {
      super();
      recognitionInstances.push(this);
    }
    start() { this.started = true; this.onstart?.(); }
    stop() { this.stopped = true; this.onend?.(); }
    abort() { this.aborted = true; }
  };
  const synthesis = supportedSynthesis ? {
    getVoices: () => voices,
    cancel() { this.cancelled = true; },
    speak(utterance) { utterances.push(utterance); },
  } : null;
  const assistant = new VoiceAssistant({
    Recognition: RecognitionConstructor,
    synthesis,
    Utterance: class { constructor(text) { this.text = text; } },
    onTranscript: (text) => transcripts.push(text),
    onStatus: (text) => statuses.push(text),
    onListeningChange: (value) => listening.push(value),
    onMuteChange: (value) => muted.push(value),
  });
  return {assistant, statuses, transcripts, listening, muted, utterances, recognition: recognitionInstances[0], synthesis};
}

test("configures Vietnamese recognition and puts final speech into the transcript input callback", () => {
  const result = setup();
  assert.equal(result.recognition.lang, "vi-VN");
  assert.equal(result.recognition.interimResults, false);
  assert.equal(result.assistant.toggleListening(), true);
  assert.deepEqual(result.listening, [true]);

  result.recognition.onresult({
    resultIndex: 0,
    results: [[{transcript: "  Mở kế hoạch tập luyện  "}]],
  });
  assert.deepEqual(result.transcripts, ["Mở kế hoạch tập luyện"]);
  assert.match(result.statuses.at(-1), /Đã nhận dạng/);
});

test("handles unsupported recognition and reports microphone errors", () => {
  const statuses = [];
  const assistant = new VoiceAssistant({
    Recognition: null,
    synthesis: null,
    Utterance: null,
    onStatus: (text) => statuses.push(text),
  });
  assert.equal(assistant.toggleListening(), false);
  assert.match(statuses.at(-1), /chưa hỗ trợ/);

  const result = setup();
  result.recognition.onerror({error: "not-allowed"});
  assert.match(result.statuses.at(-1), /cấp quyền micro/);
});

test("reads Vietnamese text, selects a Vietnamese voice and cancels speech when muted", () => {
  const vietnameseVoice = {lang: "vi-VN"};
  const result = setup({voices: [{lang: "en-US"}, vietnameseVoice]});
  assert.equal(result.assistant.speak("Xin chào"), true);
  assert.equal(result.utterances[0].lang, "vi-VN");
  assert.equal(result.utterances[0].voice, vietnameseVoice);

  assert.equal(result.assistant.toggleMute(), true);
  assert.equal(result.synthesis.cancelled, true);
  assert.equal(result.assistant.speak("Không đọc câu này"), false);
  assert.equal(result.utterances.length, 1);
});

test("does not claim to speak when browser speech synthesis is unavailable", () => {
  const result = setup({supportedSynthesis: false});
  assert.equal(result.assistant.speak("Xin chào"), false);
  assert.match(result.statuses.at(-1), /chưa hỗ trợ đọc/);
});
