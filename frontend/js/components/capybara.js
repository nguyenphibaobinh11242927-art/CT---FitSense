/**
 * Capybara Workout Companion Component
 * Featuring Autonomous Leisure Wandering, Natural Waddle Animation,
 * Smart Responsive Speech Bubble & Free Drag-and-Drop
 */

import { API } from "../api.js";
import { VoiceAssistant } from "./voice_assistant.js";

export const Capybara = {
  element: null,
  bubbleEl: null,
  speechEl: null,
  avatarEl: null,
  closeBtn: null,
  transcriptInput: null,
  chatForm: null,
  chatLogEl: null,
  chatSendBtn: null,
  voiceStatusEl: null,
  micBtn: null,
  muteBtn: null,
  readBtn: null,
  voiceAssistant: null,
  chatMessages: [],
  chatBusy: false,
  voiceBusy: false,
  quotes: [],
  currentQuoteIdx: 0,
  cycleTimer: null,
  hideTimeout: null,
  wanderTimer: null,
  isDismissedByUser: false,
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
    this.transcriptInput = document.getElementById("capy-chat-input");
    this.chatForm = document.getElementById("capy-chat-form");
    this.chatLogEl = document.getElementById("capy-chat-log");
    this.chatSendBtn = document.getElementById("capy-chat-send");
    this.voiceStatusEl = document.getElementById("capy-voice-status");
    this.micBtn = document.getElementById("capy-mic-btn");
    this.muteBtn = document.getElementById("capy-mute-btn");
    this.readBtn = document.getElementById("capy-read-btn");

    if (!this.element || !this.speechEl || !this.avatarEl) return;

    await this.refresh();
    this.setupVoiceAssistant();
    this.setupVoiceEvents();

    if (new URLSearchParams(window.location.search).has("voiceDebug")) {
      window.CapybaraVoiceDebug = {
        assistant: this.voiceAssistant,
        report: () => {
          const report = this.voiceAssistant?.debugReport();
          console.table(report);
          return report;
        },
      };
      console.info("SCRUM-33 voice debug enabled. Run window.CapybaraVoiceDebug.report()");
    }

    // Close button ('x') handler
    this.closeBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      this.hideBubble(true);
    });

    // Setup Drag-and-Drop & Avatar Click handlers
    this.setupInteractions();

    // Bubble click (outside 'x'): cycle to next tip
    this.bubbleEl?.addEventListener("click", (e) => {
      if (e.target.closest?.(".capy-voice-controls, .capy-chat-panel")) return;
      if (e.target === this.closeBtn || this.closeBtn?.contains(e.target)) return;
      this.nextQuote(true);
      this.restartTimer();
    });

    // Start intermittent speech bubble cycle (Show 7.5s -> Hide 5s -> Repeat)
    this.startPeriodicCycle();

    // Start leisurely ambient wandering along screen bottom
    this.startWandering();
  },

  setupVoiceAssistant() {
    this.voiceAssistant = new VoiceAssistant({
      interimResults: true,
      onInterim: (text) => {
        if (!this.transcriptInput) return;
        this.transcriptInput.value = text;
        this.transcriptInput.classList.add("is-interim");
        this.syncVoiceBusy();
      },
      onTranscript: (text) => {
        if (!this.transcriptInput) return;
        this.transcriptInput.classList.remove("is-interim");
        this.transcriptInput.value = text;
        this.transcriptInput.dispatchEvent(new Event("input", {bubbles: true}));
        document.dispatchEvent(new CustomEvent("capy:transcript", {
          detail: {text, source: "voice", final: true, submit: true},
        }));
        this.showBubble();
        this.syncVoiceBusy();
        this.transcriptInput.focus();
      },
      onStatus: (message) => {
        if (this.voiceStatusEl) this.voiceStatusEl.textContent = message;
      },
      onPermissionChange: (permission) => {
        if (!this.voiceStatusEl) return;
        if (permission === "denied") {
          this.voiceStatusEl.textContent = "Quyền micro đang bị chặn. Hãy cho phép micro trong cài đặt trình duyệt.";
        } else if (permission === "granted") {
          this.voiceStatusEl.textContent = "Đã có quyền micro. Bấm nút micro để bắt đầu nghe.";
        }
      },
      onListeningChange: (listening) => {
        this.micBtn?.classList.toggle("is-listening", listening);
        this.micBtn?.setAttribute("aria-pressed", String(listening));
        this.syncVoiceBusy();
      },
      onSpeakingChange: (speaking) => {
        this.readBtn?.setAttribute("aria-pressed", String(speaking));
        if (this.readBtn) {
          this.readBtn.title = speaking ? "Dừng đọc" : "Đọc lời thoại hiện tại";
        }
        this.syncVoiceBusy();
      },
      onMuteChange: (muted) => {
        if (!this.muteBtn) return;
        this.muteBtn.textContent = muted ? "🔇" : "🔊";
        this.muteBtn.title = muted ? "Bật âm thanh Capy" : "Tắt âm thanh Capy";
        this.muteBtn.setAttribute("aria-pressed", String(muted));
      },
    });

    this.micBtn?.addEventListener("click", () => this.voiceAssistant.toggleListening());
    this.muteBtn?.addEventListener("click", () => this.voiceAssistant.toggleMute());
    this.readBtn?.addEventListener("click", () => {
      if (this.voiceAssistant.speaking) this.voiceAssistant.cancelSpeech();
      else this.voiceAssistant.speak(this.speechEl?.textContent || "");
    });
  },

  setupVoiceEvents() {
    this.chatForm?.addEventListener("submit", (event) => {
      event.preventDefault();
      void this.sendMessage(this.transcriptInput?.value);
    });
    document.addEventListener("capy:transcript", (event) => {
      if (event.detail?.source === "voice" && event.detail?.submit) {
        void this.sendMessage(event.detail.text);
      }
    });
    this.transcriptInput?.addEventListener("input", () => {
      if (this.transcriptInput.value.trim()) this.transcriptInput.classList.remove("is-interim");
      this.syncVoiceBusy();
    });
    this.transcriptInput?.addEventListener("blur", () => this.syncVoiceBusy());
    this.bubbleEl?.addEventListener("focusin", () => this.syncVoiceBusy());
    this.bubbleEl?.addEventListener("focusout", () => setTimeout(() => this.syncVoiceBusy(), 0));
    document.addEventListener("capy:schedule-changed", (event) => this.celebrate(event.detail?.message));
    window.addEventListener("pagehide", () => this.voiceAssistant?.dispose());
  },

  async sendMessage(rawText) {
    const text = String(rawText || "").trim();
    if (!text || this.chatBusy || !this.transcriptInput) return false;

    this.chatBusy = true;
    this.transcriptInput.value = "";
    this.transcriptInput.classList.remove("is-interim");
    this.transcriptInput.disabled = true;
    if (this.chatSendBtn) this.chatSendBtn.disabled = true;
    if (this.micBtn) this.micBtn.disabled = true;
    this.appendChatMessage("user", text);
    if (this.voiceStatusEl) this.voiceStatusEl.textContent = "Đang gửi tin nhắn đến Capy…";
    this.syncVoiceBusy();

    try {
      const messages = [
        ...this.chatMessages.slice(-10),
        {role: "user", content: text},
      ];
      const result = await API.capybara.chat(messages);
      const reply = typeof result?.reply === "string" ? result.reply.trim() : "";
      if (!reply) throw new Error("Capy chưa trả lời được. Vui lòng thử lại.");

      this.chatMessages.push({role: "user", content: text}, {role: "assistant", content: reply});
      if (this.chatMessages.length > 12) this.chatMessages.splice(0, this.chatMessages.length - 12);
      this.appendChatMessage("assistant", reply);
      this.setSpeech(reply);
      if (this.voiceStatusEl) this.voiceStatusEl.textContent = "Capy đã trả lời.";
      this.voiceAssistant?.speak(reply);
      return true;
    } catch (error) {
      this.appendChatMessage("error", `Không gửi được: ${error.message}`);
      if (this.transcriptInput) {
        this.transcriptInput.value = text;
        this.transcriptInput.focus();
      }
      if (this.voiceStatusEl) this.voiceStatusEl.textContent = "Tin nhắn chưa được gửi. Kiểm tra kết nối hoặc cấu hình AI rồi thử lại.";
      return false;
    } finally {
      this.chatBusy = false;
      if (this.transcriptInput) this.transcriptInput.disabled = false;
      if (this.chatSendBtn) this.chatSendBtn.disabled = false;
      if (this.micBtn) this.micBtn.disabled = false;
      this.syncVoiceBusy();
    }
  },

  appendChatMessage(role, text) {
    if (!this.chatLogEl) return;
    const message = document.createElement("div");
    message.className = `capy-chat-message capy-chat-message-${role}`;
    message.textContent = text;
    this.chatLogEl.append(message);
    while (this.chatLogEl.childElementCount > 24) this.chatLogEl.firstElementChild.remove();
    this.chatLogEl.hidden = false;
    this.chatLogEl.scrollTop = this.chatLogEl.scrollHeight;
  },

  syncVoiceBusy() {
    const va = this.voiceAssistant;
    this.voiceBusy = Boolean(
      this.chatBusy || va?.listening || va?.speaking ||
      this.transcriptInput?.value.trim() ||
      this.bubbleEl?.matches(":focus-within")
    );
    if (this.voiceBusy) {
      this.showBubble();
      if (this.hideTimeout) clearTimeout(this.hideTimeout);
    }
  },

  celebrate(message = "Mình đã đổi lịch tập xong rồi nhé!") {
    this.isDismissedByUser = false;
    this.setSpeech(message);
    this.showBubble();
    this.voiceAssistant?.playCue("schedule_done");
    this.voiceAssistant?.speak(message);
  },

  setupInteractions() {
    let startX = 0, startY = 0;
    let initialPosX = this.currentX, initialPosY = this.currentY;
    let dragDistance = 0;
    let startTime = 0;

    const onPointerDown = (e) => {
      if (e.button && e.button !== 0) return;
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
          setTimeout(() => { this.isPaused = false; }, 15000);
        } else if (elapsed < 350 && dragDistance < 6) {
          // Plain click on Capybara!
          this.isDismissedByUser = false;
          this.nextQuote(true);
          this.showBubble();
          this.restartTimer();
          setTimeout(() => { this.isPaused = false; }, 8000);
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
    this.element.addEventListener("mouseenter", () => { this.isPaused = true; });
    this.element.addEventListener("mouseleave", () => {
      if (!this.isDragging) {
        setTimeout(() => { this.isPaused = false; }, 5000);
      }
    });
  },

  startWandering() {
    if (this.wanderTimer) clearInterval(this.wanderTimer);

    // Every 22 seconds, take a walk along bottom dock
    this.wanderTimer = setInterval(() => {
      if (this.isPaused || this.isDragging || this.voiceBusy) return;
      const workoutView = document.getElementById("view-workout");
      if (workoutView && workoutView.classList.contains("active")) return;

      this.takeWalk();
    }, 22000);
  },

  takeWalk() {
    if (this.isPaused || this.isDragging || this.voiceBusy) return;

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
    this.showBubble();
    this.hideTimeout = setTimeout(() => {
      if (!this.isDismissedByUser && !this.voiceBusy) this.hideBubble(false);
    }, SHOW_MS);

    // Recurring intermittent cycle
    this.cycleTimer = setInterval(() => {
      if (this.isDismissedByUser || this.voiceBusy) return;

      this.nextQuote(false);
      this.showBubble();

      if (this.hideTimeout) clearTimeout(this.hideTimeout);
      this.hideTimeout = setTimeout(() => {
        if (!this.isDismissedByUser && !this.voiceBusy) this.hideBubble(false);
      }, SHOW_MS);
    }, SHOW_MS + HIDE_MS);
  },

  restartTimer() {
    if (this.hideTimeout) clearTimeout(this.hideTimeout);
    this.hideTimeout = setTimeout(() => {
      if (!this.isDismissedByUser && !this.voiceBusy) this.hideBubble(false);
    }, 7500);
  },

  showBubble() {
    if (!this.bubbleEl) return;
    this.bubbleEl.classList.remove("hidden");
    this.updateBubbleDirection();
  },

  hideBubble(dismissedByUser = false) {
    if (!this.bubbleEl) return;
    this.bubbleEl.classList.add("hidden");

    if (dismissedByUser) {
      this.isDismissedByUser = true;
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
        this.avatarEl.style.transform = this.isFacingLeft ? "scaleX(-1)" : "";
      }, 250);
    }
  },
};
