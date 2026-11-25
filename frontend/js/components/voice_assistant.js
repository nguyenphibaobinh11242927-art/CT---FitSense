/**
 * Voice Assistant (SCRUM-33): nhận diện giọng nói tiếng Việt (STT) + đọc/âm báo phản hồi (TTS).
 */

const SPEECH_ERRORS = {
  "not-allowed": "Micro bị từ chối quyền. Hãy cấp quyền micro trong trình duyệt rồi thử lại.",
  "service-not-allowed": "Trình duyệt không cho phép dịch vụ nhận diện giọng nói.",
  "audio-capture": "Không tìm thấy micro. Hãy kiểm tra thiết bị thu âm.",
  "no-speech": "Chưa nghe thấy giọng nói. Hãy thử nói lại gần micro hơn.",
  network: "Không thể kết nối dịch vụ nhận diện giọng nói (Chrome gửi âm thanh tới máy chủ của Google nên cần Internet).",
  "language-not-supported": "Trình duyệt chưa hỗ trợ nhận diện giọng nói tiếng Việt.",
  aborted: "Đã dừng nhận diện giọng nói.",
};

export const CUES = {
  schedule_done: [[523.25, 0, 0.12], [659.25, 0.11, 0.12], [783.99, 0.22, 0.12], [1046.5, 0.33, 0.28]],
  listen_start: [[880, 0, 0.07], [1174.66, 0.07, 0.09]],
  listen_stop: [[1174.66, 0, 0.07], [880, 0.07, 0.09]],
  error: [[330, 0, 0.12], [247, 0.12, 0.18]],
};

const MUTE_KEY = "capy.voice.muted";

function truncateAtSentence(text, max) {
  if (text.length <= max) return text;
  const window = text.slice(0, max);
  let end = -1;
  for (const m of window.matchAll(/[.!?…](?=\s|$)/g)) end = m.index + 1;
  if (end >= max / 3) return window.slice(0, end).trim();
  const cut = window.lastIndexOf(" ");
  return (cut > 0 ? window.slice(0, cut) : window).replace(/[\s,;]+$/, "");
}

export function cleanForSpeech(text, maxChars = 600) {
  if (typeof text !== "string" || !text.trim()) return "";
  let t = text.normalize("NFC")
    .replace(/```[\s\S]*?```/g, " ")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, " ")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/(?:https?:\/\/|www\.)\S+/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/`([^`]*)`/g, "$1")
    .replace(/^[ \t]*\|?[ \t]*:?-{2,}:?[ \t]*(?:\|[ \t]*:?-{2,}:?[ \t]*)*\|?[ \t]*$/gm, " ")
    .replace(/\|/g, ", ")
    .replace(/^[ \t]{0,3}#{1,6}[ \t]*/gm, "")
    .replace(/^[ \t]*>+[ \t]?/gm, "")
    .replace(/^[ \t]*(?:[-*+•]|\d+[.)])[ \t]+/gm, "")
    .replace(/\*+|~~/g, "")
    .replace(/(?<!\w)_+|_+(?!\w)/g, "")
    .replace(/[←-⇿⟰-⟿⤀-⥿➜➔]+/g, ", ")
    .replace(/(\d)\s*%/g, "$1 phần trăm")
    .replace(/(\d)\s*°/g, "$1 độ")
    .replace(/[\p{Extended_Pictographic}\p{Emoji_Modifier}‍️⃣​]/gu, "");
  let joined = "";
  for (const line of t.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)) {
    if (joined && !/[.!?…:;,]$/.test(joined)) joined += ".";
    joined += (joined ? " " : "") + line;
  }
  t = joined.replace(/\s+/g, " ")
    .replace(/\s+([,.!?;:…])/g, "$1")
    .replace(/([,;:])\s*([.!?])/g, "$2")
    .replace(/,\s*,+/g, ",")
    .replace(/^[\s,;]+|[\s,;]+$/g, "");
  return truncateAtSentence(t, maxChars);
}

export function splitSentences(text, maxLen = 180) {
  const out = [];
  for (let chunk of String(text || "").trim().split(/(?<=[.!?…])\s+/)) {
    chunk = chunk.trim();
    while (chunk.length > maxLen) {
      let cut = Math.max(chunk.lastIndexOf(",", maxLen - 1), chunk.lastIndexOf(";", maxLen - 1));
      if (cut < maxLen / 3) cut = chunk.lastIndexOf(" ", maxLen - 1);
      if (cut <= 0) cut = maxLen - 1;
      out.push(chunk.slice(0, cut + 1).trim());
      chunk = chunk.slice(cut + 1).trim();
    }
    if (chunk) out.push(chunk);
  }
  return out.filter(Boolean);
}

export function pickVoice(voices, lang = "vi-VN") {
  const norm = (s) => String(s || "").replace("_", "-").toLowerCase();
  const want = norm(lang);
  const base = want.split("-")[0];
  const candidates = (voices || []).filter((v) => norm(v.lang).startsWith(base));
  if (!candidates.length) return null;
  const score = (v) => (norm(v.lang) === want ? 2 : 0) + (v.localService === true ? 1 : 0);
  return candidates.reduce((best, v) => (score(v) > score(best) ? v : best));
}

function safeStorage() {
  try { return globalThis.localStorage ?? null; } catch { return null; }
}

export class VoiceAssistant {
  constructor({
    Recognition = globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition,
    synthesis = globalThis.speechSynthesis,
    Utterance = globalThis.SpeechSynthesisUtterance,
    AudioContext = globalThis.AudioContext || globalThis.webkitAudioContext,
    storage = safeStorage(),
    browserNavigator = globalThis.navigator,
    now = () => globalThis.performance?.now?.() ?? Date.now(),
    lang = "vi-VN",
    maxListenMs = 12000,
    interimResults = false,
    onTranscript = () => {},
    onInterim = () => {},
    onStatus = () => {},
    onListeningChange = () => {},
    onMuteChange = () => {},
    onSpeakingChange = () => {},
    onLatency = () => {},
    onPermissionChange = () => {},
  } = {}) {
    this.synthesis = synthesis;
    this.Utterance = Utterance;
    this.AudioContext = AudioContext;
    this.storage = storage;
    this.browserNavigator = browserNavigator;
    this.now = now;
    this.lang = lang;
    this.maxListenMs = maxListenMs;
    this.onTranscript = onTranscript;
    this.onInterim = onInterim;
    this.onStatus = onStatus;
    this.onListeningChange = onListeningChange;
    this.onMuteChange = onMuteChange;
    this.onSpeakingChange = onSpeakingChange;
    this.onLatency = onLatency;
    this.onPermissionChange = onPermissionChange;
    this.listening = false;
    this.speaking = false;
    this.muted = this._loadMuted();
    this.latencies = [];
    this._gotResult = false;
    this._hadError = false;
    this._timer = null;
    this._audio = null;
    this._speakToken = 0;
    this.microphonePermission = "unknown";
    this._permissionStatus = null;
    this._onPermissionChange = null;
    this.recognition = Recognition ? new Recognition() : null;
    this.synthesis?.getVoices?.();
    void this._queryMicrophonePermission();

    if (this.recognition) {
      this.recognition.lang = lang;
      this.recognition.continuous = false;
      this.recognition.interimResults = interimResults;
      this.recognition.maxAlternatives = 1;
      this.recognition.onstart = () => {
        this._gotResult = false;
        this._hadError = false;
        this._armTimer();
        this.setListening(true);
        this.onStatus("Đang nghe… hãy nói tiếng Việt.");
      };
      this.recognition.onend = () => {
        this._clearTimer();
        const wasListening = this.listening;
        this.setListening(false);
        if (wasListening && !this._gotResult && !this._hadError) {
          this.onStatus("Chưa nhận được câu nào. Bấm micro và thử lại.");
        }
      };
      this.recognition.onerror = (event) => {
        this._hadError = true;
        this._clearTimer();
        this.setListening(false);
        this.onStatus(SPEECH_ERRORS[event.error] || "Nhận diện giọng nói gặp lỗi. Hãy thử lại.");
        this.playCue("error");
      };
      this.recognition.onresult = (event) => {
        let finalText = "";
        let interimText = "";
        const list = event.results || [];
        for (let i = event.resultIndex ?? 0; i < list.length; i += 1) {
          const part = list[i]?.[0]?.transcript;
          if (!part) continue;
          if (list[i].isFinal === false) interimText += part;
          else finalText += (finalText ? " " : "") + part;
        }
        const clean = (s) => s.normalize("NFC").replace(/\s+/g, " ").trim();
        if (!finalText && interimText) this.onInterim(clean(interimText));
        const text = clean(finalText);
        if (!text) return;
        this._gotResult = true;
        this.onTranscript(text);
        this.onStatus("Đã nhận dạng giọng nói tiếng Việt.");
      };
    }
    if (this.muted) queueMicrotask(() => this.onMuteChange(true));
  }

  setListening(value) { this.listening = value; this.onListeningChange(value); }

  async _queryMicrophonePermission() {
    const permissions = this.browserNavigator?.permissions;
    if (typeof permissions?.query !== "function") {
      this.microphonePermission = "unavailable";
      this.onPermissionChange(this.microphonePermission);
      return this.microphonePermission;
    }
    try {
      if (!this._permissionStatus) {
        this._permissionStatus = await permissions.query({name: "microphone"});
        this.microphonePermission = this._permissionStatus.state || "unknown";
        this.onPermissionChange(this.microphonePermission);
        this._onPermissionChange = () => {
          this.microphonePermission = this._permissionStatus?.state || "unknown";
          this.onPermissionChange(this.microphonePermission);
        };
        this._permissionStatus.addEventListener?.("change", this._onPermissionChange);
        if (!this._permissionStatus.addEventListener) {
          this._permissionStatus.onchange = this._onPermissionChange;
        }
      } else {
        this.microphonePermission = this._permissionStatus.state || "unknown";
      }
    } catch {
      // Some browsers expose Permissions API but do not implement microphone queries.
      this.microphonePermission = "unavailable";
      this.onPermissionChange(this.microphonePermission);
    }
    return this.microphonePermission;
  }

  toggleListening() {
    if (!this.recognition) {
      this.onStatus("Trình duyệt này chưa hỗ trợ nhận diện giọng nói. Hãy thử Chrome, Edge hoặc Safari phiên bản mới.");
      return false;
    }
    if (globalThis.isSecureContext === false) {
      this.onStatus("Micro chỉ hoạt động trên HTTPS hoặc localhost. Hãy mở ứng dụng qua một trong hai địa chỉ này.");
      return false;
    }
    this.unlockAudio();
    if (this.listening) {
      try {
        this.recognition.stop();
        this.playCue("listen_stop");
        return true;
      } catch {
        this.onStatus("Không thể dừng micro. Vui lòng thử lại.");
        return false;
      }
    }

    if (this.microphonePermission === "denied") {
      this.onStatus("Quyền micro đang bị chặn. Hãy cho phép micro trong cài đặt trang/trình duyệt rồi thử lại.");
      this.playCue("error");
      return false;
    }

    try {
      this.cancelSpeech();
      this.recognition.start();
      this.playCue("listen_start");
      return true;
    } catch (error) {
      if (error?.name === "InvalidStateError") this.onStatus("Micro đang khởi động hoặc vừa dừng. Vui lòng thử lại sau giây lát.");
      else this.onStatus("Không thể khởi động micro. Hãy kiểm tra quyền truy cập rồi thử lại.");
      this.playCue("error");
      return false;
    }
  }

  _armTimer() {
    this._clearTimer();
    if (!this.maxListenMs) return;
    this._timer = setTimeout(() => { try { this.recognition.stop(); } catch {} }, this.maxListenMs);
    this._timer?.unref?.();
  }
  _clearTimer() { if (this._timer) clearTimeout(this._timer); this._timer = null; }

  _loadMuted() {
    try { return this.storage?.getItem(MUTE_KEY) === "1"; } catch { return false; }
  }
  _saveMuted() {
    try { this.storage?.setItem(MUTE_KEY, this.muted ? "1" : "0"); } catch {}
  }
  toggleMute() {
    this.muted = !this.muted;
    this._saveMuted();
    if (this.muted) this.cancelSpeech();
    else this.unlockAudio();
    this.onMuteChange(this.muted);
    this.onStatus(this.muted ? "Đã tắt âm thanh Capy." : "Đã bật âm thanh Capy.");
    return this.muted;
  }

  _setSpeaking(value) {
    if (this.speaking === value) return;
    this.speaking = value;
    this.onSpeakingChange(value);
  }
  cancelSpeech() {
    this._speakToken += 1;
    this.synthesis?.cancel?.();
    this._setSpeaking(false);
  }
  speak(text) {
    const message = cleanForSpeech(text);
    if (this.muted || !message) return false;
    if (!this.synthesis || !this.Utterance) {
      this.onStatus("Trình duyệt này chưa hỗ trợ đọc văn bản.");
      return false;
    }
    try {
      if (this.listening) {
        this.recognition?.abort?.();
        this.setListening(false);
      }
      const chunks = splitSentences(message);
      const voice = pickVoice(this.synthesis.getVoices?.() ?? [], this.lang);
      this.synthesis.cancel();
      const token = (this._speakToken += 1);
      const t0 = this.now();
      chunks.forEach((chunk, index) => {
        const utterance = new this.Utterance(chunk);
        utterance.lang = this.lang;
        utterance.rate = 1;
        if (voice) utterance.voice = voice;
        if (index === 0) {
          utterance.onstart = () => {
            if (token !== this._speakToken) return;
            this._recordLatency(this.now() - t0);
            this._setSpeaking(true);
          };
        }
        if (index === chunks.length - 1) {
          utterance.onend = () => {
            if (token !== this._speakToken) return;
            this._setSpeaking(false);
            this.onStatus("Capy đã đọc xong.");
          };
        }
        utterance.onerror = (event) => {
          if (token !== this._speakToken || ["interrupted", "canceled"].includes(event?.error)) return;
          this._setSpeaking(false);
          this.onStatus("Không thể phát giọng đọc. Hãy thử lại hoặc kiểm tra âm thanh thiết bị.");
        };
        this.synthesis.speak(utterance);
      });
      this.onStatus("Capy đang đọc bằng tiếng Việt.");
      return true;
    } catch {
      this.onStatus("Không thể phát giọng đọc. Hãy thử lại hoặc kiểm tra âm thanh thiết bị.");
      return false;
    }
  }

  _recordLatency(ms) {
    this.latencies.push(ms);
    if (this.latencies.length > 50) this.latencies.shift();
    this.onLatency(ms);
  }
  latencyStats() {
    const v = [...this.latencies].sort((a, b) => a - b);
    if (!v.length) return {count: 0, last: null, median: null, max: null};
    const middle = Math.floor(v.length / 2);
    const median = v.length % 2 ? v[middle] : (v[middle - 1] + v[middle]) / 2;
    return {count: v.length, last: this.latencies.at(-1), median, max: v.at(-1)};
  }
  debugReport() {
    const voices = this.synthesis?.getVoices?.() ?? [];
    const voice = pickVoice(voices, this.lang);
    return {
      secureContext: globalThis.isSecureContext,
      browser: globalThis.navigator?.userAgent || "",
      recognitionSupported: Boolean(this.recognition),
      microphonePermission: this.microphonePermission,
      language: this.lang,
      selectedVoice: voice ? {
        name: voice.name,
        lang: voice.lang,
        localService: voice.localService,
      } : null,
      availableVietnameseVoices: voices
        .filter((item) => String(item.lang || "").toLowerCase().replace("_", "-").startsWith("vi"))
        .map((item) => ({
          name: item.name,
          lang: item.lang,
          localService: item.localService,
        })),
      listening: this.listening,
      speaking: this.speaking,
      muted: this.muted,
      ttsLatencyMs: this.latencyStats(),
      cueLatencyMs: this.cueLatencyMs(),
    };
  }

  _ctx() {
    if (this._audio) return this._audio;
    if (!this.AudioContext) return null;
    try { this._audio = new this.AudioContext(); } catch { this._audio = null; }
    return this._audio;
  }
  _resumeAudio(ctx) {
    try {
      const resume = ctx?.resume?.();
      resume?.catch?.(() => {});
    } catch {
      // Browser autoplay policies can reject resume until the next user gesture.
    }
  }
  unlockAudio() {
    const ctx = this._ctx();
    if (ctx?.state === "suspended") this._resumeAudio(ctx);
  }
  playCue(name = "schedule_done") {
    const notes = CUES[name];
    if (this.muted || !notes) return false;
    const ctx = this._ctx();
    if (!ctx) return false;
    if (ctx.state === "suspended") this._resumeAudio(ctx);
    const t0 = ctx.currentTime + 0.005;
    for (const [freq, at, dur] of notes) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.0001, t0 + at);
      gain.gain.exponentialRampToValueAtTime(0.25, t0 + at + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + at + dur);
      osc.connect(gain).connect(ctx.destination);
      osc.start(t0 + at);
      osc.stop(t0 + at + dur + 0.02);
    }
    return true;
  }
  cueLatencyMs() {
    const ctx = this._audio;
    if (!ctx) return null;
    const ms = ((ctx.baseLatency || 0) + (ctx.outputLatency || 0)) * 1000;
    return Number.isFinite(ms) ? Math.round(ms * 10) / 10 : null;
  }
  dispose() {
    this._clearTimer();
    if (this.listening) this.recognition?.abort?.();
    if (this._permissionStatus && this._onPermissionChange) {
      this._permissionStatus.removeEventListener?.("change", this._onPermissionChange);
      if (this._permissionStatus.onchange === this._onPermissionChange) {
        this._permissionStatus.onchange = null;
      }
    }
    this.cancelSpeech();
    this.setListening(false);
    this._audio?.close?.();
    this._audio = null;
  }
}
