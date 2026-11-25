const JOINT_SWAP_FALLBACKS = Object.freeze({
  knee: {
    old: "Squat (Gánh đùi)",
    new: "Glute Bridge (Cầu mông)",
    note: "Thay bài tập giảm áp lực tối đa lên khớp gối",
  },
  wrist: {
    old: "Standard Push-up (Chống đẩy)",
    new: "Forearm Plank (Plank cẳng tay)",
    note: "Thay bài tránh dồn trọng lượng gập cổ tay",
  },
  shoulder: {
    old: "Pike Push-up (Đẩy vai dốc)",
    new: "Incline Push-up (Chống đẩy dốc)",
    note: "Giảm tải áp lực góc xoay của khớp vai",
  },
  lower_back: {
    old: "Leg Raise (Nâng chân)",
    new: "Dead Bug (Bọ chết siết bụng)",
    note: "Bảo vệ đĩa đệm và cơ thắt lưng dưới",
  },
});

function cleanText(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  const trimmed = String(value).trim();
  return trimmed || fallback;
}

function normalizePercentage(rawPct) {
  const num = Number(rawPct);
  if (!Number.isFinite(num) || num <= 0) return 30;
  const pct = num > 0 && num < 1 ? Math.round(num * 100) : Math.round(num);
  if (pct <= 0 || pct >= 100) return 30;
  return Math.max(5, Math.min(90, pct));
}

/**
 * Normalize either a raw API response (SCRUM-29 / SCRUM-30) or a stored card object
 * into a clean Action Card model. Returns null when no concrete schedule change occurred.
 */
export function normalizeActionCard(source) {
  if (!source || typeof source !== "object") return null;

  // Case 1: Already-normalized Action Card object (e.g. from localStorage)
  if (!source.action && (source.old || source.oldExercise) && (source.new || source.newExercise)) {
    const oldVal = cleanText(source.old ?? source.oldExercise);
    const newVal = cleanText(source.new ?? source.newExercise);
    if (!oldVal || !newVal) return null;

    return {
      actionType: cleanText(source.actionType, "custom_update"),
      title: cleanText(source.title, "Cập nhật Kế hoạch Tập luyện"),
      badge: cleanText(source.badge, "🛡️ Điều chỉnh lịch tập"),
      old: oldVal,
      new: newVal,
      day: cleanText(source.day, "Lịch tuần hiện tại"),
      note: cleanText(source.note, ""),
    };
  }

  // Case 2: Raw API response from /api/capybara/chat
  const action = cleanText(source.action);
  if (!action) return null;

  const result = source.action_result || source.changes || source.diff || {};
  if (
    source.applied === false ||
    result.applied === false ||
    result.success === false
  ) {
    return null;
  }

  const params = source.params && typeof source.params === "object" ? source.params : {};

  if (action === "swap_exercise_for_injury") {
    const joint = cleanText(result.joint ?? params.joint, "knee").toLowerCase();
    const fallback = JOINT_SWAP_FALLBACKS[joint] || JOINT_SWAP_FALLBACKS.knee;

    const oldEx = cleanText(
      result.old_exercise ?? result.oldExercise ?? result.from_exercise ?? params.old_exercise,
      fallback.old
    );
    const newEx = cleanText(
      result.new_exercise ?? result.newExercise ?? result.to_exercise ?? params.new_exercise,
      fallback.new
    );
    const day = cleanText(
      result.day ?? result.target_day ?? params.day ?? params.from_day,
      "Hôm nay"
    );
    const note = cleanText(result.note ?? result.reason, fallback.note);

    return {
      actionType: action,
      title: "Đổi bài tập an toàn",
      badge: "🛡️ Bảo vệ khớp",
      old: oldEx,
      new: newEx,
      day,
      note,
    };
  }

  if (action === "move_workout_day") {
    const fromDay = cleanText(result.from_day ?? params.from_day, "Hôm nay");
    const toDay = cleanText(result.to_day ?? params.to_day, "Ngày mai");
    if (fromDay.toLowerCase() === toDay.toLowerCase()) return null;

    return {
      actionType: action,
      title: "Dời lịch tập luyện",
      badge: "⚡ Hoán đổi lịch tuần",
      old: cleanText(result.old_label, `Buổi tập ${fromDay}`),
      new: cleanText(result.new_label, `Chuyển sang ${toDay}`),
      day: cleanText(result.day, `${fromDay} → ${toDay}`),
      note: cleanText(
        result.note ?? result.reason,
        `Đã dời buổi tập từ ${fromDay} sang ${toDay} trong giáo án tuần`
      ),
    };
  }

  if (action === "apply_instant_deload") {
    const pct = normalizePercentage(result.percentage ?? params.percentage);
    const day = cleanText(result.day ?? params.day, "Buổi tập kế tiếp");

    return {
      actionType: action,
      title: "Giảm tải cường độ (Deload)",
      badge: "🌿 Hồi phục cơ bắp",
      old: cleanText(result.old_label, "100% Khối lượng"),
      new: cleanText(result.new_label, `${100 - pct}% (Giảm ${pct}%)`),
      day,
      note: cleanText(
        result.note ?? result.reason,
        `Giảm ${pct}% số reps và hiệp để cơ thể phục hồi tốt hơn`
      ),
    };
  }

  return null;
}

/**
 * Trigger instant SPA navigation to the Planner view without reloading the page.
 * Prefers App.navigate("planner"), with safe fallbacks.
 */
export function navigateToPlanner(options = {}) {
  if (typeof options.onBeforeNavigate === "function") {
    options.onBeforeNavigate();
  }

  const root = options.globalObj || (typeof window !== "undefined" ? window : null);
  if (!root) return null;

  if (typeof root.App?.navigate === "function") {
    root.App.navigate("planner");
    return "App.navigate";
  }

  if (typeof root.navigateTo === "function") {
    root.navigateTo("planner", true);
    return "navigateTo";
  }

  if (root.location) {
    root.location.hash = "#planner";
    return "hash";
  }

  return null;
}

/**
 * Build a secure, XSS-safe DOM element for the Action Card.
 * Returns null if cardInput does not represent a valid action.
 */
export function createActionCardElement(cardInput, options = {}) {
  const card = normalizeActionCard(cardInput);
  if (!card) return null;

  const doc = options.document || (typeof document !== "undefined" ? document : null);
  if (!doc) return null;

  const container = doc.createElement("div");
  container.className = "capy-action-card";
  container.setAttribute("data-action-type", card.actionType);

  // 1. Header: Badge + Workout Day Pill
  const header = doc.createElement("div");
  header.className = "action-card-header";

  const badgeEl = doc.createElement("span");
  badgeEl.className = "action-badge";
  badgeEl.textContent = card.badge;

  const dayEl = doc.createElement("span");
  dayEl.className = "action-day-pill";
  dayEl.textContent = `📅 ${card.day}`;

  header.appendChild(badgeEl);
  header.appendChild(dayEl);
  container.appendChild(header);

  // 2. Title
  const titleEl = doc.createElement("div");
  titleEl.className = "action-card-title";
  titleEl.textContent = card.title;
  container.appendChild(titleEl);

  // 3. Diff Row: Old (red strikethrough <del>) -> New (emerald green <ins>)
  const swapRow = doc.createElement("div");
  swapRow.className = "action-swap-row";

  const oldEl = doc.createElement("del");
  oldEl.className = "action-old";
  oldEl.setAttribute("aria-label", `Bài cũ: ${card.old}`);
  oldEl.textContent = card.old;

  const arrowEl = doc.createElement("span");
  arrowEl.className = "action-arrow";
  arrowEl.setAttribute("aria-hidden", "true");
  arrowEl.textContent = "➔";

  const newEl = doc.createElement("ins");
  newEl.className = "action-new";
  newEl.setAttribute("aria-label", `Bài mới: ${card.new}`);
  newEl.textContent = card.new;

  swapRow.appendChild(oldEl);
  swapRow.appendChild(arrowEl);
  swapRow.appendChild(newEl);
  container.appendChild(swapRow);

  // 4. Optional Note
  if (card.note) {
    const noteEl = doc.createElement("div");
    noteEl.className = "action-note";
    noteEl.textContent = card.note;
    container.appendChild(noteEl);
  }

  // 5. Instant SPA Navigation Button
  const navBtn = doc.createElement("button");
  navBtn.type = "button";
  navBtn.className = "action-card-btn";
  navBtn.textContent = "Xem Lịch tuần 📅";
  navBtn.addEventListener("click", (e) => {
    if (e && typeof e.preventDefault === "function") e.preventDefault();
    if (e && typeof e.stopPropagation === "function") e.stopPropagation();
    navigateToPlanner(options);
  });
  container.appendChild(navBtn);

  return container;
}