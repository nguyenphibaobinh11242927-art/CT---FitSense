const ADDRESS = /^(?:fit\s?sense|capy(?:bara)?)(?: oi)?(?: |$)/;
const REQUEST = /^(?:vui long|lam on|(?:cho|giup) (?:minh|toi|em)|(?:minh|toi|em)(?: muon)?|co the) /;
const POLITE_END = /(?: (?:giup (?:minh|toi|em|voi)|cho (?:minh|toi|em)|bay gio|duoc khong|nhe|nha|di|nao|a))+$/;

// Match the whole request, so a phrase quoted in conversation is not a command.
const COMMANDS = [
  ["start", /^(?:bat dau(?: lai)?(?: tap(?: luyen)?| bai tap| buoi tap)?|khoi dong buoi tap|vao (?:tap|buoi tap)|tap thoi|tiep tuc(?: tap| buoi tap| bai tap)?|tap tiep|lam tiep)$/],
  ["pause", /^(?:(?:tam )?(?:dung|ngung)(?: lai)?(?: (?:tap|buoi tap|bai tap)(?: nay)?(?: lai)?)?(?: (?:mot )?(?:chut|lat|ti|xiu))?|thoi tap)$/],
  ["rest", /^(?:(?:bat dau |cho )?nghi (?:giua )?hiep(?: nay)?|(?:bat|mo) dong ho nghi(?: giua hiep)?|nghi (?:(?:mot )?(?:chut|lat|ti|xiu)|giai lao)|cho nghi)$/],
  ["next", /^(?:(?:(?:chuyen|qua|sang|doi)(?: sang| qua)? )?(?:bai(?: tap)?|dong tac) (?:tiep theo|ke tiep|ke|tiep|sau)|qua bai|sang bai|chuyen bai|bo qua bai(?: nay)?)$/],
];

const MIC_ERRORS = {
  "not-allowed": "Hãy cấp quyền micro rồi bật lại khẩu lệnh.",
  "service-not-allowed": "Trình duyệt đang chặn nhận diện giọng nói.",
  "audio-capture": "Không mở được micro. Hãy kiểm tra thiết bị rồi thử lại.",
  "network": "Dịch vụ nhận diện giọng nói mất kết nối. Hãy bật lại khẩu lệnh.",
  "language-not-supported": "Trình duyệt chưa hỗ trợ nhận diện tiếng Việt.",
};
const RESTART_DELAY_MS = 300;

export function matchVoiceCommand(transcript) {
  if (typeof transcript !== "string") return undefined;
  const phrase = transcript.toLocaleLowerCase("vi-VN").normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/đ/g, "d")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
  const addressed = ADDRESS.test(phrase);
  const action = phrase.replace(ADDRESS, "").replace(REQUEST, "").replace(POLITE_END, "");
  if (addressed && action === "thoi") return "pause";
  return COMMANDS.find(([, pattern]) => pattern.test(action))?.[0];
}

export function createVoiceCommands({
  SpeechRecognition, onCommand, onStatus, onEnabledChange,
  schedule = setTimeout, cancel = clearTimeout,
}) {
  const supported = typeof SpeechRecognition === "function";
  let enabled = false;
  let blockMessage = "";
  let attempt;
  let restart;

  function cancelRestart() {
    if (restart !== undefined) cancel(restart);
    restart = undefined;
  }

  function abortAttempt() {
    if (!attempt?.accepting) return;
    attempt.accepting = false;
    try {
      attempt.recognizer.abort();
    } catch {
      attempt = undefined;
    }
  }

  function stop(message = "Đã tắt micro khẩu lệnh.") {
    enabled = false;
    cancelRestart();
    abortAttempt();
    onEnabledChange(false);
    onStatus(message);
  }

  function restartAfterQuiet() {
    if (!enabled || blockMessage || attempt || restart !== undefined) return;
    restart = schedule(() => {
      restart = undefined;
      start();
    }, RESTART_DELAY_MS);
  }

  function start() {
    if (!enabled || blockMessage || attempt || restart !== undefined) return;
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
        if (!enabled || blockMessage || !current.accepting || attempt !== current) return;
        const commands = new Set();
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          const command = result.isFinal && matchVoiceCommand(result[0]?.transcript);
          if (command) commands.add(command);
        }
        if (commands.size === 1) onCommand(commands.values().next().value);
      };
      recognizer.onerror = event => {
        if (attempt !== current || !current.accepting || event.error === "no-speech") return;
        stop(MIC_ERRORS[event.error] ?? "Nhận diện bị gián đoạn. Hãy bật lại khẩu lệnh.");
      };
      recognizer.onend = () => {
        if (attempt !== current) return;
        attempt = undefined;
        restartAfterQuiet();
      };
      onStatus("Đang mở micro…");
      recognizer.start();
    } catch {
      attempt = undefined;
      stop("Không mở được micro. Hãy kiểm tra quyền rồi thử lại.");
    }
  }

  return {
    supported,
    get enabled() { return enabled; },
    toggle() {
      if (!supported) return;
      if (enabled) {
        stop();
      } else {
        enabled = true;
        onEnabledChange(true);
        if (blockMessage) onStatus(blockMessage);
        else start();
      }
    },
    setBlocked(message = "") {
      if (blockMessage === message) return;
      blockMessage = message;
      if (message) {
        cancelRestart();
        abortAttempt();
        if (enabled) onStatus(message);
      } else {
        restartAfterQuiet();
      }
    },
    stop,
  };
}
