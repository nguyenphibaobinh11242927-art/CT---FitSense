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

// Lightweight Mock DOM for verifying DOM API rendering, XSS safety & click events
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

test("All 4 SVG expressions are lightweight, valid, and free of duplicate IDs or scripts", () => {
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

test("resolveCapyMood maps intents, loading, praise, and negated completion accurately", () => {
  assert.equal(resolveCapyMood({ isLoading: true }), "thinking");
  assert.equal(resolveCapyMood({ intent: "INJURY_REPORT" }), "worried");
  assert.equal(resolveCapyMood({ action: "swap_exercise_for_injury" }), "worried");
  assert.equal(resolveCapyMood({ action: "move_workout_day" }), "thinking");
  assert.equal(resolveCapyMood({ action: "apply_instant_deload" }), "thinking");
  assert.equal(resolveCapyMood({ intent: "QA_FITNESS_APP", userMessage: "Mình vừa hoàn thành buổi tập hôm nay!" }), "proud");
  assert.equal(resolveCapyMood({ intent: "QA_FITNESS_APP", reply: "Giỏi quá bạn ơi, đạt kỷ lục mới rồi!" }), "proud");

  // Negated completion must NOT trigger proud
  assert.equal(resolveCapyMood({ intent: "QA_FITNESS_APP", userMessage: "Hôm nay mình chưa hoàn thành buổi tập" }), "happy");
  assert.equal(resolveCapyMood({ intent: "QA_FITNESS_APP", userMessage: "Mình chưa tập xong nữa" }), "happy");

  // Explicit backend mood takes precedence
  assert.equal(resolveCapyMood({ mood: "proud", intent: "QA_FITNESS_APP", reply: "Chào bạn" }), "proud");
  assert.equal(resolveCapyMood({}), "happy");
});

test("normalizeActionCard handles all 3 actions, SCRUM-30 payloads, and non-action guards", () => {
  // 1. Injury swap fallback
  const kneeCard = normalizeActionCard({
    intent: "INJURY_REPORT",
    action: "swap_exercise_for_injury",
    params: { joint: "knee" },
  });
  assert.equal(kneeCard.old, "Squat (Gánh đùi)");
  assert.equal(kneeCard.new, "Glute Bridge (Cầu mông)");
  assert.equal(kneeCard.day, "Hôm nay");

  // 2. Enriched SCRUM-30 payload takes priority
  const enrichedCard = normalizeActionCard({
    intent: "INJURY_REPORT",
    action: "swap_exercise_for_injury",
    params: { joint: "knee" },
    action_result: {
      applied: true,
      old_exercise: "Jump Squat",
      new_exercise: "Glute Bridge",
      day: "Thứ 4",
      note: "Đã cập nhật trực tiếp lịch Thứ 4",
    },
  });
  assert.equal(enrichedCard.old, "Jump Squat");
  assert.equal(enrichedCard.new, "Glute Bridge");
  assert.equal(enrichedCard.day, "Thứ 4");
  assert.equal(enrichedCard.note, "Đã cập nhật trực tiếp lịch Thứ 4");

  // 3. Move workout day & same-day no-op guard
  const moveCard = normalizeActionCard({
    action: "move_workout_day",
    params: { from_day: "Thứ 2", to_day: "Thứ 4" },
  });
  assert.equal(moveCard.day, "Thứ 2 → Thứ 4");
  assert.equal(
    normalizeActionCard({ action: "move_workout_day", params: { from_day: "Thứ 2", to_day: "Thứ 2" } }),
    null
  );

  // 4. Deload percentage normalization (fraction, integer, invalid)
  const deloadFrac = normalizeActionCard({ action: "apply_instant_deload", params: { percentage: 0.25 } });
  assert.equal(deloadFrac.new, "75% (Giảm 25%)");
  const deloadInvalid = normalizeActionCard({ action: "apply_instant_deload", params: { percentage: -50 } });
  assert.equal(deloadInvalid.new, "70% (Giảm 30%)");

  // 5. Non-action & unapplied guards
  assert.equal(normalizeActionCard({ intent: "QA_FITNESS_APP", action: null }), null);
  assert.equal(
    normalizeActionCard({ action: "swap_exercise_for_injury", action_result: { applied: false } }),
    null
  );
  assert.equal(normalizeActionCard({ action: "unknown_action" }), null);
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

  // Click button -> closes chat and navigates via App.navigate("planner") without reload
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