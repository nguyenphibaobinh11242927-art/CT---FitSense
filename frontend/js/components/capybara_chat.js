/**
 * Capybara AI Assistant Chat Dialog Component (SCRUM-31 & SCRUM-32)
 * Features:
 * - Interactive Dialog Modal with smooth pop-from-capy animation
 * - Quick Prompt Chips with 1-click send & inline direct editing (✏️)
 * - Persistent chat history via localStorage
 * - Seamless integration with Action Card & 4 Dynamic SVG Expressions (SCRUM-32)
 * - Full Dark / Light Theme & Responsive Mobile Compatibility
 */

import { API } from "../api.js";
import { Toast } from "./toast.js";
import { createCapyAvatarElement, resolveCapyMood } from "./capybara_expressions.js";
import { createActionCardElement, normalizeActionCard } from "./capybara_action_card.js";

const STORAGE_KEY = "fitsense_capy_chat_history";

const DEFAULT_CHIPS = [
  {
    id: "injury_knee",
    label: "🩹 Đau gối khi squat",
    prompt: "Tôi bị đau đầu gối khi tập squat, có bài nào thay thế không?",
  },
  {
    id: "move_day",
    label: "📅 Dời lịch sang mai",
    prompt: "Dời lịch tập hôm nay sang ngày mai giúp mình nhé",
  },
  {
    id: "deload",
    label: "📉 Giảm tải 30%",
    prompt: "Hôm nay mình hơi mệt, cho mình giảm tải 30%",
  },
  {
    id: "pushup_tips",
    label: "💪 Mẹo chống đẩy",
    prompt: "Cho mình xin mẹo kỹ thuật chống đẩy đúng cách",
  },
  {
    id: "library_info",
    label: "📚 Xem thư viện",
    prompt: "Mục Thư viện bài tập ở đâu vậy bạn?",
  },
];

export const CapybaraChat = {
  modal: null,
  dialogBox: null,
  closeBtn: null,
  clearBtn: null,
  chipsContainer: null,
  messagesContainer: null,
  form: null,
  input: null,
  sendBtn: null,
  isOpen: false,
  isLoading: false,
  messages: [],
  chips: [...DEFAULT_CHIPS],

  init() {
    this.modal = document.getElementById("modal-capybara-chat");
    this.dialogBox = document.getElementById("capy-chat-dialog-box");
    this.closeBtn = document.getElementById("btn-capy-chat-close");
    this.clearBtn = document.getElementById("btn-capy-clear-chat");
    this.chipsContainer = document.getElementById("capy-chips-list");
    this.messagesContainer = document.getElementById("capy-messages-container");
    this.form = document.getElementById("capy-chat-form");
    this.input = document.getElementById("capy-chat-input");
    this.sendBtn = document.getElementById("capy-chat-send-btn");

    if (!this.modal || !this.messagesContainer || !this.form) return;

    this.setupEventListeners();
    this.loadMessages();
    this.renderChips();
    this.renderMessages();
  },

  setupEventListeners() {
    // Close button
    this.closeBtn?.addEventListener("click", () => this.close());

    // Clear history button
    this.clearBtn?.addEventListener("click", () => this.clearHistory());

    // Backdrop click
    this.modal?.addEventListener("click", (e) => {
      if (e.target === this.modal) this.close();
    });

    // Escape key
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.isOpen) {
        this.close();
      }
    });

    // Form submission
    this.form?.addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleFormSubmit();
    });
  },

  open() {
    if (!this.modal) this.init();
    if (!this.modal) return;
    this.isOpen = true;
    this.modal.classList.add("active");

    // Hide companion speech bubble to prevent visual clutter
    import("./capybara.js?v=3.0.0").then((m) => {
      m.Capybara?.hideBubble?.(true);
      if (m.Capybara) m.Capybara.isPaused = true;
    });

    this.renderMessages();
    setTimeout(() => {
      this.scrollToBottom(false);
      this.input?.focus();
    }, 100);
  },

  close() {
    if (!this.modal) return;
    this.isOpen = false;
    this.modal.classList.remove("active");

    // Restore companion speech bubble
    import("./capybara.js?v=3.0.0").then((m) => {
      if (m.Capybara) {
        m.Capybara.isPaused = false;
        m.Capybara.showBubble?.();
      }
    });
  },

  getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  },

  loadMessages() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) {
          this.messages = parsed;
          return;
        }
      }
    } catch (e) {
      console.warn("Could not load Capybara chat history:", e);
    }

    // Default warm welcome greeting from CapyHeo
    this.messages = [
      {
        role: "assistant",
        content: "Xin chào! Tớ là CapyHeo 🦫✨, huấn luyện viên đồng hành Calisthenics của bạn. Tớ có thể giúp bạn giải đáp thắc mắc về bài tập, đổi bài an toàn khi đau chấn thương, hoặc điều chỉnh lịch tập. Bạn cần Capy giúp gì hôm nay?",
        time: this.getCurrentTime(),
        mood: "happy",
        emotion: "happy",
        actionCard: null,
      },
    ];
  },

  saveMessages() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.messages));
    } catch (e) {
      console.warn("Could not save Capybara chat history:", e);
    }
  },

  clearHistory() {
    localStorage.removeItem(STORAGE_KEY);
    this.messages = [
      {
        role: "assistant",
        content: "Cuộc trò chuyện đã được làm mới! CapyHeo đã sẵn sàng hỗ trợ bạn. Bạn cần tư vấn bài tập hay điều chỉnh lịch tập nào? 🦫✨",
        time: this.getCurrentTime(),
        mood: "happy",
        emotion: "happy",
        actionCard: null,
      },
    ];
    this.saveMessages();
    this.renderChips();
    this.renderMessages();
    Toast.show("Đã làm mới đoạn chat cùng Capybara!", "info");
  },

  /**
   * Render Quick Prompt Chips
   * - Click text: Sends immediately (1-click response)
   * - Click ✏️: Inline editing directly inside the chip widget
   */
  renderChips() {
    if (!this.chipsContainer) return;
    this.chipsContainer.innerHTML = "";

    this.chips.forEach((chip) => {
      const chipEl = document.createElement("div");
      chipEl.className = "capy-chip";
      chipEl.dataset.chipId = chip.id;

      chipEl.innerHTML = `
        <span class="capy-chip-text" title="Nhấp để gửi câu hỏi này ngay">${this.escapeHtml(chip.label)}</span>
        <button type="button" class="capy-chip-edit-btn" title="Chỉnh sửa trực tiếp câu này trước khi gửi">✏️</button>
      `;

      const textSpan = chipEl.querySelector(".capy-chip-text");
      textSpan.addEventListener("click", () => {
        this.sendMessage(chip.prompt);
      });

      const editBtn = chipEl.querySelector(".capy-chip-edit-btn");
      editBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        this.enableInlineChipEdit(chipEl, chip);
      });

      this.chipsContainer.appendChild(chipEl);
    });
  },

  /**
   * Transforms chip into an inline text editor right at its position
   */
  enableInlineChipEdit(chipEl, chip) {
    chipEl.classList.add("is-editing");
    chipEl.innerHTML = `
      <div class="capy-chip-inline-editor">
        <input type="text" class="capy-chip-edit-input" value="${this.escapeHtml(chip.prompt)}" />
        <button type="button" class="capy-chip-confirm-btn" title="Gửi câu đã sửa">✓</button>
        <button type="button" class="capy-chip-cancel-btn" title="Hủy">&times;</button>
      </div>
    `;

    const input = chipEl.querySelector(".capy-chip-edit-input");
    const confirmBtn = chipEl.querySelector(".capy-chip-confirm-btn");
    const cancelBtn = chipEl.querySelector(".capy-chip-cancel-btn");

    input.focus();
    input.select();

    const doConfirm = () => {
      const editedText = input.value.trim();
      this.renderChips();
      if (editedText) {
        this.sendMessage(editedText);
      }
    };

    const doCancel = () => {
      this.renderChips();
    };

    chipEl.addEventListener("keydown", (e) => {
      e.stopPropagation();
      if (e.key === "Escape") {
        e.preventDefault();
        doCancel();
      }
    });

    confirmBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      doConfirm();
    });

    cancelBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      doCancel();
    });

    input.addEventListener("click", (e) => {
      e.stopPropagation();
    });

    input.addEventListener("keydown", (e) => {
      e.stopPropagation();
      if (e.key === "Enter") {
        e.preventDefault();
        doConfirm();
      } else if (e.key === "Escape") {
        e.preventDefault();
        doCancel();
      }
    });
  },

  renderMessages() {
    if (!this.messagesContainer) return;
    this.messagesContainer.innerHTML = "";

    const fragment = document.createDocumentFragment();

    this.messages.forEach((msg) => {
      const isAssistant = msg.role === "assistant";
      const row = document.createElement("div");
      row.className = `capy-msg-row ${isAssistant ? "assistant" : "user"}`;

      // Avatar container (SVG expression for assistant, crisp icon for user)
      const avatarBox = document.createElement("div");
      avatarBox.className = "capy-msg-avatar";

      if (isAssistant) {
        const mood = resolveCapyMood(msg);
        avatarBox.setAttribute("data-mood", mood);
        const svgAvatar = createCapyAvatarElement(mood);
        if (svgAvatar) {
          avatarBox.appendChild(svgAvatar);
        }
      } else {
        avatarBox.title = "Bạn";
        avatarBox.textContent = "👤";
      }

      // Message bubble
      const bubble = document.createElement("div");
      bubble.className = "capy-msg-bubble";

      const contentEl = document.createElement("div");
      contentEl.className = "capy-msg-content";
      contentEl.innerHTML = this.formatMessageContent(msg.content);
      bubble.appendChild(contentEl);

      // SCRUM-32 Action Card (DOM API + textContent, zero XSS)
      if (msg.actionCard) {
        const cardEl = createActionCardElement(msg.actionCard, {
          onBeforeNavigate: () => this.close(),
        });
        if (cardEl) {
          bubble.appendChild(cardEl);
        }
      }

      const timeEl = document.createElement("div");
      timeEl.className = "capy-msg-time";
      timeEl.textContent = msg.time || "";
      bubble.appendChild(timeEl);

      row.appendChild(avatarBox);
      row.appendChild(bubble);
      fragment.appendChild(row);
    });

    this.messagesContainer.appendChild(fragment);
  },

  showTypingIndicator() {
    const existing = document.getElementById("capy-typing-row");
    if (existing) return;

    const row = document.createElement("div");
    row.id = "capy-typing-row";
    row.className = "capy-msg-row assistant";

    const avatarBox = document.createElement("div");
    avatarBox.className = "capy-msg-avatar";
    avatarBox.setAttribute("data-mood", "thinking");
    const thinkingAvatar = createCapyAvatarElement("thinking");
    if (thinkingAvatar) {
      avatarBox.appendChild(thinkingAvatar);
    }

    const bubble = document.createElement("div");
    bubble.className = "capy-msg-bubble";
    bubble.innerHTML = `
      <div class="capy-typing-indicator">
        <span class="capy-typing-dot"></span>
        <span class="capy-typing-dot"></span>
        <span class="capy-typing-dot"></span>
      </div>
    `;

    row.appendChild(avatarBox);
    row.appendChild(bubble);
    this.messagesContainer.appendChild(row);
    this.scrollToBottom();
  },

  removeTypingIndicator() {
    const existing = document.getElementById("capy-typing-row");
    if (existing) existing.remove();
  },

  scrollToBottom(smooth = true) {
    if (!this.messagesContainer) return;
    this.messagesContainer.scrollTo({
      top: this.messagesContainer.scrollHeight,
      behavior: smooth ? "smooth" : "auto",
    });
  },

  handleFormSubmit() {
    const text = this.input?.value.trim();
    if (!text || this.isLoading) return;
    this.input.value = "";
    this.sendMessage(text);
  },

  async sendMessage(text) {
    if (!text || this.isLoading) return;

    // 1. Add user message
    this.messages.push({
      role: "user",
      content: text,
      time: this.getCurrentTime(),
    });
    this.saveMessages();
    this.renderMessages();
    this.scrollToBottom();

    this.isLoading = true;
    if (this.sendBtn) this.sendBtn.disabled = true;
    this.showTypingIndicator();

    try {
      const res = await API.capybara.chat(text);
      this.removeTypingIndicator();

      const actionCard = normalizeActionCard(res);
      const mood = resolveCapyMood({
        mood: res?.mood ?? res?.emotion,
        intent: res?.intent,
        action: res?.action,
        reply: res?.reply,
        userMessage: text,
      });

      if (actionCard) {
        this.playSuccessChime();
      }

      this.messages.push({
        role: "assistant",
        content: res?.reply || "Capy nghe bạn rồi! 🦫✨",
        time: this.getCurrentTime(),
        mood,
        emotion: mood,
        actionCard,
      });

      this.saveMessages();
      this.renderMessages();
      this.scrollToBottom();
    } catch (err) {
      console.error("Capybara chat error:", err);
      this.removeTypingIndicator();
      this.messages.push({
        role: "assistant",
        content: "Capy đang gặp chút trục trặc mạng nhỏ, nhưng đừng lo bạn cứ nghỉ ngơi một chút rồi thử lại nhé! 🦫✨",
        time: this.getCurrentTime(),
        mood: "worried",
        emotion: "worried",
        actionCard: null,
      });
      this.saveMessages();
      this.renderMessages();
      this.scrollToBottom();
    } finally {
      this.isLoading = false;
      if (this.sendBtn) this.sendBtn.disabled = false;
      this.input?.focus();
    }
  },

  /**
   * Sound effect: Celebratory chime synthesized via Web Audio API
   * Played ONLY when Capy performs a workout reschedule/action
   */
  playSuccessChime() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      if (ctx.state === "suspended") {
        ctx.resume();
      }

      const now = ctx.currentTime;
      // High pleasant notes: C5 (523.25Hz), E5 (659.25Hz), G5 (783.99Hz)
      const freqs = [523.25, 659.25, 783.99];
      freqs.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        osc.type = "sine";
        osc.frequency.setValueAtTime(freq, now + idx * 0.1);

        gain.gain.setValueAtTime(0, now + idx * 0.1);
        gain.gain.linearRampToValueAtTime(0.16, now + idx * 0.1 + 0.025);
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.1 + 0.28);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now + idx * 0.1);
        osc.stop(now + idx * 0.1 + 0.3);
      });
    } catch (e) {
      console.warn("Could not play Capybara chime:", e);
    }
  },

  formatMessageContent(content) {
    if (!content) return "";
    let safe = this.escapeHtml(content);
    // Format bold **text**
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Format newlines
    safe = safe.replace(/\n/g, "<br/>");
    return safe;
  },

  escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  },
};