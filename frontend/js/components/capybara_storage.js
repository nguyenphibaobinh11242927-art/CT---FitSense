/**
 * Per-User Capybara Chat Storage & Async FPS-Safe Sync Helper (SCRUM-34)
 * - Isolates localStorage by normalized user identifier (never shares a global key)
 * - Cleans up legacy un-scoped key to prevent cross-account leakage
 * - Debounces async sync with idle scheduling to keep Workout MediaPipe Pose >= 25-30 FPS
 */

export const STORAGE_KEY_PREFIX = "fitsense_capy_chat_history";
const MAX_LOCAL_MESSAGES = 100;

let pendingSyncTimer = null;

export const CapybaraStorage = {
  normalizeUserKey(user) {
    if (!user) return null;
    const raw = typeof user === "string"
      ? user
      : (user.email || user.user_email || user.id || "");
    const cleaned = String(raw).trim().toLowerCase();
    return cleaned || null;
  },

  getStorageKey(userKey) {
    if (!userKey) return null;
    return `${STORAGE_KEY_PREFIX}::${userKey}`;
  },

  cleanupLegacyGlobalKey() {
    try {
      if (typeof localStorage !== "undefined") {
        localStorage.removeItem(STORAGE_KEY_PREFIX);
      }
    } catch (_) {
      // Ignore storage access restrictions
    }
  },

  readLocalHistory(userKey) {
    const key = this.getStorageKey(userKey);
    if (!key) return [];
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.slice(-MAX_LOCAL_MESSAGES) : [];
    } catch (e) {
      console.warn("Could not read per-user Capybara chat history:", e);
      return [];
    }
  },

  writeLocalHistory(userKey, messages) {
    const key = this.getStorageKey(userKey);
    if (!key || !Array.isArray(messages)) return false;
    try {
      const trimmed = messages.slice(-MAX_LOCAL_MESSAGES);
      localStorage.setItem(key, JSON.stringify(trimmed));
      return true;
    } catch (e) {
      console.warn("Could not save per-user Capybara chat history:", e);
      return false;
    }
  },

  removeLocalHistory(userKey) {
    const key = this.getStorageKey(userKey);
    if (!key) return;
    try {
      localStorage.removeItem(key);
    } catch (_) {
      // Ignore storage errors
    }
  },

  /**
   * Schedule non-blocking async work so chat persistence never competes with
   * MediaPipe Pose frames when Workout camera is active.
   */
  scheduleAsyncSync(taskFn, delayMs = 250) {
    if (pendingSyncTimer) {
      clearTimeout(pendingSyncTimer);
      pendingSyncTimer = null;
    }

    pendingSyncTimer = setTimeout(() => {
      pendingSyncTimer = null;
      const run = () => {
        Promise.resolve()
          .then(() => taskFn())
          .catch((err) => console.warn("Capybara async history sync skipped:", err));
      };

      if (typeof window !== "undefined" && typeof window.requestIdleCallback === "function") {
        window.requestIdleCallback(run, { timeout: 1000 });
      } else {
        run();
      }
    }, delayMs);
  },
};
