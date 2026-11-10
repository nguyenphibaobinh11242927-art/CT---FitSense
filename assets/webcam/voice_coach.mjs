import {VI_CUES} from "./voice/vi_cues.mjs";

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
  let current, pendingRep, pendingCorrection;

  function stop() {
    const playback = current;
    current = pendingRep = pendingCorrection = null;
    for (const source of playback?.sources ?? []) source.stop();
  }

  async function play(cueIds, capturedAt) {
    const playback = {sources: new Set()};
    current = playback;
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
      if (current !== playback) return;

      let when = context.currentTime;
      for (const cueId of cueIds) {
        const [offset, duration] = VI_CUES[cueId];
        const source = context.createBufferSource();
        source.buffer = buffer;
        source.connect(context.destination);
        source.onended = () => {
          source.disconnect();
          playback.sources.delete(source);
          if (current !== playback || playback.sources.size) return;
          current = null;
          if (pendingRep) {
            const next = pendingRep;
            pendingRep = null;
            void playRep(next);
          } else if (pendingCorrection) {
            const next = pendingCorrection;
            pendingCorrection = null;
            void playCorrection(next);
          }
        };
        source.start(when, offset, duration);
        playback.sources.add(source);
        when += duration;
      }
      const elapsed = Number.isFinite(capturedAt) ? now() - capturedAt : -1;
      showStatus(elapsed >= 0
        ? `Từ khung hình đến lúc lên lịch phát: ${Math.round(elapsed)} ms.`
        : "Đã bật giọng tiếng Việt.");
    } catch {
      if (current !== playback) return;
      stop();
      showStatus("Không phát được âm thanh. Hãy tắt rồi bật lại Voice Coach.");
    }
  }

  function playRep({count, captured_at: capturedAt}) {
    const cues = count <= MAX_RECORDED_REP ? [count] : Array.from(String(count), Number);
    return play(cues, capturedAt);
  }

  function playCorrection({captured_at: capturedAt}) {
    showCue("Hạ thấp hơn nếu thấy thoải mái.");
    return play([SHALLOW_SQUAT_CUE], capturedAt);
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
        showCue("");
        showStatus("Đã tắt giọng nói.");
      }
    },
    receive(event) {
      if (!enabled) return;
      if (event?.kind === "rep" && Number.isSafeInteger(event.count) && event.count > 0) {
        pendingCorrection = null;
        showCue("");
        // Keep the latest rep while a clip finishes, without building up a queue.
        if (current) pendingRep = event;
        else void playRep(event);
      } else if (event?.kind === "shallow_squat") {
        if (current) pendingCorrection = event;
        else void playCorrection(event);
      }
    },
    stop,
  };
}
