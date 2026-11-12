const PHRASES = new Map([
  ["bắt đầu", "start"], ["bắt đầu đi", "start"], ["tập thôi", "start"],
  ["tiếp tục", "start"], ["tập tiếp", "start"],
  ["dừng lại", "pause"], ["dừng", "pause"], ["ngưng", "pause"], ["ngừng", "pause"],
  ["tạm dừng", "pause"], ["tạm ngưng", "pause"], ["thôi tập", "pause"],
  ["fitsense thôi", "pause"], ["fit sense thôi", "pause"],
  ["nghỉ hiệp", "rest"], ["nghỉ giữa hiệp", "rest"], ["cho nghỉ hiệp", "rest"],
  ["bài tiếp theo", "next"], ["bài kế tiếp", "next"], ["qua bài", "next"], ["chuyển bài", "next"],
]);

const MIC_ERRORS = {
  "not-allowed": "Hãy cấp quyền micro trong trình duyệt rồi bật lại khẩu lệnh.",
  "service-not-allowed": "Trình duyệt đang chặn dịch vụ nhận diện giọng nói.",
  "audio-capture": "Không mở được micro. Hãy kiểm tra thiết bị rồi thử lại.",
  "network": "Dịch vụ nhận diện giọng nói mất kết nối. Hãy thử lại.",
  "language-not-supported": "Dịch vụ nhận diện chưa hỗ trợ tiếng Việt trên trình duyệt này.",
};

export function matchVoiceCommand(transcript) {
  if (typeof transcript !== "string") return undefined;
  const phrase = transcript.normalize("NFC").toLocaleLowerCase("vi-VN")
    .replace(/[^\p{L}\p{M}\p{N}]+/gu, " ").trim();
  return PHRASES.get(phrase);
}

export function createVoiceCommands({
  SpeechRecognition, onCommand, onStatus, onEnabledChange,
  schedule = setTimeout, cancel = clearTimeout,
}) {
  const supported = typeof SpeechRecognition === "function";
  let enabled = false, playing = false, attempt, restart;

  function abortAttempt() {
    if (!attempt?.accepting) return;
    attempt.accepting = false;
    try {
      attempt.recognizer.abort();
    } catch {
      attempt = undefined;
    }
  }

  function disable(message = "Đã tắt khẩu lệnh.") {
    enabled = false;
    cancel(restart);
    restart = undefined;
    abortAttempt();
    onEnabledChange(false);
    onStatus(message);
  }

  function start() {
    if (!enabled || playing || attempt || restart !== undefined) return;
    try {
      const recognizer = new SpeechRecognition();
      const current = {recognizer, accepting: true};
      attempt = current;
      recognizer.lang = "vi-VN";
      recognizer.continuous = true;
      recognizer.interimResults = false;
      recognizer.onstart = () => {
        if (current.accepting && attempt === current) onStatus("Đang nghe khẩu lệnh tiếng Việt.");
      };
      recognizer.onresult = event => {
        if (!enabled || playing || attempt !== current || !current.accepting) return;
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const command = result.isFinal && matchVoiceCommand(result[0]?.transcript);
          if (command) {
            onCommand(command);
            return;
          }
        }
      };
      recognizer.onerror = event => {
        if (attempt !== current || !current.accepting || event.error === "no-speech") return;
        attempt = undefined;
        disable(MIC_ERRORS[event.error] ?? "Nhận diện giọng nói bị gián đoạn. Hãy bật lại khẩu lệnh.");
      };
      recognizer.onend = () => {
        if (attempt !== current) return;
        attempt = undefined;
        if (enabled && !playing) {
          restart = schedule(() => {
            restart = undefined;
            start();
          }, 300);
        }
      };
      onStatus("Đang mở micro…");
      recognizer.start();
    } catch {
      attempt = undefined;
      disable("Không mở được nhận diện giọng nói. Hãy kiểm tra micro rồi thử lại.");
    }
  }

  return {
    supported,
    toggle() {
      if (!supported) return;
      if (enabled) {
        disable();
      } else {
        enabled = true;
        onEnabledChange(true);
        if (playing) onStatus("Đang chờ Voice Coach nói xong…");
        else start();
      }
    },
    setPlaybackActive(active) {
      playing = active;
      if (!enabled) return;
      if (playing) {
        abortAttempt();
        onStatus("Đang chờ Voice Coach nói xong…");
      } else {
        start();
      }
    },
    stop: disable,
  };
}
