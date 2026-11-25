/**
 * Capybara AI Assistant Chat Dialog Component (SCRUM-31)
 * Features:
 * - Interactive Dialog Modal with smooth pop-from-capy animation
 * - Quick Prompt Chips with 1-click send & inline direct editing (✏️)
 * - Persistent chat history via localStorage
 * - Seamless integration with Action Card (SCRUM-32) & Audio Feedback
 * - Full Dark / Light Theme & Responsive Mobile Compatibility
 */

import { API } from "../api.js";
import { Toast } from "./toast.js";

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
  audioCtx: null,
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

    // Lock companion wandering & speech bubble while chat is open
    import("./capybara.js?v=3.0.0").then((m) => {
      m.Capybara?.setChatOpen?.(true);
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

    // Unlock companion & restore speech bubble cycle cleanly
    import("./capybara.js?v=3.0.0").then((m) => {
      m.Capybara?.setChatOpen?.(false);
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
          let migrated = false;
          this.messages = parsed.map((m) => {
            if (m && m.role === "assistant" && typeof m.content === "string") {
              const unified = m.content
                .replace(/\bCapy(?:Heo)?\b(?!bara)/g, "Capybara")
                .replace(/\bTớ là Capybara\b/g, "Mình là Capybara");
              if (unified !== m.content) {
                migrated = true;
                return { ...m, content: unified };
              }
            }
            return m;
          });
          if (migrated) this.saveMessages();
          return;
        }
      }
    } catch (e) {
      console.warn("Could not load Capybara chat history:", e);
    }

    // Default warm welcome greeting from Capybara
    this.messages = [
      {
        role: "assistant",
        content: "Xin chào! Mình là Capybara 🦫✨, huấn luyện viên đồng hành Calisthenics của bạn. Mình có thể giúp bạn giải đáp thắc mắc về bài tập, đổi bài an toàn khi đau chấn thương, hoặc điều chỉnh lịch tập. Bạn cần Capybara hỗ trợ gì hôm nay?",
        time: this.getCurrentTime(),
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
        content: "Cuộc trò chuyện đã được làm mới! Capybara đã sẵn sàng hỗ trợ bạn. Bạn cần tư vấn bài tập hay điều chỉnh lịch tập nào? 🦫✨",
        time: this.getCurrentTime(),
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

      // Normal state markup
      chipEl.innerHTML = `
        <span class="capy-chip-text" title="Nhấp để gửi câu hỏi này ngay">${this.escapeHtml(chip.label)}</span>
        <button type="button" class="capy-chip-edit-btn" title="Chỉnh sửa trực tiếp câu này trước khi gửi">✏️</button>
      `;

      // 1. Click text -> Send immediately
      const textSpan = chipEl.querySelector(".capy-chip-text");
      textSpan.addEventListener("click", () => {
        if (this.isLoading) return;
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
        <input type="text" class="capy-chip-edit-input" maxlength="1000" value="${this.escapeHtml(chip.prompt)}" />
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
      if (this.isLoading) return;
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
        <div class="capy-msg-avatar" title="${isAssistant ? 'Trợ lý Capybara AI' : 'Bạn'}">
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
      <div class="capy-msg-avatar" title="Trợ lý Capybara AI">🦫</div>
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

  async requestChatReply(text) {
    try {
      return await API.capybara.chat(text);
    } catch (err) {
      if (err && (err.status === 404 || err.status === 405)) {
        return this.buildLocalFallbackReply(text);
      }
      throw err;
    }
  },

  buildLocalFallbackReply(rawMessage) {
    const norm = String(rawMessage || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/gi, "d")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();

    const isNegatedOrEducational =
      /\b(?:khong (?:con |bi |thay |can )?(?:dau|nhuc|sung|doi|giam)|het (?:dau|nhuc)|dung doi|chua can|la gi|nghia la gi|co (?:lam|gay) dau)\b/.test(norm);

    if (!isNegatedOrEducational) {
      if (/\b(?:dau|nhuc|sung|chan thuong)\b/.test(norm)) {
        if (/\bgoi\b/.test(norm)) {
          return {
            intent: "INJURY_REPORT",
            action: "swap_exercise_for_injury",
            params: { joint: "knee" },
            reply: "Capybara nghe rồi. Mình có thể tìm bài thay thế phù hợp với lịch tập của bạn. 🦫✨",
          };
        }
        if (/\bco tay\b/.test(norm)) {
          return {
            intent: "INJURY_REPORT",
            action: "swap_exercise_for_injury",
            params: { joint: "wrist" },
            reply: "Capybara nghe rồi. Mình có thể tìm bài thay thế phù hợp với lịch tập của bạn. 🦫✨",
          };
        }
        if (/\bvai\b/.test(norm)) {
          return {
            intent: "INJURY_REPORT",
            action: null,
            params: { joint: "shoulder" },
            reply: "Capybara ghi nhận vùng vai đang khó chịu. Bạn nên nghỉ ngơi hoặc chọn biến thể nhẹ hơn nhé! 🦫✨",
          };
        }
        if (/\b(?:lung duoi|that lung)\b/.test(norm)) {
          return {
            intent: "INJURY_REPORT",
            action: null,
            params: { joint: "lower_back" },
            reply: "Capybara ghi nhận vùng thắt lưng đang khó chịu. Hãy ưu tiên giữ lưng trung lập và nghỉ ngơi khi cần nhé! 🦫✨",
          };
        }
        return {
          intent: "INJURY_REPORT",
          action: null,
          params: {},
          reply: "Capybara nghe rồi. Vùng nào đang đau hoặc khó chịu nhất vậy? 🦫✨",
        };
      }

      if (/\b(?:deload|giam (?:tai|khoi luong|cuong do|volume|so rep|so hiep)|tap nhe)\b/.test(norm)) {
        const pctMatch = norm.match(/(\d+(?:[.,]\d+)?)\s*(?:%|phan tram)/);
        const pct = pctMatch ? parseFloat(pctMatch[1].replace(",", ".")) : 30;
        if (pct > 0 && pct < 100) {
          return {
            intent: "RESCHEDULE_DELOAD",
            action: "apply_instant_deload",
            params: { percentage: pct / 100 },
            reply: `Capybara hiểu rồi, bạn muốn giảm tải ${pct}%. 🦫✨`,
          };
        }
        return {
          intent: "RESCHEDULE_DELOAD",
          action: null,
          params: {},
          reply: "Bạn muốn giảm tải bao nhiêu phần trăm, ví dụ 30%? 🦫✨",
        };
      }

      if (/\b(?:doi|chuyen|hoan doi|lui|hoan)\s+(?:lich|buoi|ngay|tap|thu|t[2-7]|hom nay|sang)\b/.test(norm)) {
        const dayLabels = ["Chủ Nhật", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7"];
        const todayIdx = new Date().getDay();
        const foundDays = [];
        const dayRegex = /\b(?:thu\s*([2-7]|hai|ba|tu|nam|sau|bay)|t([2-7])|(chu nhat|cn)|(hom nay)|(ngay mai|mai))\b/g;
        const wordMap = { hai: "2", ba: "3", tu: "4", nam: "5", sau: "6", bay: "7" };
        let m;
        while ((m = dayRegex.exec(norm)) !== null) {
          let label = null;
          if (m[1]) label = `Thứ ${wordMap[m[1]] || m[1]}`;
          else if (m[2]) label = `Thứ ${m[2]}`;
          else if (m[3]) label = "Chủ Nhật";
          else if (m[4]) label = dayLabels[todayIdx];
          else if (m[5] && todayIdx !== 0) label = dayLabels[(todayIdx + 1) % 7];
          if (label && !foundDays.includes(label)) foundDays.push(label);
        }
        if (foundDays.length >= 2) {
          return {
            intent: "RESCHEDULE_DELOAD",
            action: "move_workout_day",
            params: { from_day: foundDays[0], to_day: foundDays[1] },
            reply: `Capybara đã ghi nhận yêu cầu dời buổi tập từ ${foundDays[0]} sang ${foundDays[1]}. 🦫✨`,
          };
        }
        return {
          intent: "RESCHEDULE_DELOAD",
          action: null,
          params: foundDays[0] ? { from_day: foundDays[0] } : {},
          reply: "Bạn muốn dời buổi tập từ ngày nào sang ngày nào trong tuần này? 🦫✨",
        };
      }
    }

    let answer =
      "Capybara có thể giúp bạn tìm hiểu bài tập Calisthenics hoặc cách dùng Kế hoạch, Thư viện và Live HUD. Bạn muốn hỏi phần nào? 🦫✨";
    if (/\b(?:chong day|hit dat|push[ -]?up)\b/.test(norm)) {
      answer = "Khi chống đẩy, hãy giữ thân người thẳng từ đầu đến gót chân, siết bụng và hạ ngực có kiểm soát nhé! 🦫✨";
    } else if (/\b(?:thu vien|tim bai)\b/.test(norm)) {
      answer = "Mở mục Thư viện để tìm bài tập theo tên, nhóm cơ hoặc dụng cụ bạn có nhé! 🦫✨";
    } else if (/\b(?:ke hoach|lich tap)\b/.test(norm)) {
      answer = "Bạn có thể mở mục Kế hoạch để xem lịch tuần và chọn buổi muốn tập nha! 🦫✨";
    } else if (/\b(?:live hud|camera|dem rep)\b/.test(norm)) {
      answer = "Mở Phòng tập (Live HUD) rồi bật camera để AI đếm rep tự động hoặc nhập thủ công nhé! 🦫✨";
    }
    return {
      intent: "QA_FITNESS_APP",
      action: null,
      params: {},
      reply: answer,
    };
  },

  async sendMessage(rawText) {
    const text = String(rawText || "").trim().slice(0, 1000);
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
      const res = await this.requestChatReply(text);
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
        content: res.reply || "Capybara nghe bạn rồi! 🦫✨",
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
        content: "Capybara đang gặp chút trục trặc mạng nhỏ, nhưng đừng lo bạn cứ nghỉ ngơi một chút rồi thử lại nhé! 🦫✨",
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
      if (!this.audioCtx || this.audioCtx.state === "closed") {
        this.audioCtx = new AudioCtx();
      }
      const ctx = this.audioCtx;
      if (ctx.state === "suspended") {
        ctx.resume().catch(() => {});
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

        osc.onended = () => {
          osc.disconnect();
          gain.disconnect();
        };

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
