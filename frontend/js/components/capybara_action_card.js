/**
 * SCRUM-32: Capybara Chat Action Card Component
 * - Renders schedule change diff (old strikethrough red -> new emerald green + workout day)
 * - Reads nested (action_result/changes/diff), top-level response fields, and params
 * - Uses DOM API + textContent exclusively (immune to XSS)
 * - Instant SPA navigation via App.navigate("planner") without page reload
 */

const JOINT_SWAP_FALLBACKS = Object.freeze({
  knee: {
    old: "Squat (Gánh đùi)",
    new: "Glute Bridge (Cầu mông)",
    note: "Giảm áp lực tối đa lên khớp gối",
  },
  wrist: {
    old: "Standard Push-up (Chống đẩy)",
    new: "Forearm Plank (Plank cẳng tay)",
    note: "Tránh dồn trọng lượng gập cổ tay",
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

function firstText(candidates, fallback = "") {
  for (const val of candidates) {
    const cleaned = cleanText(val);
    if (cleaned) return cleaned;
  }
  return fallback;
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
 * into a clean Action Card model. Returns null when no concrete schedule change exists.
 */
export function normalizeActionCard(source) {
  if (!source || typeof source !== "object") return null;

  const hasRawAction = Boolean(
    cleanText(source.action) || (typeof source.action_required === "string" && cleanText(source.action_required))
  );

  // Case 1: Already-normalized Action Card object (e.g. restored from localStorage)
  if (!hasRawAction && (source.old || source.oldExercise) && (source.new || source.newExercise)) {
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
  if (source.action_required === false) return null;

  const action = cleanText(
    source.action ?? (typeof source.action_required === "string" ? source.action_required : "")
  );
  if (!action) return null;

  const result = source.action_result || source.changes || source.diff || {};
  if (
    source.applied === false ||
    result.applied === false ||
    result.success === false
  ) {
    return null;
  }

  const isApplied =
    source.applied === true ||
    result.applied === true ||
    result.success === true;

  const params = source.params && typeof source.params === "object" ? source.params : {};

  if (action === "swap_exercise_for_injury") {
    const joint = firstText([result.joint, source.joint, params.joint]).toLowerCase();
    const fallback = Object.prototype.hasOwnProperty.call(JOINT_SWAP_FALLBACKS, joint)
      ? JOINT_SWAP_FALLBACKS[joint]
      : null;

    const oldEx = firstText(
      [
        result.old_exercise,
        result.oldExercise,
        result.from_exercise,
        source.old_exercise,
        source.oldExercise,
        source.from_exercise,
        params.old_exercise,
      ],
      fallback ? fallback.old : ""
    );
    const newEx = firstText(
      [
        result.new_exercise,
        result.newExercise,
        result.to_exercise,
        source.new_exercise,
        source.newExercise,
        source.to_exercise,
        params.new_exercise,
      ],
      fallback ? fallback.new : ""
    );

    // Do not fabricate a wrong knee swap when joint is unrecognized and API gave no exercises
    if (!oldEx || !newEx) return null;

    const day = firstText(
      [
        result.target_day,
        result.day,
        source.target_day,
        source.day,
        params.target_day,
        params.day,
        params.from_day,
      ],
      "Hôm nay"
    );

    const defaultNote = fallback
      ? `${isApplied ? "Đã thay bài giúp" : "Đề xuất thay bài giúp"} ${fallback.note.charAt(0).toLowerCase()}${fallback.note.slice(1)}`
      : isApplied
        ? "Đã cập nhật bài tập thay thế an toàn hơn trong giáo án"
        : "Đề xuất bài tập thay thế an toàn hơn cho vùng đang khó chịu";

    const note = firstText([result.note, result.reason, source.note, source.reason], defaultNote);

    return {
      actionType: action,
      title: isApplied ? "Đã đổi bài tập an toàn" : "Đề xuất đổi bài tập an toàn",
      badge: "🛡️ Bảo vệ khớp",
      old: oldEx,
      new: newEx,
      day,
      note,
    };
  }

  if (action === "move_workout_day") {
    const fromDay = firstText([result.from_day, source.from_day, params.from_day], "Hôm nay");
    const toDay = firstText([result.to_day, source.to_day, params.to_day], "Ngày mai");
    if (fromDay.toLowerCase() === toDay.toLowerCase()) return null;

    const defaultNote = isApplied
      ? `Đã dời buổi tập từ ${fromDay} sang ${toDay} trong giáo án tuần`
      : `Đề xuất dời buổi tập từ ${fromDay} sang ${toDay} trong giáo án tuần`;

    return {
      actionType: action,
      title: isApplied ? "Đã dời lịch tập luyện" : "Đề xuất dời lịch tập luyện",
      badge: "⚡ Hoán đổi lịch tuần",
      old: firstText([result.old_label, source.old_label], `Buổi tập ${fromDay}`),
      new: firstText([result.new_label, source.new_label], `Chuyển sang ${toDay}`),
      day: firstText([result.target_day, result.day, source.target_day, source.day], `${fromDay} → ${toDay}`),
      note: firstText([result.note, result.reason, source.note, source.reason], defaultNote),
    };
  }

  if (action === "apply_instant_deload") {
    const pct = normalizePercentage(result.percentage ?? source.percentage ?? params.percentage);
    const day = firstText(
      [result.target_day, result.day, source.target_day, source.day, params.target_day, params.day],
      "Buổi tập kế tiếp"
    );

    const defaultNote = isApplied
      ? `Đã giảm ${pct}% số reps và hiệp để cơ thể phục hồi tốt hơn`
      : `Đề xuất giảm ${pct}% số reps và hiệp để cơ thể phục hồi tốt hơn`;

    return {
      actionType: action,
      title: isApplied ? "Đã giảm tải cường độ (Deload)" : "Đề xuất giảm tải (Deload)",
      badge: "🌿 Hồi phục cơ bắp",
      old: firstText([result.old_label, source.old_label], "100% Khối lượng"),
      new: firstText([result.new_label, source.new_label], `${100 - pct}% (Giảm ${pct}%)`),
      day,
      note: firstText([result.note, result.reason, source.note, source.reason], defaultNote),
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