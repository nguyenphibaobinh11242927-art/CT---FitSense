import {VI_CUES} from "./voice/vi_cues.mjs";

const MAX_RECORDED_REP = 100;
const ENABLE_CUE = MAX_RECORDED_REP + 1;
const SHALLOW_SQUAT_CUE = ENABLE_CUE + 1;
const VOICE_URL = new URL("./voice/vi.mp3", import.meta.url);
const CORRECTION_COOLDOWN_MS = 4000;
const CORRECTION_MAX_AGE_MS = 1000;

export function createVoiceCoach({
  AudioContext, fetchAudio = globalThis.fetch, showCue, showStatus, now = () => performance.now(),
  onEnabledChange = () => {}, onCorrection = () => {},
}) {
  const supported = typeof AudioContext === "function";
  let enabled = false;
  let context, audioBuffer;
  let current, pendingRep, pendingCorrection;
  let lastCorrectionAt = -Infinity;

  function setEnabled(value) {
    enabled = value;
    onEnabledChange(enabled);
  }

  function stop() {
    const playback = current;
    if (pendingCorrection) onCorrection(pendingCorrection.event, "stopped");
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
            scheduleCorrection(next);
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
      return true;
    } catch {
      if (current !== playback) return;
      stop();
      setEnabled(false);
      showCue("");
      showStatus("Không phát được âm thanh. Bấm Voice Coach để thử lại.");
    }
  }

  function playRep({count, captured_at: capturedAt}) {
    const cues = count <= MAX_RECORDED_REP ? [count] : Array.from(String(count), Number);
    return play(cues, capturedAt);
  }

  async function playCorrection(event) {
    showCue("Hạ thấp hơn nếu thấy thoải mái.");
    if (await play([SHALLOW_SQUAT_CUE], event.captured_at)) {
      lastCorrectionAt = now();
      onCorrection(event, "scheduled");
    } else {
      onCorrection(event, "not-played");
    }
  }

  function scheduleCorrection(request) {
    const {event, expiresAt} = request;
    const timestamp = now();
    if (!enabled) {
      onCorrection(event, "muted");
    } else if (timestamp >= expiresAt) {
      onCorrection(event, "expired");
    } else if (timestamp - lastCorrectionAt < CORRECTION_COOLDOWN_MS) {
      onCorrection(event, "cooldown");
    } else if (current) {
      if (pendingCorrection) onCorrection(pendingCorrection.event, "replaced");
      pendingCorrection = request;
      onCorrection(event, "waiting");
    } else {
      void playCorrection(event);
    }
  }

  return {
    supported,
    get enabled() { return enabled; },
    toggle() {
      if (!supported) return;
      setEnabled(!enabled);
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
      if (event?.kind === "shallow_squat") {
        onCorrection(event, "detected");
        const capturedAt = Number.isFinite(event.captured_at) ? event.captured_at : now();
        scheduleCorrection({event, expiresAt: capturedAt + CORRECTION_MAX_AGE_MS});
        return;
      }
      if (!enabled) return;
      if (event?.kind === "rep" && Number.isSafeInteger(event.count) && event.count > 0) {
        if (pendingCorrection) onCorrection(pendingCorrection.event, "rep-completed");
        pendingCorrection = null;
        showCue("");
        // Keep the latest rep while a clip finishes, without building up a queue.
        if (current) pendingRep = event;
        else void playRep(event);
      }
    },
    stop,
  };
}
