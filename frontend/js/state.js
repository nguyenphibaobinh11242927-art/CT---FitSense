/**
 * Central State Store & Reactive Event Emitter
 */

class StateStore {
  constructor() {
    this.state = {
      user: null,
      theme: localStorage.getItem("fitsense_theme") || "dark",
      currentView: "dashboard",
      catalogMeta: null,
      weeklySchedule: null,
      workoutStats: null,
      activeWorkout: null,
    };
    this.listeners = new Map();
  }

  get(key) {
    return this.state[key];
  }

  set(key, value) {
    this.state[key] = value;
    this.emit(key, value);
  }

  subscribe(key, callback) {
    if (!this.listeners.has(key)) {
      this.listeners.set(key, new Set());
    }
    this.listeners.get(key).add(callback);
    return () => this.listeners.get(key).delete(callback);
  }

  emit(key, value) {
    if (this.listeners.has(key)) {
      this.listeners.get(key).forEach((cb) => {
        try {
          cb(value, this.state);
        } catch (e) {
          console.error(`Error in state listener for ${key}:`, e);
        }
      });
    }
  }
}

export const Store = new StateStore();
