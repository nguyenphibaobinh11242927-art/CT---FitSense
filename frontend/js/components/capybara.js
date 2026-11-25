/**
 * Capybara Workout Companion Component
 * Featuring Autonomous Leisure Wandering, Natural Waddle Animation,
 * Smart Responsive Speech Bubble & Free Drag-and-Drop
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
  wanderTimer: null,
  dismissTimer: null,
  resumeTimer: null,
  isDismissedByUser: false,
  isChatOpen: false,
  isPaused: false,
  isDragging: false,
  currentX: 0, // Translation offset X from default bottom-right
  currentY: 0, // Translation offset Y from default bottom-right
  isFacingLeft: false,

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

    // Setup Drag-and-Drop & Avatar Click handlers
    this.setupInteractions();

    // Bubble click (outside 'x'): cycle to next tip
    this.bubbleEl?.addEventListener("click", (e) => {
      if (e.target === this.closeBtn || this.closeBtn?.contains(e.target)) return;
      this.nextQuote(true);
      this.restartTimer();
    });

    // Start intermittent speech bubble cycle (Show 7.5s -> Hide 5s -> Repeat)
    this.startPeriodicCycle();

    // Start leisurely ambient wandering along screen bottom
    this.startWandering();
  },

  setupInteractions() {
    let startX = 0, startY = 0;
    let initialPosX = this.currentX, initialPosY = this.currentY;
    let dragDistance = 0;
    let startTime = 0;

    const onPointerDown = (e) => {
      if (e.button && e.button !== 0) return;
      if (this.resumeTimer) clearTimeout(this.resumeTimer);
      this.isPaused = true;
      startX = e.clientX || e.touches?.[0]?.clientX || 0;
      startY = e.clientY || e.touches?.[0]?.clientY || 0;
      initialPosX = this.currentX;
      initialPosY = this.currentY;
      dragDistance = 0;
      startTime = Date.now();

      const onPointerMove = (ev) => {
        const clientX = ev.clientX || ev.touches?.[0]?.clientX || 0;
        const clientY = ev.clientY || ev.touches?.[0]?.clientY || 0;
        const dx = clientX - startX;
        const dy = clientY - startY;
        dragDistance = Math.hypot(dx, dy);

        if (dragDistance > 5) {
          this.isDragging = true;
          this.element.classList.add("is-dragging");
          this.currentX = initialPosX + dx;
          this.currentY = initialPosY + dy;
          this.applyPosition();
          this.updateBubbleDirection();
        }
      };

      const onPointerUp = () => {
        window.removeEventListener("mousemove", onPointerMove);
        window.removeEventListener("mouseup", onPointerUp);
        window.removeEventListener("touchmove", onPointerMove);
        window.removeEventListener("touchend", onPointerUp);

        this.element.classList.remove("is-dragging");
        const elapsed = Date.now() - startTime;

        if (this.isDragging) {
          setTimeout(() => { this.isDragging = false; }, 50);
          this.clampWithinScreen();
          // Resume wandering after 15s of idle in new position
          if (this.resumeTimer) clearTimeout(this.resumeTimer);
          this.resumeTimer = setTimeout(() => {
            if (!this.isChatOpen) this.isPaused = false;
          }, 15000);
        } else if (elapsed < 350 && dragDistance < 6) {
          // Plain click on Capybara: Open Capybara AI Chat Dialog (SCRUM-31)!
          this.setChatOpen(true);
          import("./capybara_chat.js?v=3.0.0").then((m) => m.CapybaraChat?.open());
        }
      };

      window.addEventListener("mousemove", onPointerMove);
      window.addEventListener("mouseup", onPointerUp);
      window.addEventListener("touchmove", onPointerMove, { passive: true });
      window.addEventListener("touchend", onPointerUp);
    };

    this.avatarEl.addEventListener("mousedown", onPointerDown);
    this.avatarEl.addEventListener("touchstart", onPointerDown, { passive: true });

    // Pause wandering when hovered
    this.element.addEventListener("mouseenter", () => {
      if (this.resumeTimer) clearTimeout(this.resumeTimer);
      this.isPaused = true;
    });
    this.element.addEventListener("mouseleave", () => {
      if (!this.isDragging && !this.isChatOpen) {
        if (this.resumeTimer) clearTimeout(this.resumeTimer);
        this.resumeTimer = setTimeout(() => {
          if (!this.isChatOpen) this.isPaused = false;
        }, 5000);
      }
    });
  },

  startWandering() {
    if (this.wanderTimer) clearInterval(this.wanderTimer);

    // Every 22 seconds, take a walk along bottom dock
    this.wanderTimer = setInterval(() => {
      if (this.isChatOpen || this.isPaused || this.isDragging) return;
      const workoutView = document.getElementById("view-workout");
      if (workoutView && workoutView.classList.contains("active")) return;

      this.takeWalk();
    }, 22000);
  },

  takeWalk() {
    if (this.isChatOpen || this.isPaused || this.isDragging) return;

    const screenWidth = window.innerWidth;
    const maxWalkLeft = Math.max(120, screenWidth - 280);
    const targetOffset = -Math.floor(Math.random() * maxWalkLeft);

    const distance = Math.abs(targetOffset - this.currentX);
    if (distance < 50) return;

    // Determine facing direction
    this.isFacingLeft = targetOffset < this.currentX;
    this.avatarEl.style.transform = this.isFacingLeft ? "scaleX(-1)" : "scaleX(1)";

    // Walking speed: ~60px/s, clamped between 2.5s and 6s
    const walkDurationSec = Math.max(2.5, Math.min(6, distance / 60));

    // Add walking CSS class
    this.avatarEl.classList.add("is-walking");
    this.element.classList.add("is-moving");
    this.element.style.transition = `transform ${walkDurationSec}s cubic-bezier(0.25, 1, 0.5, 1)`;

    this.currentX = targetOffset;
    this.currentY = Math.floor(Math.random() * 12) - 4;
    this.applyPosition();
    this.updateBubbleDirection();

    // When arrival complete
    setTimeout(() => {
      this.avatarEl.classList.remove("is-walking");
      this.element.classList.remove("is-moving");
      this.avatarEl.style.transform = this.isFacingLeft ? "scaleX(-1)" : "";
    }, walkDurationSec * 1000);
  },

  applyPosition() {
    if (this.element) {
      this.element.style.transform = `translate3d(${this.currentX}px, ${this.currentY}px, 0)`;
    }
  },

  updateBubbleDirection() {
    if (!this.element) return;
    const rect = this.element.getBoundingClientRect();
    if (rect.left < 340) {
      this.element.classList.add("bubble-right");
    } else {
      this.element.classList.remove("bubble-right");
    }
  },

  clampWithinScreen() {
    const rect = this.element.getBoundingClientRect();
    const pad = 16;
    let fixX = 0, fixY = 0;

    if (rect.left < pad) fixX = pad - rect.left;
    if (rect.right > window.innerWidth - pad) fixX = (window.innerWidth - pad) - rect.right;
    if (rect.top < pad) fixY = pad - rect.top;
    if (rect.bottom > window.innerHeight - pad) fixY = (window.innerHeight - pad) - rect.bottom;

    if (fixX !== 0 || fixY !== 0) {
      this.currentX += fixX;
      this.currentY += fixY;
      this.applyPosition();
    }
    this.updateBubbleDirection();
  },

  startPeriodicCycle() {
    if (this.cycleTimer) clearInterval(this.cycleTimer);
    if (this.hideTimeout) clearTimeout(this.hideTimeout);

    const SHOW_MS = 7500;
    const HIDE_MS = 5000;

    // Initial show
    if (!this.isChatOpen) {
      this.showBubble();
      this.hideTimeout = setTimeout(() => {
        if (!this.isDismissedByUser && !this.isChatOpen) this.hideBubble(false);
      }, SHOW_MS);
    }

    // Recurring intermittent cycle
    this.cycleTimer = setInterval(() => {
      if (this.isChatOpen || this.isDismissedByUser) return;

      this.nextQuote(false);
      this.showBubble();

      if (this.hideTimeout) clearTimeout(this.hideTimeout);
      this.hideTimeout = setTimeout(() => {
        if (!this.isDismissedByUser && !this.isChatOpen) this.hideBubble(false);
      }, SHOW_MS);
    }, SHOW_MS + HIDE_MS);
  },

  setChatOpen(isOpen) {
    this.isChatOpen = Boolean(isOpen);
    if (this.dismissTimer) {
      clearTimeout(this.dismissTimer);
      this.dismissTimer = null;
    }
    if (this.resumeTimer) {
      clearTimeout(this.resumeTimer);
      this.resumeTimer = null;
    }
    if (this.isChatOpen) {
      this.isPaused = true;
      if (this.hideTimeout) {
        clearTimeout(this.hideTimeout);
        this.hideTimeout = null;
      }
      this.hideBubble(false);
    } else {
      this.isPaused = false;
      this.isDismissedByUser = false;
      this.showBubble();
      this.restartTimer();
    }
  },

  restartTimer() {
    if (this.hideTimeout) clearTimeout(this.hideTimeout);
    if (this.isChatOpen) return;
    this.hideTimeout = setTimeout(() => {
      if (!this.isDismissedByUser && !this.isChatOpen) this.hideBubble(false);
    }, 7500);
  },

  showBubble() {
    if (!this.bubbleEl || this.isChatOpen) return;
    this.bubbleEl.classList.remove("hidden");
    this.updateBubbleDirection();
  },

  hideBubble(dismissedByUser = false) {
    if (!this.bubbleEl) return;
    this.bubbleEl.classList.add("hidden");

    if (dismissedByUser) {
      this.isDismissedByUser = true;
      if (this.dismissTimer) clearTimeout(this.dismissTimer);
      this.dismissTimer = setTimeout(() => {
        this.isDismissedByUser = false;
        this.dismissTimer = null;
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
        this.avatarEl.style.transform = this.isFacingLeft ? "scaleX(-1)" : "";
      }, 250);
    }
  },
};
