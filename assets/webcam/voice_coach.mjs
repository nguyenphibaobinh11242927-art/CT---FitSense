const REP_WORDS = ["", "Một", "Hai", "Ba", "Bốn", "Năm", "Sáu", "Bảy", "Tám", "Chín", "Mười"];

export function createVoiceCoach({synthesis, Utterance, showCue, showStatus, now = () => performance.now()}) {
  const supported = Boolean(synthesis && Utterance);
  let enabled = false;
  let active;

  function stop() {
    if (!active) return;
    active = null;
    synthesis.cancel();
  }

  function speak(text, capturedAt) {
    stop();
    const voices = synthesis.getVoices().filter(voice => /^vi(?:-|$)/i.test(voice.lang));
    const voice = voices.find(voice => voice.localService) ?? voices[0];
    if (!voice) {
      showStatus("Chưa có giọng tiếng Việt. Hãy cài giọng tiếng Việt cho thiết bị.");
      return;
    }

    const utterance = new Utterance(text);
    utterance.lang = voice.lang;
    utterance.voice = voice;
    utterance.onstart = () => {
      if (active !== utterance) return;
      const elapsed = Number.isFinite(capturedAt) ? now() - capturedAt : -1;
      showStatus(elapsed >= 0
        ? `Từ khung hình đến lúc bắt đầu đọc: ${Math.round(elapsed)} ms.`
        : "Đã bật giọng tiếng Việt.");
    };
    utterance.onend = () => {
      if (active === utterance) active = null;
    };
    utterance.onerror = () => {
      if (active !== utterance) return;
      active = null;
      showStatus("Không phát được giọng nói. Hãy tắt rồi bật lại Voice Coach.");
    };
    active = utterance;
    synthesis.speak(utterance);
  }

  return {
    supported,
    get enabled() { return enabled; },
    toggle() {
      if (!supported) return;
      enabled = !enabled;
      if (enabled) {
        showStatus("Đang thử giọng tiếng Việt…");
        speak("Đã bật trợ lý giọng nói.");
      } else {
        stop();
        showStatus("Đã tắt giọng nói.");
      }
    },
    receive(event) {
      let text;
      if (event?.kind === "rep" && Number.isSafeInteger(event.count) && event.count > 0) {
        text = REP_WORDS[event.count] ?? String(event.count);
      } else if (event?.kind === "shallow_squat") {
        text = "Hạ thấp hơn một chút nếu thấy thoải mái.";
      } else {
        return;
      }
      showCue(text);
      if (enabled) speak(text, event.captured_at);
    },
    stop,
  };
}
