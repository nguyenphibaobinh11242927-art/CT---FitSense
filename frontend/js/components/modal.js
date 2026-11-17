/**
 * FitSense Web Confirmation & Alert Pop-up Modal System
 * Thay thế cho window.confirm / window.alert mặc định của trình duyệt bằng giao diện pop-up web hiện đại.
 */

export function showConfirmModal({
  title = "Xác nhận",
  subtitle = "FitSense Assistant",
  icon = "❓",
  message = "",
  confirmText = "Đồng ý",
  cancelText = "Hủy bỏ",
  confirmClass = "btn btn-primary",
} = {}) {
  return new Promise((resolve) => {
    const modal = document.getElementById("modal-confirm");
    if (!modal) {
      resolve(window.confirm(message.replace(/<[^>]*>/g, "")));
      return;
    }

    const titleEl = document.getElementById("confirm-modal-title");
    const subEl = document.getElementById("confirm-modal-subtitle");
    const iconEl = document.getElementById("confirm-modal-icon-badge");
    const bodyEl = document.getElementById("confirm-modal-body");
    const okBtn = document.getElementById("btn-confirm-ok");
    const cancelBtn = document.getElementById("btn-confirm-cancel");
    const closeBtn = modal.querySelector(".modal-close-btn");

    if (titleEl) titleEl.textContent = title;
    if (subEl) subEl.textContent = subtitle;
    if (iconEl) iconEl.textContent = icon;

    if (bodyEl) {
      if (typeof message === "string" && message.includes("<")) {
        bodyEl.innerHTML = message;
      } else {
        bodyEl.innerHTML = String(message)
          .split("\n")
          .filter((p) => p.trim())
          .map((p) => `<p style="margin-bottom: 0.5rem;">${p}</p>`)
          .join("");
      }
    }

    if (okBtn) {
      okBtn.textContent = confirmText;
      okBtn.className = confirmClass;
    }
    if (cancelBtn) {
      cancelBtn.textContent = cancelText;
    }

    let isDone = false;
    const cleanup = (result) => {
      if (isDone) return;
      isDone = true;
      modal.classList.remove("active");
      okBtn?.removeEventListener("click", onOk);
      cancelBtn?.removeEventListener("click", onCancel);
      closeBtn?.removeEventListener("click", onCancel);
      modal.removeEventListener("click", onBackdrop);
      resolve(result);
    };

    const onOk = (e) => {
      e.stopPropagation();
      cleanup(true);
    };
    const onCancel = (e) => {
      e.stopPropagation();
      cleanup(false);
    };
    const onBackdrop = (e) => {
      if (e.target === modal) cleanup(false);
    };

    okBtn?.addEventListener("click", onOk);
    cancelBtn?.addEventListener("click", onCancel);
    closeBtn?.addEventListener("click", onCancel);
    modal.addEventListener("click", onBackdrop);

    modal.classList.add("active");
  });
}

if (typeof window !== "undefined") {
  window.showConfirmModal = showConfirmModal;
}
