import {VI_CUES} from "./voice/vi_cues.mjs";

const REP_WORDS = ["", "Một", "Hai", "Ba", "Bốn", "Năm", "Sáu", "Bảy", "Tám", "Chín", "Mười"];
const MAX_RECORDED_REP = 100;
const ENABLE_CUE = MAX_RECORDED_REP + 1;
const SHALLOW_SQUAT_CUE = ENABLE_CUE + 1;
const VOICE_URL = new URL("./voice/vi.mp3", import.meta.url);

export function createVoiceCoach({
  AudioContext, fetchAudio = globalThis.fetch, showCue, showStatus, now = () => performance.now(),
}) {
  const supported = typeof AudioContext === "function";
  let enabled = false;
  let context, audioBuffer;
  let sources = [], playbackId = 0;

  function stop() {
    playbackId++;
    for (const source of sources) source.stop();
    sources = [];
  }

  async function play(cueIds, capturedAt) {
    stop();
    const id = playbackId;
    try {
      context ??= new AudioContext();
      // Call resume before awaiting so the Voice Coach click can unlock playback.
      const ready = context.state === "running" ? undefined : context.resume();
      audioBuffer ??= fetchAudio(VOICE_URL).then(response => {
        if (!response.ok) throw new Error("Voice cues unavailable");
        return response.arrayBuffer();
      }).then(bytes => context.decodeAudioData(bytes)).catch(error => {
        audioBuffer = undefined;
        throw error;
      });
      const [buffer] = await Promise.all([audioBuffer, ready]);
      if (id !== playbackId) return;

      let when = context.currentTime;
      for (const cueId of cueIds) {
        const [offset, duration] = VI_CUES[cueId];
        const source = context.createBufferSource();
        source.buffer = buffer;
        source.connect(context.destination);
        source.onended = () => {
          source.disconnect();
          sources = sources.filter(playing => playing !== source);
        };
        source.start(when, offset, duration);
        sources.push(source);
        when += duration;
      }
      const elapsed = Number.isFinite(capturedAt) ? now() - capturedAt : -1;
      showStatus(elapsed >= 0
        ? `Từ khung hình đến lúc lên lịch phát: ${Math.round(elapsed)} ms.`
        : "Đã bật giọng tiếng Việt.");
    } catch {
      if (id === playbackId) showStatus("Không phát được âm thanh. Hãy tắt rồi bật lại Voice Coach.");
    }
  }

  return {
    supported,
    get enabled() { return enabled; },
    toggle() {
      if (!supported) return;
      enabled = !enabled;
      if (enabled) {
        showStatus("Đang nạp giọng tiếng Việt…");
        void play([ENABLE_CUE]);
      } else {
        stop();
        showStatus("Đã tắt giọng nói.");
      }
    },
    receive(event) {
      let text;
      let cues;
      if (event?.kind === "rep" && Number.isSafeInteger(event.count) && event.count > 0) {
        text = REP_WORDS[event.count] ?? String(event.count);
        cues = event.count <= MAX_RECORDED_REP ? [event.count] : Array.from(String(event.count), Number);
      } else if (event?.kind === "shallow_squat") {
        text = "Hạ thấp hơn một chút nếu thấy thoải mái.";
        cues = [SHALLOW_SQUAT_CUE];
      } else {
        return;
      }
      showCue(text);
      if (enabled) void play(cues, event.captured_at);
    },
    stop,
  };
}
