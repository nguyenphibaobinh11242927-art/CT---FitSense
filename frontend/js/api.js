/**
 * FitSense REST API Client (ES6 Module)
 * Connects Frontend SPA to FastAPI Backend Endpoints
 */

const BASE_URL = window.location.origin;

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = data.detail || `Lỗi yêu cầu: ${response.status}`;
      throw new Error(errorMsg);
    }
    return data;
  } catch (err) {
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

export const API = {
  health: () => request("/api/health"),

  auth: {
    config: () => request("/api/auth/config"),
    saveConfig: (google_client_id) => request("/api/auth/config", {
      method: "POST",
      body: JSON.stringify({ google_client_id }),
    }),
    me: () => request("/api/auth/me"),
    login: (email, password) => request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
    register: (userData) => request("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(userData),
    }),
    google: (googleData) => request("/api/auth/google", {
      method: "POST",
      body: JSON.stringify(googleData),
    }),
    googleComplete: (registrationData) => request("/api/auth/google/complete-registration", {
      method: "POST",
      body: JSON.stringify(registrationData),
    }),
    logout: () => request("/api/auth/logout", { method: "POST" }),
  },

  profile: {
    get: () => request("/api/profile"),
    update: (profile) => request("/api/profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    }),
    calculateBMI: (weight_kg, height_cm) => request("/api/profile/bmi", {
      method: "POST",
      body: JSON.stringify({ weight_kg, height_cm }),
    }),
  },

  exercises: {
    meta: () => request("/api/exercises/meta"),
    list: (params = {}) => {
      const query = new URLSearchParams(params).toString();
      return request(`/api/exercises?${query}`);
    },
    detail: (id) => request(`/api/exercises/${encodeURIComponent(id)}`),
    alternatives: (id, preferredId) => request(
      `/api/exercises/${encodeURIComponent(id)}/alternatives${preferredId ? `?preferred_id=${encodeURIComponent(preferredId)}` : ""}`,
    ),
  },

  planner: {
    getWeek: () => request("/api/planner/week"),
    generate: (goal, useAI = true) => request("/api/planner/generate", {
      method: "POST",
      body: JSON.stringify({ goal, use_ai: useAI }),
    }),
    swap: (day, currentExerciseId, newExerciseId, exerciseIndex) => request("/api/planner/swap", {
      method: "POST",
      body: JSON.stringify({
        day,
        current_exercise_id: currentExerciseId,
        new_exercise_id: newExerciseId,
        exercise_index: exerciseIndex,
      }),
    }),
    reset: () => request("/api/planner/reset", { method: "POST" }),
    template: () => request("/api/planner/template"),
    upload: (content, filename) => request("/api/planner/upload", {
      method: "POST",
      body: JSON.stringify({ content, filename }),
    }),
    updateDay: (day, focus, isRest, exercises) => request("/api/planner/update-day", {
      method: "POST",
      body: JSON.stringify({ day, focus, is_rest: isRest, exercises }),
    }),
    checkRecovery: (day) => request(`/api/planner/check-recovery/${encodeURIComponent(day)}`),
    startDayWorkout: (source_day, use_ai = true) => request("/api/planner/start-day-workout", {
      method: "POST",
      body: JSON.stringify({ source_day, use_ai }),
    }),
  },

  session: {
    model: () => request("/api/session/model"),
    start: (exerciseId, targetReps = 10, day = null) => request("/api/session/start", {
      method: "POST",
      body: JSON.stringify({ exercise_id: exerciseId, target_reps: targetReps, day }),
    }),
    sendAngle: (sessionId, angle, landmarkType = "knee", trackingInterrupted = false) => request("/api/session/fsm-rep", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, angle, landmark_type: landmarkType, tracking_interrupted: trackingInterrupted }),
    }),
    finish: ({ sessionId, exerciseId, completedReps, durationSeconds, rpe = 7, notes = "", day = null, targetReps = null }) => request("/api/session/finish", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        exercise_id: exerciseId,
        completed_reps: completedReps,
        duration_seconds: durationSeconds,
        rpe,
        feedback_notes: notes,
        day,
        target_reps: targetReps,
      }),
    }),
  },

  progress: {
    history: () => request("/api/progress/history"),
    stats: () => request("/api/progress/stats"),
    heatmap: () => request("/api/progress/heatmap"),
    analytics: (timeframe = "week") => request(`/api/progress/analytics?timeframe=${encodeURIComponent(timeframe)}`),
    evaluationMeta: () => request("/api/progress/evaluation-meta"),
    evaluations: () => request("/api/progress/evaluations"),
    submitEvaluation: (data) => request("/api/progress/evaluate", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  },

  capybara: {
    status: () => request("/api/capybara/status"),
  },
};
