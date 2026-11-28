/**
 * Capybara AI Assistant Chat Dialog Component (SCRUM-31 & SCRUM-32)
 * Features:
 * - Interactive Dialog Modal with smooth pop-from-capy animation
 * - Quick Prompt Chips with 1-click send & inline direct editing (✏️)
 * - Persistent chat history via localStorage
 * - Seamless integration with Action Card & 4 Dynamic SVG Expressions (SCRUM-32)
 * - 404/405 local fallback, singleton AudioContext, and companion state lock
 */

import { API } from "../api.js?v=3.0.0";
import { Toast } from "./toast.js?v=3.0.0";
import { createCapyAvatarElement, resolveCapyMood } from "./capybara_expressions.js?v=3.0.0";
import { createActionCardElement, normalizeActionCard } from "./capybara_action_card.js?v=3.0.0";

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
  headerAvatar: null,
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
    this.headerAvatar = document.getElementById("capy-header-avatar");
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
    this.syncHeaderAvatar();
  },

  updateHeaderAvatar(mood = "happy") {
    if (!this.headerAvatar) return;
    const svgAvatar = createCapyAvatarElement(mood);
    if (!svgAvatar) return;
    this.headerAvatar.classList.add("has-svg-avatar");
    this.headerAvatar.setAttribute("data-mood", svgAvatar.getAttribute("data-mood") || "happy");
    this.headerAvatar.innerHTML = "";
    this.headerAvatar.appendChild(svgAvatar);
  },

  syncHeaderAvatar() {
    for (let i = this.messages.length - 1; i >= 0; i -= 1) {
      if (this.messages[i]?.role === "assistant") {
        this.updateHeaderAvatar(resolveCapyMood(this.messages[i]));
        return;
      }
    }
    this.updateHeaderAvatar("happy");
  },

  setupEventListeners() {
    this.closeBtn?.addEventListener("click", () => this.close());
    this.clearBtn?.addEventListener("click", () => this.clearHistory());

    this.modal?.addEventListener("click", (e) => {
      if (e.target === this.modal) this.close();
    });

    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && this.isOpen) {
        this.close();
      }
    });

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
    this.syncHeaderAvatar();
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
        content: "Cuộc trò chuyện đã được làm mới! Capybara đã sẵn sàng hỗ trợ bạn. Bạn cần tư vấn bài tập hay điều chỉnh lịch tập nào? 🦫✨",
        time: this.getCurrentTime(),
        mood: "happy",
        emotion: "happy",
        actionCard: null,
      },
    ];
    this.saveMessages();
    this.renderChips();
    this.renderMessages();
    this.updateHeaderAvatar("happy");
    Toast.show("Đã làm mới đoạn chat cùng Capybara!", "info");
  },

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
        if (this.isLoading) return;
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

      const avatarBox = document.createElement("div");
      avatarBox.className = "capy-msg-avatar";

      if (isAssistant) {
        const mood = resolveCapyMood(msg);
        avatarBox.classList.add("has-svg-avatar");
        avatarBox.setAttribute("data-mood", mood);
        const svgAvatar = createCapyAvatarElement(mood);
        if (svgAvatar) {
          avatarBox.appendChild(svgAvatar);
        }
      } else {
        avatarBox.title = "Bạn";
        avatarBox.textContent = "👤";
      }

      const bubble = document.createElement("div");
      bubble.className = "capy-msg-bubble";

      const contentEl = document.createElement("div");
      contentEl.className = "capy-msg-content";
      contentEl.innerHTML = this.formatMessageContent(msg.content);
      bubble.appendChild(contentEl);

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

    this.updateHeaderAvatar("thinking");

    const row = document.createElement("div");
    row.id = "capy-typing-row";
    row.className = "capy-msg-row assistant";

    const avatarBox = document.createElement("div");
    avatarBox.className = "capy-msg-avatar has-svg-avatar";
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

      const actionCard = normalizeActionCard(res);
      const mood = resolveCapyMood({
        mood: res?.mood ?? res?.emotion,
        intent: res?.intent,
        action: res?.action ?? res?.action_required,
        reply: res?.reply,
      });

      if (actionCard) {
        this.playSuccessChime();
      }

      this.messages.push({
        role: "assistant",
        content: res?.reply || "Capybara nghe bạn rồi! 🦫✨",
        time: this.getCurrentTime(),
        mood,
        emotion: mood,
        actionCard,
      });

      this.saveMessages();
      this.renderMessages();
      this.updateHeaderAvatar(mood);
      this.scrollToBottom();
    } catch (err) {
      console.error("Capybara chat error:", err);
      this.removeTypingIndicator();
      this.messages.push({
        role: "assistant",
        content: "Capybara đang gặp chút trục trặc mạng nhỏ, nhưng đừng lo bạn cứ nghỉ ngơi một chút rồi thử lại nhé! 🦫✨",
        time: this.getCurrentTime(),
        mood: "worried",
        emotion: "worried",
        actionCard: null,
      });
      this.saveMessages();
      this.renderMessages();
      this.updateHeaderAvatar("worried");
      this.scrollToBottom();
    } finally {
      this.isLoading = false;
      if (this.sendBtn) this.sendBtn.disabled = false;
      this.input?.focus();
    }
  },

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
    safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
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