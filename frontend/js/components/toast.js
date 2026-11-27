/**
 * FitSense Toast Alert System
 */

export const Toast = {
  container: null,

  init() {
    if (!this.container) {
      this.container = document.createElement("div");
      this.container.className = "toast-container";
      document.body.appendChild(this.container);
    }
  },

  show(message, type = "info", duration = 3500) {
    this.init();

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    const icon = type === "success" ? "✅" : type === "error" ? "❌" : type === "warning" ? "⚠️" : "ℹ️";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;

    this.container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(-20px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  success(msg) {
    this.show(msg, "success");
  },

  error(msg) {
    this.show(msg, "error", 4500);
  },

  info(msg) {
    this.show(msg, "info");
  },

  warning(msg) {
    this.show(msg, "warning", 4500);
  },
};
