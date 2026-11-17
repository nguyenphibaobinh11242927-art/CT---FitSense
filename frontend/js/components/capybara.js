/**
 * Capybara Workout Companion Component
 */

import { API } from "../api.js";

export const Capybara = {
  element: null,
  bubbleEl: null,
  speechEl: null,
  avatarEl: null,
  closeBtn: null,
  quotes: [],
  currentQuoteIdx: 0,
  cycleTimer: null,
  hideTimeout: null,
  isDismissedByUser: false,

  async init() {
    this.element = document.getElementById("capybara-companion");
    this.bubbleEl = document.getElementById("capy-speech-bubble");
    this.speechEl = document.getElementById("capy-speech-text");
    this.avatarEl = document.getElementById("capy-avatar-wrap");
    this.closeBtn = document.getElementById("capy-close-btn");

    if (!this.element || !this.speechEl || !this.avatarEl) return;

    await this.refresh();

    // Close button ('x') handler
    this.closeBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      this.hideBubble(true);
    });

    // Avatar click handler: wake up mascot, display quote with wiggle
    this.avatarEl.addEventListener("click", () => {
      this.isDismissedByUser = false;
      this.nextQuote(true);
      this.showBubble();
      this.restartTimer();
    });

    // Bubble click (outside 'x'): cycle to next tip
    this.bubbleEl?.addEventListener("click", (e) => {
      if (e.target === this.closeBtn || this.closeBtn?.contains(e.target)) return;
      this.nextQuote(true);
      this.restartTimer();
    });

    // Start intermittent speech bubble cycle (Show 7s -> Hide 5s -> Repeat)
    this.startPeriodicCycle();
  },

  startPeriodicCycle() {
    if (this.cycleTimer) clearInterval(this.cycleTimer);
    if (this.hideTimeout) clearTimeout(this.hideTimeout);

    const SHOW_MS = 7500; // Show bubble for 7.5 seconds
    const HIDE_MS = 5000; // Hide bubble for 5 seconds

    // Initial show
    this.showBubble();
    this.hideTimeout = setTimeout(() => {
      if (!this.isDismissedByUser) this.hideBubble(false);
    }, SHOW_MS);

    // Recurring intermittent cycle
    this.cycleTimer = setInterval(() => {
      if (this.isDismissedByUser) return;

      this.nextQuote(false);
      this.showBubble();

      if (this.hideTimeout) clearTimeout(this.hideTimeout);
      this.hideTimeout = setTimeout(() => {
        if (!this.isDismissedByUser) this.hideBubble(false);
      }, SHOW_MS);
    }, SHOW_MS + HIDE_MS);
  },

  restartTimer() {
    if (this.hideTimeout) clearTimeout(this.hideTimeout);
    this.hideTimeout = setTimeout(() => {
      if (!this.isDismissedByUser) this.hideBubble(false);
    }, 7500);
  },

  showBubble() {
    if (!this.bubbleEl) return;
    this.bubbleEl.classList.remove("hidden");
  },

  hideBubble(dismissedByUser = false) {
    if (!this.bubbleEl) return;
    this.bubbleEl.classList.add("hidden");

    if (dismissedByUser) {
      this.isDismissedByUser = true;
      // After 30 seconds, re-allow gentle periodic tips
      setTimeout(() => {
        this.isDismissedByUser = false;
      }, 30000);
    }
  },

  async refresh() {
    try {
      const data = await API.capybara.status();
      this.quotes = data.all_quotes || [data.quote];
      this.avatarEl.innerHTML = data.svg;
      this.setSpeech(data.quote);
    } catch (e) {
      console.warn("Could not load capybara status:", e);
    }
  },

  setSpeech(text) {
    if (this.speechEl) {
      this.speechEl.textContent = text;
    }
  },

  nextQuote(userClicked = false) {
    if (!this.quotes || this.quotes.length === 0) return;
    this.currentQuoteIdx = (this.currentQuoteIdx + 1) % this.quotes.length;
    this.setSpeech(this.quotes[this.currentQuoteIdx]);

    if (userClicked && this.avatarEl) {
      this.avatarEl.style.transform = "scale(1.2) rotate(8deg)";
      setTimeout(() => {
        this.avatarEl.style.transform = "";
      }, 250);
    }
  },
};
