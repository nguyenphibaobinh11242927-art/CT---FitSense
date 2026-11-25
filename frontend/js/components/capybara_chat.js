/**
 * Capybara AI Assistant Chat Dialog Component (SCRUM-31)
 * Features:
 * - Interactive Dialog Modal with smooth pop-from-capy animation
 * - Quick Prompt Chips with 1-click send & inline direct editing (✏️)
 * - Persistent chat history via localStorage
 * - Seamless integration with Action Card (SCRUM-32) & Audio Feedback
 * - Full Dark / Light Theme & Responsive Mobile Compatibility
 */

import { API } from "../api.js?v=3.0.0";
import { Store } from "../state.js?v=3.0.0";
import { Toast } from "./toast.js?v=3.0.0";
import { CapybaraStorage, STORAGE_KEY_PREFIX } from "./capybara_storage.js?v=3.0.0";

const STORAGE_KEY = STORAGE_KEY_PREFIX; // "fitsense_capy_chat_history" (scoped per user via CapybaraStorage)

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

// Vector SVG avatar expressions (Modular hook for SCRUM-32)
const CAPY_AVATARS = {
  happy: "🥰",
  worried: "🥺",
  thinking: "🤔",
  proud: "😎",
  default: "🦫",
};

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
  activeUserKey: null,
  _syncVersion: 0,
  _storeUnsubscribe: null,
  _listenersBound: false,

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

    CapybaraStorage.cleanupLegacyGlobalKey();

    if (!this._listenersBound) {
      this.setupEventListeners();
      this._listenersBound = true;
    }

    if (!this._storeUnsubscribe) {
      this._storeUnsubscribe = Store.subscribe("user", (user) => {
        this.setActiveUser(user);
      });
    }

    this.activeUserKey = CapybaraStorage.normalizeUserKey(Store.get("user"));
    this.loadMessages();
    this.renderChips();
    this.renderMessages();
  },

  setActiveUser(user) {
    const nextKey = CapybaraStorage.normalizeUserKey(user);
    this._syncVersion += 1;
    const version = this._syncVersion;

    if (!nextKey) {
      this.activeUserKey = null;
      this.isLoading = false;
      this.messages = [];
      if (this.isOpen) this.close();
      if (this.messagesContainer) {
        this.messagesContainer.innerHTML = "";
      }
      return;
    }

    const userChanged = nextKey !== this.activeUserKey;
    this.activeUserKey = nextKey;

    if (userChanged || this.messages.length === 0) {
      this.loadMessages();
      this.renderMessages();
    }

    // Hydrate from backend asynchronously without blocking Workout camera frames
    CapybaraStorage.scheduleAsyncSync(async () => {
      const res = await API.capybara.getHistory();
      if (version !== this._syncVersion || this.activeUserKey !== nextKey) return;
      if (res && res.authenticated && Array.isArray(res.messages) && res.messages.length > 0) {
        this.messages = res.messages;
        CapybaraStorage.writeLocalHistory(nextKey, this.messages);
        if (this.messagesContainer) {
          this.renderMessages();
          if (this.isOpen) this.scrollToBottom(false);
        }
      }
    }, 120);
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
    const cached = CapybaraStorage.readLocalHistory(this.activeUserKey);
    if (cached.length > 0) {
      this.messages = cached;
      return;
    }

    // Default warm welcome greeting from CapyHeo
    this.messages = [
      {
        role: "assistant",
        content: "Xin chào! Tớ là CapyHeo 🦫✨, huấn luyện viên đồng hành Calisthenics của bạn. Tớ có thể giúp bạn giải đáp thắc mắc về bài tập, đổi bài an toàn khi đau chấn thương, hoặc điều chỉnh lịch tập. Bạn cần Capy giúp gì hôm nay?",
        time: this.getCurrentTime(),
        emotion: "happy",
        actionCard: null,
      },
    ];
  },

  saveMessages(syncRemote = true) {
    if (!this.activeUserKey) return;
    CapybaraStorage.writeLocalHistory(this.activeUserKey, this.messages);

    if (syncRemote) {
      const userKeySnapshot = this.activeUserKey;
      const versionSnapshot = this._syncVersion;
      const messagesSnapshot = this.messages.slice();
      CapybaraStorage.scheduleAsyncSync(async () => {
        if (versionSnapshot !== this._syncVersion || this.activeUserKey !== userKeySnapshot) return;
        await API.capybara.saveHistory(messagesSnapshot);
      }, 250);
    }
  },

  clearHistory() {
    const userKeySnapshot = this.activeUserKey;
    CapybaraStorage.removeLocalHistory(userKeySnapshot);
    this.messages = [
      {
        role: "assistant",
        content: "Cuộc trò chuyện đã được làm mới! CapyHeo đã sẵn sàng hỗ trợ bạn. Bạn cần tư vấn bài tập hay điều chỉnh lịch tập nào? 🦫✨",
        time: this.getCurrentTime(),
        emotion: "happy",
        actionCard: null,
      },
    ];
    this.saveMessages(false);
    if (userKeySnapshot) {
      CapybaraStorage.scheduleAsyncSync(async () => {
        await API.capybara.clearHistory();
      }, 50);
    }
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

      // Normal state markup
      chipEl.innerHTML = `
        <span class="capy-chip-text" title="Nhấp để gửi câu hỏi này ngay">${this.escapeHtml(chip.label)}</span>
        <button type="button" class="capy-chip-edit-btn" title="Chỉnh sửa trực tiếp câu này trước khi gửi">✏️</button>
      `;

      // 1. Click text -> Send immediately
      const textSpan = chipEl.querySelector(".capy-chip-text");
      textSpan.addEventListener("click", () => {
        this.sendMessage(chip.prompt);
      });

      // 2. Click ✏️ -> Inline direct editing
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
      this.renderChips(); // Restore chips
      if (editedText) {
        this.sendMessage(editedText);
      }
    };

    const doCancel = () => {
      this.renderChips(); // Restore chips
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

    this.messages.forEach((msg) => {
      const isAssistant = msg.role === "assistant";
      const row = document.createElement("div");
      row.className = `capy-msg-row ${isAssistant ? "assistant" : "user"}`;

      // Avatar
      const avatarIcon = isAssistant
        ? (CAPY_AVATARS[msg.emotion] || CAPY_AVATARS.default)
        : "👤";

      let actionCardHtml = "";
      if (msg.actionCard) {
        actionCardHtml = this.renderActionCardHtml(msg.actionCard);
      }

      row.innerHTML = `
        <div class="capy-msg-avatar" title="${isAssistant ? 'Capybara Assistant' : 'Bạn'}">
          ${avatarIcon}
        </div>
        <div class="capy-msg-bubble">
          <div class="capy-msg-content">${this.formatMessageContent(msg.content)}</div>
          ${actionCardHtml}
          <div class="capy-msg-time">${msg.time || ""}</div>
        </div>
      `;

      // Setup action card navigation button if present
      const navBtn = row.querySelector(".action-card-btn");
      if (navBtn) {
        navBtn.addEventListener("click", () => {
          this.close();
          if (typeof window.navigateTo === "function") {
            window.navigateTo("planner", true);
          } else {
            window.location.hash = "#planner";
          }
        });
      }

      this.messagesContainer.appendChild(row);
    });
  },

  /**
   * Action Card Component HTML (SCRUM-32 Integration & Support)
   */
  renderActionCardHtml(card) {
    if (!card) return "";

    const title = card.title || "🔄 Cập nhật Kế hoạch Tập luyện";
    const badge = card.badge || "Đổi bài do chấn thương";
    const oldLabel = card.old || "Bài cũ";
    const newLabel = card.new || "Bài mới";
    const note = card.note || "Tự động tối ưu bảo vệ khớp và nhóm cơ";

    return `
      <div class="capy-action-card">
        <div class="action-card-header">
          <span class="action-badge">${this.escapeHtml(badge)}</span>
        </div>
        <div class="action-swap-row">
          <span class="action-old">${this.escapeHtml(oldLabel)}</span>
          <span class="action-arrow">➔</span>
          <span class="action-new">${this.escapeHtml(newLabel)}</span>
        </div>
        <div class="action-note">${this.escapeHtml(note)}</div>
        <button type="button" class="action-card-btn">
          <span>📋</span> Xem Kế hoạch Tuần
        </button>
      </div>
    `;
  },

  showTypingIndicator() {
    const existing = document.getElementById("capy-typing-row");
    if (existing) return;

    const row = document.createElement("div");
    row.id = "capy-typing-row";
    row.className = "capy-msg-row assistant";
    row.innerHTML = `
      <div class="capy-msg-avatar">🦫</div>
      <div class="capy-msg-bubble">
        <div class="capy-typing-indicator">
          <span class="capy-typing-dot"></span>
          <span class="capy-typing-dot"></span>
          <span class="capy-typing-dot"></span>
        </div>
      </div>
    `;
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

      let emotion = "happy";
      let actionCard = null;

      // 1. Emotion mapping
      if (res.intent === "INJURY_REPORT") {
        emotion = "worried";
      } else if (res.action === "move_workout_day" || res.action === "apply_instant_deload") {
        emotion = "thinking";
      }

      // 2. Action Card mapping (ONLY when res.action is a concrete action)
      if (res.action === "swap_exercise_for_injury") {
        const joint = res.params?.joint;
        let oldEx = "Squat (Gánh đùi)";
        let newEx = "Glute Bridge (Cầu mông)";
        let note = "Thay bài tập giảm áp lực tối đa lên khớp gối";

        if (joint === "wrist") {
          oldEx = "Standard Push-up (Chống đẩy)";
          newEx = "Forearm Plank (Plank cẳng tay)";
          note = "Thay bài tránh dồn trọng lượng gập cổ tay";
        } else if (joint === "shoulder") {
          oldEx = "Pike Push-up (Đẩy vai dốc)";
          newEx = "Incline Push-up (Chống đẩy dốc)";
          note = "Giảm tải áp lực góc xoay của khớp vai";
        } else if (joint === "lower_back") {
          oldEx = "Leg Raise (Nâng chân)";
          newEx = "Dead Bug (Bọ chết siết bụng)";
          note = "Bảo vệ đĩa đệm và cơ thắt lưng dưới";
        }

        actionCard = {
          title: "🔄 Đổi bài tập bảo vệ khớp",
          badge: "🛡️ Tránh chấn thương",
          old: oldEx,
          new: newEx,
          note: note,
        };
        this.playSuccessChime();
      } else if (res.action === "move_workout_day") {
        const fromD = res.params?.from_day || "Hôm nay";
        const toD = res.params?.to_day || "Ngày mai";

        actionCard = {
          title: "📅 Dời lịch tập luyện",
          badge: "⚡ Hoán đổi lịch tuần",
          old: fromD,
          new: toD,
          note: `Đã dời buổi tập từ ${fromD} sang ${toD} trong giáo án`,
        };
        this.playSuccessChime();
      } else if (res.action === "apply_instant_deload") {
        const pct = res.params?.percentage ? Math.round(res.params.percentage * 100) : 30;

        actionCard = {
          title: "📉 Giảm tải cường độ (Deload)",
          badge: "🌿 Hồi phục cơ bắp",
          old: "100% Khối lượng",
          new: `${100 - pct}% (Giảm ${pct}%)`,
          note: `Giảm ${pct}% số reps và hiệp để cơ thể phục hồi tốt hơn`,
        };
        this.playSuccessChime();
      }

      this.messages.push({
        role: "assistant",
        content: res.reply || "Capy nghe bạn rồi! 🦫✨",
        time: this.getCurrentTime(),
        emotion: emotion,
        actionCard: actionCard,
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
        emotion: "thinking",
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
