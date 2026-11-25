export const VALID_MOODS = Object.freeze(["happy", "worried", "thinking", "proud"]);

export const CAPY_MOOD_META = Object.freeze({
  happy: {
    label: "Vui vẻ",
    ariaLabel: "Capybara đang vui vẻ",
  },
  worried: {
    label: "Lo lắng",
    ariaLabel: "Capybara đang lo lắng",
  },
  thinking: {
    label: "Suy nghĩ",
    ariaLabel: "Capybara đang suy nghĩ",
  },
  proud: {
    label: "Tự hào",
    ariaLabel: "Capybara đang tự hào",
  },
});

const MOOD_ALIASES = Object.freeze({
  happy: "happy",
  default: "happy",
  welcome: "happy",
  worried: "worried",
  sad: "worried",
  concerned: "worried",
  injury: "worried",
  thinking: "thinking",
  loading: "thinking",
  processing: "thinking",
  proud: "proud",
  celebrate: "proud",
  excited: "proud",
});

export const CAPY_EXPRESSION_SVGS = Object.freeze({
  happy: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="36" height="36" aria-hidden="true" focusable="false">
  <ellipse cx="60" cy="72" rx="42" ry="34" fill="#B58A63"/>
  <ellipse cx="30" cy="46" rx="9" ry="12" fill="#885532" transform="rotate(-15 30 46)"/>
  <ellipse cx="30" cy="46" rx="5" ry="7" fill="#DDA15E" transform="rotate(-15 30 46)"/>
  <ellipse cx="90" cy="46" rx="9" ry="12" fill="#885532" transform="rotate(15 90 46)"/>
  <ellipse cx="90" cy="46" rx="5" ry="7" fill="#DDA15E" transform="rotate(15 90 46)"/>
  <path d="M 40 68 C 40 56, 80 56, 80 68 C 80 82, 40 82, 40 68 Z" fill="#885532"/>
  <ellipse cx="54" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <ellipse cx="66" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <path d="M 38 54 Q 44 46 50 54" stroke="#2B1A0E" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <path d="M 70 54 Q 76 46 82 54" stroke="#2B1A0E" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <ellipse cx="36" cy="61" rx="7.5" ry="4.5" fill="#FB7185" opacity="0.75"/>
  <ellipse cx="84" cy="61" rx="7.5" ry="4.5" fill="#FB7185" opacity="0.75"/>
  <path d="M 54 73 Q 60 79 66 73" stroke="#4A2810" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <circle cx="60" cy="28" r="11" fill="#EA580C"/>
  <circle cx="59" cy="26" r="9.5" fill="#F97316"/>
  <circle cx="56" cy="23" r="3" fill="#FDBA74" opacity="0.65"/>
  <path d="M 60 17 Q 67 13 69 16 Q 66 20 60 17 Z" fill="#22C55E"/>
  <path d="M 20 25 L 22 30 L 27 32 L 22 34 L 20 39 L 18 34 L 13 32 L 18 30 Z" fill="#FACC15"/>
  <ellipse cx="44" cy="98" rx="9" ry="6" fill="#885532"/>
  <ellipse cx="76" cy="98" rx="9" ry="6" fill="#885532"/>
</svg>`,

  worried: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="36" height="36" aria-hidden="true" focusable="false">
  <ellipse cx="60" cy="72" rx="42" ry="34" fill="#A47148"/>
  <ellipse cx="30" cy="48" rx="9" ry="12" fill="#7D4B27" transform="rotate(-30 30 48)"/>
  <ellipse cx="30" cy="48" rx="5" ry="7" fill="#C99468" transform="rotate(-30 30 48)"/>
  <ellipse cx="90" cy="48" rx="9" ry="12" fill="#7D4B27" transform="rotate(30 90 48)"/>
  <ellipse cx="90" cy="48" rx="5" ry="7" fill="#C99468" transform="rotate(30 90 48)"/>
  <rect x="46" y="34" width="28" height="10" rx="5" fill="#FEF2F2" stroke="#F87171" stroke-width="1.5"/>
  <path d="M 60 36 V 42 M 57 39 H 63" stroke="#EF4444" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M 40 68 C 40 56, 80 56, 80 68 C 80 82, 40 82, 40 68 Z" fill="#885532"/>
  <ellipse cx="54" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <ellipse cx="66" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <ellipse cx="44" cy="54" rx="5.5" ry="7" fill="#2B1A0E"/>
  <circle cx="43" cy="52" r="2.2" fill="#FFFFFF"/>
  <circle cx="46.5" cy="56" r="1.1" fill="#FFFFFF"/>
  <ellipse cx="76" cy="54" rx="5.5" ry="7" fill="#2B1A0E"/>
  <circle cx="75" cy="52" r="2.2" fill="#FFFFFF"/>
  <circle cx="78.5" cy="56" r="1.1" fill="#FFFFFF"/>
  <path d="M 37 45 Q 43 41 49 46" stroke="#4A2810" stroke-width="2.6" fill="none" stroke-linecap="round"/>
  <path d="M 83 45 Q 77 41 71 46" stroke="#4A2810" stroke-width="2.6" fill="none" stroke-linecap="round"/>
  <path d="M 54 76 Q 60 71.5 66 76" stroke="#4A2810" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  <path d="M 85 62 C 82 66, 82 70, 85 72 C 88 70, 88 66, 85 62 Z" fill="#38BDF8"/>
  <circle cx="84.4" cy="68" r="0.9" fill="#FFFFFF"/>
  <ellipse cx="44" cy="98" rx="9" ry="6" fill="#7D4B27"/>
  <ellipse cx="76" cy="98" rx="9" ry="6" fill="#7D4B27"/>
</svg>`,

  thinking: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="36" height="36" aria-hidden="true" focusable="false">
  <ellipse cx="60" cy="72" rx="42" ry="34" fill="#B58A63"/>
  <ellipse cx="30" cy="46" rx="9" ry="12" fill="#885532" transform="rotate(-18 30 46)"/>
  <ellipse cx="30" cy="46" rx="5" ry="7" fill="#DDA15E" transform="rotate(-18 30 46)"/>
  <ellipse cx="90" cy="44" rx="9" ry="12" fill="#885532" transform="rotate(10 90 44)"/>
  <ellipse cx="90" cy="44" rx="5" ry="7" fill="#DDA15E" transform="rotate(10 90 44)"/>
  <path d="M 40 68 C 40 56, 80 56, 80 68 C 80 82, 40 82, 40 68 Z" fill="#885532"/>
  <ellipse cx="54" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <ellipse cx="66" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <circle cx="44" cy="53" r="5" fill="#2B1A0E"/>
  <circle cx="45.8" cy="51.2" r="1.9" fill="#FFFFFF"/>
  <circle cx="76" cy="53" r="5" fill="#2B1A0E"/>
  <circle cx="77.8" cy="51.2" r="1.9" fill="#FFFFFF"/>
  <path d="M 37 45 L 49 45" stroke="#4A2810" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M 70 43 Q 76 38 83 43" stroke="#4A2810" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M 55 75 Q 60 73.5 65 75.5" stroke="#4A2810" stroke-width="2.4" fill="none" stroke-linecap="round"/>
  <ellipse cx="42" cy="98" rx="9" ry="6" fill="#885532"/>
  <ellipse cx="71" cy="87" rx="9" ry="6.5" fill="#7D4B27" transform="rotate(-22 71 87)"/>
  <circle cx="95" cy="31" r="3" fill="#38BDF8"/>
  <circle cx="102" cy="22" r="4.2" fill="#38BDF8" opacity="0.85"/>
  <circle cx="110" cy="12" r="5.5" fill="#38BDF8" opacity="0.7"/>
</svg>`,

  proud: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="36" height="36" aria-hidden="true" focusable="false">
  <ellipse cx="60" cy="72" rx="42" ry="34" fill="#B58A63"/>
  <ellipse cx="30" cy="45" rx="9" ry="12" fill="#885532" transform="rotate(-12 30 45)"/>
  <ellipse cx="30" cy="45" rx="5" ry="7" fill="#DDA15E" transform="rotate(-12 30 45)"/>
  <ellipse cx="90" cy="45" rx="9" ry="12" fill="#885532" transform="rotate(12 90 45)"/>
  <ellipse cx="90" cy="45" rx="5" ry="7" fill="#DDA15E" transform="rotate(12 90 45)"/>
  <path d="M 40 68 C 40 56, 80 56, 80 68 C 80 82, 40 82, 40 68 Z" fill="#885532"/>
  <ellipse cx="54" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <ellipse cx="66" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <rect x="33" y="46" width="22" height="14" rx="5" fill="#0F172A" stroke="#FACC15" stroke-width="1.8"/>
  <rect x="65" y="46" width="22" height="14" rx="5" fill="#0F172A" stroke="#FACC15" stroke-width="1.8"/>
  <line x1="55" y1="52" x2="65" y2="52" stroke="#FACC15" stroke-width="2.4"/>
  <line x1="38" y1="50" x2="43" y2="56" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" opacity="0.85"/>
  <line x1="70" y1="50" x2="75" y2="56" stroke="#38BDF8" stroke-width="2" stroke-linecap="round" opacity="0.85"/>
  <path d="M 52 73 Q 61 81 69 72" stroke="#4A2810" stroke-width="2.8" fill="none" stroke-linecap="round"/>
  <path d="M 48 34 L 51 22 L 60 28 L 69 22 L 72 34 Z" fill="#FACC15" stroke="#D97706" stroke-width="1.5" stroke-linejoin="round"/>
  <path d="M 19 24 L 21 29 L 26 31 L 21 33 L 19 38 L 17 33 L 12 31 L 17 29 Z" fill="#FACC15"/>
  <path d="M 101 23 L 103 27 L 107 29 L 103 31 L 101 35 L 99 31 L 95 29 L 99 27 Z" fill="#4ADE80"/>
  <ellipse cx="44" cy="98" rx="9" ry="6" fill="#885532"/>
  <ellipse cx="76" cy="98" rx="9" ry="6" fill="#885532"/>
</svg>`,
});

const PROUD_PATTERN = /(?:hoan thanh|tap xong|xong buoi|xuat sac|tuyet voi|gioi qua|tu hao|ky luc|chuc mung|dinh chop|vuot muc tieu|pr moi)/;
const NEGATED_COMPLETION_PATTERN = /\b(?:chua|khong|dung|thieu)\s+(?:the\s+)?(?:hoan thanh|tap xong|xong buoi|dat duoc)/;

const browserSvgCache = new Map();

function stripDiacritics(text) {
  return String(text || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase();
}

export function normalizeMood(rawMood) {
  if (typeof rawMood !== "string") return "happy";
  const key = rawMood.trim().toLowerCase();
  return MOOD_ALIASES[key] || "happy";
}

export function resolveCapyMood(context = {}) {
  if (!context || typeof context !== "object") return "happy";

  if (context.isLoading || context.isTyping) {
    return "thinking";
  }

  const explicit = context.mood ?? context.emotion;
  if (typeof explicit === "string" && explicit.trim()) {
    const key = explicit.trim().toLowerCase();
    if (Object.prototype.hasOwnProperty.call(MOOD_ALIASES, key)) {
      return MOOD_ALIASES[key];
    }
  }

  const intent = String(context.intent || "").toUpperCase();
  const action = String(context.action || "").toLowerCase();

  if (intent === "INJURY_REPORT" || action === "swap_exercise_for_injury") {
    return "worried";
  }

  if (
    intent === "RESCHEDULE_DELOAD" ||
    action === "move_workout_day" ||
    action === "apply_instant_deload"
  ) {
    return "thinking";
  }

  if (
    intent === "WORKOUT_COMPLETE" ||
    intent === "PRAISE" ||
    context.completed === true
  ) {
    return "proud";
  }

  const combinedText = stripDiacritics(
    `${context.userMessage || ""} ${context.reply || ""} ${context.content || ""}`
  );
  if (combinedText && PROUD_PATTERN.test(combinedText) && !NEGATED_COMPLETION_PATTERN.test(combinedText)) {
    return "proud";
  }

  return "happy";
}

export function getCapyAvatarSvg(mood) {
  const canonical = normalizeMood(mood);
  return CAPY_EXPRESSION_SVGS[canonical];
}

function getCachedSvgNode(canonicalMood, doc) {
  const isBrowserDoc = typeof globalThis.document !== "undefined" && doc === globalThis.document;

  if (isBrowserDoc && browserSvgCache.has(canonicalMood)) {
    return browserSvgCache.get(canonicalMood).cloneNode(true);
  }

  const tpl = doc.createElement("template");
  tpl.innerHTML = CAPY_EXPRESSION_SVGS[canonicalMood].trim();
  const svgNode = tpl.content?.firstElementChild || tpl.firstElementChild || null;

  if (isBrowserDoc && svgNode) {
    browserSvgCache.set(canonicalMood, svgNode);
    return svgNode.cloneNode(true);
  }

  return svgNode;
}

export function createCapyAvatarElement(mood, options = {}) {
  const doc = options.document || (typeof document !== "undefined" ? document : null);
  if (!doc) return null;

  const canonical = normalizeMood(mood);
  const meta = CAPY_MOOD_META[canonical];

  const wrapper = doc.createElement("div");
  wrapper.className = `capy-svg-avatar capy-mood-${canonical}`;
  wrapper.setAttribute("data-mood", canonical);
  wrapper.setAttribute("role", "img");
  wrapper.setAttribute("aria-label", meta.ariaLabel);
  wrapper.setAttribute("title", meta.ariaLabel);

  const svgNode = getCachedSvgNode(canonical, doc);
  if (svgNode) {
    wrapper.appendChild(svgNode);
  } else {
    wrapper.innerHTML = CAPY_EXPRESSION_SVGS[canonical];
  }

  return wrapper;
}