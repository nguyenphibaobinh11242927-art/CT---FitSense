import test from "node:test";
import assert from "node:assert/strict";

import {
  VALID_MOODS,
  CAPY_EXPRESSION_SVGS,
  normalizeMood,
  resolveCapyMood,
  getCapyAvatarSvg,
  createCapyAvatarElement,
} from "../frontend/js/components/capybara_expressions.js";

import {
  normalizeActionCard,
  navigateToPlanner,
  createActionCardElement,
} from "../frontend/js/components/capybara_action_card.js";

function createMockDocument() {
  class MockElement {
    constructor(tagName) {
      this.tagName = tagName.toUpperCase();
      this.className = "";
      this.attributes = new Map();
      this.children = [];
      this.listeners = new Map();
      this._textContent = "";
      this._innerHTML = "";
      this.innerHTMLWriteCount = 0;
    }

    get textContent() {
      return this._textContent;
    }

    set textContent(val) {
      this._textContent = String(val);
    }

    get innerHTML() {
      return this._innerHTML;
    }

    set innerHTML(val) {
      this.innerHTMLWriteCount += 1;
      this._innerHTML = String(val);
    }

    setAttribute(k, v) {
      this.attributes.set(k, String(v));
    }

    getAttribute(k) {
      return this.attributes.get(k) ?? null;
    }

    appendChild(child) {
      this.children.push(child);
      return child;
    }

    addEventListener(event, handler) {
      if (!this.listeners.has(event)) this.listeners.set(event, []);
      this.listeners.get(event).push(handler);
    }

    click() {
      let prevented = false;
      const ev = {
        preventDefault: () => { prevented = true; },
        stopPropagation: () => {},
      };
      for (const fn of this.listeners.get("click") || []) {
        fn(ev);
      }
      return prevented;
    }

    findByClass(cls) {
      if (this.className.split(/\s+/).includes(cls)) return this;
      for (const child of this.children) {
        const found = child.findByClass(cls);
        if (found) return found;
      }
      return null;
    }
  }

  return {
    createElement(tag) {
      return new MockElement(tag);
    },
  };
}

test("All 4 SVG expressions are lightweight, valid, safe, and stay inside circular clip radius", () => {
  assert.deepEqual([...VALID_MOODS].sort(), ["happy", "proud", "thinking", "worried"]);

  for (const mood of VALID_MOODS) {
    const svg = getCapyAvatarSvg(mood);
    assert.ok(svg.startsWith("<svg "), `${mood} must start with <svg`);
    assert.ok(svg.endsWith("</svg>"), `${mood} must end with </svg>`);
    assert.ok(svg.includes('viewBox="0 0 120 120"'), `${mood} must match 120x120 viewBox`);
    assert.equal(/\bid\s*=/.test(svg), false, `${mood} SVG must not define DOM IDs`);
    assert.equal(/<script/i.test(svg), false, `${mood} SVG must not contain scripts`);
    assert.equal(/\bon[a-z]+\s*=/i.test(svg), false, `${mood} SVG must not contain inline handlers`);
    assert.ok(svg.length < 3000, `${mood} SVG should stay lightweight`);

    // Verify every <circle> stays comfortably within border-radius: 50% clip (inner radius ~55)
    for (const match of svg.matchAll(/<circle[^>]*cx="([\d.]+)"[^>]*cy="([\d.]+)"[^>]*r="([\d.]+)"/g)) {
      const cx = Number(match[1]);
      const cy = Number(match[2]);
      const r = Number(match[3]);
      const maxEdge = Math.hypot(cx - 60, cy - 60) + r;
      assert.ok(maxEdge <= 54.5, `${mood} circle (${cx},${cy},r=${r}) exceeds circular clip (${maxEdge.toFixed(1)})`);
    }
  }
  assert.equal(Object.keys(CAPY_EXPRESSION_SVGS).length, 4);
});

test("normalizeMood handles aliases and safely falls back to happy", () => {
  assert.equal(normalizeMood("WORRIED"), "worried");
  assert.equal(normalizeMood("sad"), "worried");
  assert.equal(normalizeMood(" thinking "), "thinking");
  assert.equal(normalizeMood("proud"), "proud");
  assert.equal(normalizeMood(null), "happy");
  assert.equal(normalizeMood(undefined), "happy");
  assert.equal(normalizeMood("<img src=x onerror=alert(1)>"), "happy");
});

test("resolveCapyMood avoids false-positive proud on questions, filler negations, false words, and default replies", () => {
  assert.equal(resolveCapyMood({ isLoading: true }), "thinking");
  assert.equal(resolveCapyMood({ intent: "INJURY_REPORT" }), "worried");
  assert.equal(resolveCapyMood({ action: "swap_exercise_for_injury" }), "worried");
  assert.equal(resolveCapyMood({ action: "move_workout_day" }), "thinking");
  assert.equal(resolveCapyMood({ action: "apply_instant_deload" }), "thinking");

  // Genuine assistant praise/completion -> proud
  assert.equal(resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Giỏi quá bạn ơi, đạt kỷ lục mới rồi! 🦫✨" }), "proud");
  assert.equal(resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Chúc mừng bạn đã hoàn thành buổi tập hôm nay! 🦫✨" }), "proud");
  assert.equal(resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Tự hào về bạn quá! 🦫✨" }), "proud");

  // Praise followed by a friendly follow-up question at the end -> still proud
  assert.equal(
    resolveCapyMood({
      intent: "QA_FITNESS_APP",
      reply: "Tuyệt vời quá! Chúc mừng bạn đã hoàn thành buổi tập hôm nay! Bạn muốn giãn cơ nhẹ không?",
    }),
    "proud"
  );

  // Informational questions must NOT trigger proud
  assert.equal(
    resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Tỷ lệ hoàn thành trong mục Đánh giá là gì?" }),
    "happy"
  );
  assert.equal(
    resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Làm sao đạt kỷ lục mới?" }),
    "happy"
  );

  // "thứ tư hào hứng" must NOT match "tự hào"
  assert.equal(
    resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Thứ tư hào hứng tập luyện cùng Capy nhé!" }),
    "happy"
  );
  assert.equal(
    resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "thu tu hao hung tap luyen nhe!" }),
    "happy"
  );

  // Negations with filler words must NOT trigger proud
  assert.equal(
    resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Hôm nay bạn chưa bấm hoàn thành buổi tập." }),
    "happy"
  );
  assert.equal(
    resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Tiếc quá, hôm nay không kịp tập xong rồi." }),
    "happy"
  );

  // Default backend guidance reply (both "Capy" & "Capybara") must stay happy
  assert.equal(
    resolveCapyMood({
      intent: "QA_FITNESS_APP",
      userMessage: "Mình vừa hoàn thành buổi tập hôm nay!",
      reply: "Capy có thể giúp bạn tìm hiểu bài tập Calisthenics hoặc cách dùng Kế hoạch, Thư viện và Live HUD. Bạn muốn hỏi phần nào? 🦫✨",
    }),
    "happy"
  );
  assert.equal(
    resolveCapyMood({
      intent: "QA_FITNESS_APP",
      reply: "Capybara có thể giúp bạn tìm hiểu bài tập Calisthenics. Chúc mừng bạn đến với FitSense! 🦫✨",
    }),
    "happy"
  );

  // Explicit backend mood takes precedence
  assert.equal(resolveCapyMood({ mood: "proud", intent: "QA_FITNESS_APP", reply: "Chào bạn" }), "proud");
  assert.equal(resolveCapyMood({}), "happy");
});

test("normalizeActionCard reads top-level fields, array diffs, success flags, and handles unknown joints safely", () => {
  // 1. Known joint proposal (not yet applied -> proposal phrasing)
  const kneeProposal = normalizeActionCard({
    intent: "INJURY_REPORT",
    action: "swap_exercise_for_injury",
    params: { joint: "knee" },
  });
  assert.equal(kneeProposal.old, "Squat (Gánh đùi)");
  assert.equal(kneeProposal.new, "Glute Bridge (Cầu mông)");
  assert.equal(kneeProposal.day, "Hôm nay");
  assert.ok(kneeProposal.note.startsWith("Đề xuất"));

  // 2. Top-level API fields (action_required, old_exercise, new_exercise, target_day, note)
  const topLevelSwap = normalizeActionCard({
    action_required: "swap_exercise_for_injury",
    applied: true,
    old_exercise: "Jump Squat",
    new_exercise: "Glute Bridge",
    target_day: "Thứ 4",
    note: "Đã cập nhật trực tiếp lịch Thứ 4",
  });
  assert.equal(topLevelSwap.old, "Jump Squat");
  assert.equal(topLevelSwap.new, "Glute Bridge");
  assert.equal(topLevelSwap.day, "Thứ 4");
  assert.equal(topLevelSwap.note, "Đã cập nhật trực tiếp lịch Thứ 4");

  // 3. Unknown joint WITHOUT explicit exercises must NOT fall back to knee
  assert.equal(
    normalizeActionCard({
      action: "swap_exercise_for_injury",
      params: { joint: "ankle" },
    }),
    null
  );

  // 4. Unknown joint WITH explicit exercises renders them cleanly
  const ankleExplicit = normalizeActionCard({
    action: "swap_exercise_for_injury",
    joint: "ankle",
    old_exercise: "Jumping Jacks",
    new_exercise: "Seated Arm Circles",
    target_day: "Thứ 6",
  });
  assert.equal(ankleExplicit.old, "Jumping Jacks");
  assert.equal(ankleExplicit.new, "Seated Arm Circles");
  assert.equal(ankleExplicit.day, "Thứ 6");

  // 5. Move workout day: proposal vs applied phrasing & same-day no-op guard
  const moveProposal = normalizeActionCard({
    action: "move_workout_day",
    params: { from_day: "Thứ 2", to_day: "Thứ 4" },
  });
  assert.equal(moveProposal.day, "Thứ 2 → Thứ 4");
  assert.ok(moveProposal.note.startsWith("Đề xuất dời"));

  const moveApplied = normalizeActionCard({
    action: "move_workout_day",
    applied: true,
    params: { from_day: "Thứ 2", to_day: "Thứ 4" },
  });
  assert.ok(moveApplied.note.startsWith("Đã dời"));

  assert.equal(
    normalizeActionCard({ action: "move_workout_day", params: { from_day: "Thứ 2", to_day: "Thứ 2" } }),
    null
  );

  // 6. Deload reads top-level target_day & normalizes percentage
  const deloadCard = normalizeActionCard({
    action: "apply_instant_deload",
    target_day: "Thứ 5",
    params: { percentage: 0.25 },
  });
  assert.equal(deloadCard.day, "Thứ 5");
  assert.equal(deloadCard.new, "75% (Giảm 25%)");
  assert.ok(deloadCard.note.startsWith("Đề xuất giảm"));

  // 7. Non-action & unapplied guards
  assert.equal(normalizeActionCard({ intent: "QA_FITNESS_APP", action: null }), null);
  assert.equal(normalizeActionCard({ action_required: false }), null);
  assert.equal(
    normalizeActionCard({ action: "swap_exercise_for_injury", action_result: { applied: false } }),
    null
  );
  assert.equal(normalizeActionCard({ action: "unknown_action" }), null);

  // 8. Top-level success flag (false -> null, true -> applied wording)
  assert.equal(
    normalizeActionCard({
      success: false,
      action: "swap_exercise_for_injury",
      params: { joint: "knee" },
    }),
    null
  );
  const topSuccessMove = normalizeActionCard({
    success: true,
    action: "move_workout_day",
    params: { from_day: "Thứ 2", to_day: "Thứ 4" },
  });
  assert.ok(topSuccessMove.title.startsWith("Đã dời"));
  assert.ok(topSuccessMove.note.startsWith("Đã dời"));

  // 9. Array-shaped diff / changes (SCRUM-30 payload compatibility)
  const arrayDiffSwap = normalizeActionCard({
    success: true,
    action: "swap_exercise_for_injury",
    diff: [{ old_exercise: "Jump Squat", new_exercise: "Glute Bridge", day: "Thứ 4" }],
  });
  assert.equal(arrayDiffSwap.old, "Jump Squat");
  assert.equal(arrayDiffSwap.new, "Glute Bridge");
  assert.equal(arrayDiffSwap.day, "Thứ 4");
  assert.ok(arrayDiffSwap.title.startsWith("Đã đổi"));

  const nestedChangesSwap = normalizeActionCard({
    action: "swap_exercise_for_injury",
    action_result: {
      success: true,
      changes: [{ old_exercise: "Standard Push-up", new_exercise: "Forearm Plank", target_day: "Thứ 3" }],
    },
  });
  assert.equal(nestedChangesSwap.old, "Standard Push-up");
  assert.equal(nestedChangesSwap.new, "Forearm Plank");
  assert.equal(nestedChangesSwap.day, "Thứ 3");
  assert.ok(nestedChangesSwap.title.startsWith("Đã đổi"));
});

test("createActionCardElement renders semantic diff safely (XSS-proof) and invokes App.navigate('planner')", () => {
  const doc = createMockDocument();
  const xssPayload = '<img src=x onerror="alert(1)">';
  const calls = [];

  const mockWindow = {
    App: {
      navigate: (view) => calls.push(`App.navigate:${view}`),
    },
  };

  const cardEl = createActionCardElement(
    {
      action: "swap_exercise_for_injury",
      action_result: {
        applied: true,
        old_exercise: xssPayload,
        new_exercise: "Glute Bridge",
        day: "Thứ 5",
        note: xssPayload,
      },
    },
    {
      document: doc,
      globalObj: mockWindow,
      onBeforeNavigate: () => calls.push("close"),
    }
  );

  assert.ok(cardEl);
  const oldEl = cardEl.findByClass("action-old");
  const newEl = cardEl.findByClass("action-new");
  const dayEl = cardEl.findByClass("action-day-pill");
  const noteEl = cardEl.findByClass("action-note");
  const btnEl = cardEl.findByClass("action-card-btn");

  assert.equal(oldEl.tagName, "DEL");
  assert.equal(oldEl.textContent, xssPayload);
  assert.equal(oldEl.innerHTMLWriteCount, 0, "Must never inject untrusted data via innerHTML");

  assert.equal(newEl.tagName, "INS");
  assert.equal(newEl.textContent, "Glute Bridge");
  assert.equal(dayEl.textContent, "📅 Thứ 5");
  assert.equal(noteEl.textContent, xssPayload);
  assert.equal(noteEl.innerHTMLWriteCount, 0);
  assert.equal(btnEl.textContent, "Xem Lịch tuần 📅");

  const prevented = btnEl.click();
  assert.equal(prevented, true);
  assert.deepEqual(calls, ["close", "App.navigate:planner"]);
});

test("navigateToPlanner supports fallbacks when App.navigate is unavailable", () => {
  const navCalls = [];
  const res1 = navigateToPlanner({
    globalObj: { navigateTo: (v, force) => navCalls.push([v, force]) },
  });
  assert.equal(res1, "navigateTo");
  assert.deepEqual(navCalls, [["planner", true]]);

  const mockLoc = { location: { hash: "#dashboard" } };
  const res2 = navigateToPlanner({ globalObj: mockLoc });
  assert.equal(res2, "hash");
  assert.equal(mockLoc.location.hash, "#planner");
});

test("createCapyAvatarElement builds accessible avatar wrapper for each mood", () => {
  const doc = createMockDocument();
  const el = createCapyAvatarElement("worried", { document: doc });
  assert.equal(el.getAttribute("data-mood"), "worried");
  assert.equal(el.getAttribute("role"), "img");
  assert.ok(el.className.includes("capy-mood-worried"));

  const fallbackEl = createCapyAvatarElement("invalid-mood", { document: doc });
  assert.equal(fallbackEl.getAttribute("data-mood"), "happy");
});