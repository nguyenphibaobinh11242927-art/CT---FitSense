/**
 * FitSense Live Workout HUD & AI Vision View
 * Full MediaPipe Pose Tracking (Skeleton & Joints), Live Joint Angles, Real Webcam & Video Upload
 */

import { API } from "../api.js";
import { Toast } from "../components/toast.js";
import { createVoiceCoach } from "/assets/webcam/voice_coach.mjs?v=voice-feedback-1";
import { createCameraPositionMonitor, POSITION_MESSAGES } from "../camera_position.mjs";

// Helper: Calculate joint angle in degrees from three 2D/3D points [0, 180]
function angleAt(a, b, c) {
  if (!a || !b || !c) return null;
  const ux = a.x - b.x, uy = a.y - b.y;
  const vx = c.x - b.x, vy = c.y - b.y;
  if ((!ux && !uy) || (!vx && !vy)) return null;
  return Math.atan2(Math.abs(ux * vy - uy * vx), ux * vx + uy * vy) * (180 / Math.PI);
}

function usesElbowAngle(exerciseId) {
  return /push_?up|dip|pull|row|chin|arm|chest|press|hit_dat|chong_day/.test(
    (exerciseId || "").toLowerCase()
  );
}

// MediaPipe Pose Connections (33 standard landmark bones)
const POSE_BONES = [
  // Torso
  [11, 12], [11, 23], [12, 24], [23, 24],
  // Left arm
  [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
  // Right arm
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
  // Left leg
  [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
  // Right leg
  [24, 26], [26, 28], [28, 30], [28, 32], [30, 32],
  // Face outline
  [0, 1], [1, 2], [2, 3], [3, 7], [0, 4], [4, 5], [5, 6], [6, 8], [9, 10]
];

// SCRUM-19: Standard Default Session Exercises for Up Next List & Rest Timer
const DEFAULT_SESSION_EXERCISES = [
  {
    id: "squat",
    name: "Squat Thể dục (Bodyweight)",
    sets: 3,
    reps: 12,
    rest_sec: 60,
    primary_muscle: "Đùi trước & Mông",
    secondary_muscle: "Core",
    difficulty: "Beginner",
    substitute: "Wall Squat (Tựa tường)",
    substitute_id: "wall_squat",
    form_tip: "Giữ lưng thẳng, hạ đùi song song sàn, gối không chụm vào trong.",
  },
  {
    id: "pushup",
    name: "Chống đẩy (Push-up)",
    sets: 3,
    reps: 10,
    rest_sec: 60,
    primary_muscle: "Ngực & Tay sau",
    secondary_muscle: "Cơ vai",
    difficulty: "Beginner",
    substitute: "Knee Push-up (Chống đẩy quỳ gối)",
    substitute_id: "knee_pushup",
    form_tip: "Thân người tạo thành một đường thẳng, siết chặt cơ bụng và mông.",
  },
  {
    id: "plank",
    name: "Plank Tĩnh (Core Plank)",
    sets: 3,
    reps: 30,
    rest_sec: 45,
    primary_muscle: "Cơ bụng & Lõi (Core)",
    secondary_muscle: "Cơ vai",
    difficulty: "Beginner",
    substitute: "Knee Plank (Plank quỳ gối)",
    substitute_id: "knee_plank",
    form_tip: "Khuỷu tay vuông góc dưới vai, không võng thắt lưng hoặc nhô mông.",
  },
];

// Singleton detector & model bytes
let poseDetectorInstance = null;
let isDetectorLoading = false;
let cachedModelBytes = null;

async function loadModelBuffer() {
  if (cachedModelBytes) return cachedModelBytes;
  try {
    const res = await fetch("/models/pose_landmarker_lite.task");
    if (res.ok) {
      cachedModelBytes = new Uint8Array(await res.arrayBuffer());
      return cachedModelBytes;
    }
  } catch (e) {
    console.debug("Direct model task fetch fallback to API:", e);
  }

  try {
    const apiRes = await API.session.model();
    if (apiRes && apiRes.model) {
      cachedModelBytes = Uint8Array.from(atob(apiRes.model), (c) => c.charCodeAt(0));
      return cachedModelBytes;
    }
  } catch (e2) {
    console.error("Base64 model fetch failed:", e2);
  }
  return null;
}

async function getPoseDetector() {
  if (poseDetectorInstance) return poseDetectorInstance;
  if (isDetectorLoading) return null;
  isDetectorLoading = true;

  try {
    const { FilesetResolver, PoseLandmarker } = await import("/assets/webcam/vendor/mediapipe/vision_bundle.mjs");
    const wasmUrl = new URL("/assets/webcam/vendor/mediapipe/wasm", window.location.origin).href;
    const wasmFiles = await FilesetResolver.forVisionTasks(wasmUrl);

    const modelBytes = await loadModelBuffer();
    if (!modelBytes) throw new Error("Could not load pose landmarker model.");

    let detector = null;
    try {
      detector = await PoseLandmarker.createFromOptions(wasmFiles, {
        baseOptions: { modelAssetBuffer: modelBytes.slice(), delegate: "GPU" },
        runningMode: "VIDEO",
        numPoses: 1,
      });
    } catch (gpuErr) {
      console.warn("GPU delegate not supported, fallback to CPU:", gpuErr);
      detector = await PoseLandmarker.createFromOptions(wasmFiles, {
        baseOptions: { modelAssetBuffer: modelBytes.slice() },
        runningMode: "VIDEO",
        numPoses: 1,
      });
    }

    poseDetectorInstance = detector;
    console.log("⚡ MediaPipe PoseLandmarker initialized successfully!");
    return poseDetectorInstance;
  } catch (err) {
    console.error("PoseLandmarker init error:", err);
    return null;
  } finally {
    isDetectorLoading = false;
  }
}

export const WorkoutView = {
  sessionId: null,
  workoutMode: "ai",
  modeSessions: new Map(),
  modeRequest: null,
  sessionStartRequest: null,
  sessionClosed: false,
  sessionClosing: false,
  frameId: 0,
  manualSetReps: new Map(),
  exerciseId: "squat",
  exerciseName: "Bodyweight Squat",
  targetReps: 12,
  holdSeconds: 0,
  restSeconds: 60,
  day: null,

  // SCRUM-19: Multi-Exercise Session & Sets Tracking
  exerciseList: [],
  currentExerciseIdx: 0,
  currentSet: 1,
  totalSets: 3,

  // SCRUM-19: Rest Timer & Web Audio State
  restDurationSec: 60,
  restRemainingSec: 60,
  isResting: false,
  restTimerInterval: null,
  setCompletionTimer: null,
  restSoundPlayed: { 3: false, 2: false, 1: false, 0: false },
  audioCtx: null,
  onRestFinishCallback: null,

  repCount: 0,
  currentAngle: 175,
  currentDepthPct: 0,
  currentState: "STATE_UP",
  isWorkingOut: false,
  isCameraRunning: false,
  videoSourceType: "none", // 'none' | 'camera' | 'file'
  videoFileName: "",
  voiceCoach: null,
  statusSpeech: null,
  poseRequest: null,
  poseSwitchRequest: null,
  poseEpoch: 0,
  poseTrackingLost: false,
  positionMonitor: null,

  videoEl: null,
  canvasEl: null,
  ctx: null,
  stream: null,
  activeVideoUrl: null,
  animationLoopId: null,

  // Technical FPS tracker
  frameCount: 0,
  lastFpsTime: 0,

  // SCRUM-19: Real-time Camera Pose & Standing Position Warnings (Yêu cầu 30 & 38)
  posePositionWarning: null, // null | 'too_close' | 'bad_angle' | 'out_of_frame'
  poseWarningCandidate: null,
  poseWarningCandidateTime: 0,
  lastSpokenWarning: null,
  lastSpokenWarningTime: 0,

  // SCRUM-16 & SCRUM-19: Dual Gesture - Crossed Wrists 'X' to finish set & start rest timer
  xGestureStartTime: null,
  xGestureTriggered: false,

  sessionStartTime: 0,
  sessionTimerInterval: null,
  restCountdownTimer: null,

  // Web Audio Context & Oscillator Synthesizer for 3-2-1 Beeps and Finish Chime
  getAudioContext() {
    if (!this.audioCtx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.audioCtx = new AudioCtx();
    }
    if (this.audioCtx && this.audioCtx.state === "suspended") {
      this.audioCtx.resume();
    }
    return this.audioCtx;
  },

  playBeep(freq = 600, duration = 0.2, type = "sine") {
    try {
      const ctx = this.getAudioContext();
      if (!ctx) return;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.25, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      console.debug("Audio beep error:", e);
    }
  },

  playChime() {
    try {
      [523.25, 659.25, 783.99, 1046.50].forEach((freq, idx) => {
        setTimeout(() => this.playBeep(freq, 0.4, "triangle"), idx * 110);
      });
    } catch (e) {
      console.debug("Chime error:", e);
    }
  },

  async render(forceRefresh = false) {
    const container = document.getElementById("view-workout");
    if (!container) return;
    this.voiceCoach ??= createVoiceCoach({
      AudioContext: window.AudioContext ?? window.webkitAudioContext,
      showCue: () => {},
      showStatus: text => {
        const status = document.getElementById("voice-playback-status");
        if (status) status.textContent = text;
      },
      onEnabledChange: () => this.updateVoiceToggle(),
    });
    this.positionMonitor ??= createCameraPositionMonitor({
      onChange: warning => {
        const notice = document.getElementById("camera-position-warning");
        if (!notice) return;
        notice.hidden = !warning;
        notice.textContent = warning ? `⚠️ ${POSITION_MESSAGES[warning]}` : "";
      },
      remind: warning => {
        if (this.statusSpeech) return false;
        return this.voiceCoach.warnPosition(warning);
      },
    });

    if (!forceRefresh && container.children.length > 0) {
      return;
    }

    container.innerHTML = `
      <div class="workout-hud-container">
        <!-- Top HUD Bar -->
        <div class="hud-topbar">
          <div class="hud-ex-info">
            <div style="display: flex; align-items: center; gap: 0.65rem; flex-wrap: wrap;">
              <h3 id="hud-exercise-title">🏋️ <span id="hud-exercise-title-text">${this.exerciseName}</span></h3>
              <span class="badge badge-primary" id="hud-set-badge" style="font-weight: 800; font-size: 0.85rem; padding: 0.25rem 0.75rem; border-radius: var(--radius-full);">
                Hiệp ${this.currentSet}/${this.totalSets}
              </span>
              <button class="btn btn-outline btn-xs" id="btn-top-skip-ex" style="border-radius: var(--radius-full);" title="Bỏ qua bài này và sang bài kế tiếp trong Up Next list">
                ⏭️ Bỏ qua bài
              </button>
            </div>
            <span class="hud-ex-target" id="hud-target-text">Mục tiêu: ${this.targetReps} reps${this.holdSeconds ? ` · Giữ ${this.holdSeconds}s mỗi rep` : ""} · Nghỉ ${this.restSeconds}s</span>
          </div>

          <!-- Mode Switcher Pills (Rounded, user-requested names) -->
          <div class="mode-pills-container">
            <button class="btn btn-mode-pill active" id="btn-mode-camera">
              Camera Rảnh tay
            </button>
            <button class="btn btn-mode-pill" id="btn-mode-manual">
              Không dùng Camera
            </button>
          </div>

          <div class="hud-metrics-row">
            <div class="hud-metric-box">
              <span class="label">Thời gian</span>
              <span class="val" id="hud-timer">00:00</span>
            </div>
            <div class="hud-metric-box">
              <span class="label">Calo ước tính</span>
              <span class="val" id="hud-calories">0.0 kcal</span>
            </div>
            <div class="hud-metric-box">
              <span class="label">Góc đo</span>
              <span class="val" id="hud-angle-val">175°</span>
            </div>
          </div>
        </div>

        <!-- Main Viewport Grid -->
        <div class="hud-viewport-grid">
          <!-- Left Column: Stage, Rest Overlay, Tech Metrics & Up Next List -->
          <div style="display: flex; flex-direction: column; width: 100%;">
            <p id="camera-position-warning" role="status" hidden style="color:var(--accent-amber); padding:0.75rem 1rem;"></p>
            <!-- Video / Stage Area -->
            <div class="hud-stage" id="hud-stage">
              <!-- Raw Video (Hidden, frames drawn onto Canvas with skeleton) -->
              <video id="hud-video" playsinline muted style="display: none;"></video>
              <canvas class="hud-canvas-el" id="hud-canvas"></canvas>

              <!-- Cyber HUD Top Overlays -->
              <div class="hud-overlay-top" id="hud-overlay-top">
                <div class="hud-live-tag" id="hud-live-tag">
                  <span class="status-dot" style="background: #fff; width: 6px; height: 6px;"></span>
                  <span id="hud-live-text">AI VISION READY</span>
                </div>

                <!-- X Gesture Hold Progress Indicator (Dual-Gesture Control) -->
                <div class="hud-x-gesture-pill" id="hud-x-indicator" style="display: none;">
                  <span class="x-pill-icon">🙅</span>
                  <div class="x-pill-body">
                    <div class="x-pill-label">
                      <span>Bắt chéo tay chữ X:</span>
                      <strong id="x-gesture-time">1.5s</strong>
                    </div>
                    <div class="x-pill-bar">
                      <div class="x-pill-fill" id="x-gesture-fill"></div>
                    </div>
                  </div>
                </div>

                <div class="hud-gesture-badge">
                  <span>🤖 FSM: <b id="hud-fsm-badge">STATE_UP</b></span>
                </div>
              </div>

              <!-- Form Coach Banner (Camera/Video AI mode only, hidden on standby/manual) -->
              <div class="hud-coach-banner" id="hud-coach-banner" style="display: none;">
                🎯 Chuẩn bị sẵn sàng: Đứng thẳng trước camera để bắt đầu
              </div>

              <!-- SCRUM-19: Cyber HUD Rest Timer Overlay (Glassmorphism on Stage) -->
              <div class="hud-rest-overlay" id="hud-rest-overlay" style="display: none;">
                <div class="rest-timer-box">
                  <div class="rest-header">
                    <span class="rest-badge-pulse">⏱️ ĐỒNG HỒ NGHỈ GIỮA HIỆP (REST TIMER)</span>
                    <span class="rest-target-label" id="rest-next-info">Chuẩn bị: Hiệp ${this.currentSet + 1}/${this.totalSets} — ${this.exerciseName}</span>
                  </div>

                  <div class="rest-countdown-display" id="rest-countdown-val">01:00</div>

                  <div class="rest-progress-track">
                    <div class="rest-progress-fill" id="rest-progress-bar"></div>
                  </div>

                  <div class="rest-quick-adjust-row">
                    <button class="btn btn-outline btn-sm rest-adj-btn" id="btn-rest-minus-15" title="Giảm 15 giây nghỉ">-15s</button>
                    <button class="btn btn-outline btn-sm rest-preset-btn" data-sec="30">30s</button>
                    <button class="btn btn-outline btn-sm rest-preset-btn" data-sec="45">45s</button>
                    <button class="btn btn-outline btn-sm rest-preset-btn" data-sec="60">60s</button>
                    <button class="btn btn-outline btn-sm rest-preset-btn" data-sec="90">90s</button>
                    <button class="btn btn-outline btn-sm rest-adj-btn" id="btn-rest-plus-15" title="Nghỉ thêm 15 giây">+15s</button>
                  </div>

                  <div class="rest-actions-row">
                    <button class="btn btn-emerald btn-skip-rest" id="btn-skip-rest-now">
                      ⏭️ Vào hiệp ngay
                    </button>
                  </div>

                  <div class="rest-tip-note">
                    💧 <b>Mẹo phục hồi:</b> Hít sâu bằng mũi, thở chậm bằng miệng, uống từng ngụm nước nhỏ.
                  </div>
                </div>
              </div>

              <!-- Stage Standby / Hero Card (Prominent Call to Action) -->
              <div class="stage-standby-overlay" id="stage-standby">
                <div class="standby-icon-pulse">
                  <span style="font-size: 2.5rem;">📹</span>
                </div>
                <h3 class="standby-title">Màn hình Giám sát Chuyển động AI (Live Feed)</h3>
                <p class="standby-desc">
                  Bật camera trực tiếp hoặc tải file video bài tập lên để AI tự động vẽ khớp, đo góc chuyển động và đếm số rep.
                </p>

                <!-- Setup Guide: Hướng dẫn vị trí đứng & góc máy chuẩn (Phương án 1 - Yêu cầu 30 & 38) -->
                <div class="standby-camera-guide">
                  <div class="camera-guide-item">
                    <span class="guide-icon">📏</span>
                    <div class="guide-text">
                      <strong>Khoảng cách 2.0m – 2.5m</strong>
                      <small>Đứng lùi lại để camera thấy trọn vẹn từ đầu đến chân</small>
                    </div>
                  </div>
                  <div class="camera-guide-item">
                    <span class="guide-icon">📐</span>
                    <div class="guide-text">
                      <strong>Góc quay nghiêng 45°–90°</strong>
                      <small>Đặt máy ngang ngực/thắt lưng; xoay nghiêng để thấy rõ khớp</small>
                    </div>
                  </div>
                  <div class="camera-guide-item">
                    <span class="guide-icon">💡</span>
                    <div class="guide-text">
                      <strong>Ánh sáng rõ nét</strong>
                      <small>Tránh đứng ngược sáng; đảm bảo đủ sáng cho camera</small>
                    </div>
                  </div>
                  <div class="camera-guide-item">
                    <span class="guide-icon">🙅</span>
                    <div class="guide-text">
                      <strong>Cử chỉ chữ X rảnh tay</strong>
                      <small>Bắt chéo 2 tay trước ngực 1.5s để kết thúc hiệp và nghỉ</small>
                    </div>
                  </div>
                </div>

                <div class="standby-btn-group">
                  <button class="btn btn-emerald btn-hero-camera" id="btn-hero-camera">
                    📷 Bật Camera Trực tiếp
                  </button>
                  <button class="btn btn-outline btn-hero-upload" id="btn-hero-upload">
                    📁 Tải lên Video bài tập
                  </button>
                </div>
                <input type="file" id="video-file-input" accept="video/mp4,video/webm,video/ogg,video/quicktime,video/*" style="display: none;" />
              </div>

              <!-- Manual Workout Panel (No Camera Mode - Isolated and Clean) -->
              <div class="manual-mode-panel" id="manual-panel">
                <div class="manual-icon">📝</div>
                <h3 class="manual-title">Chế độ Không dùng Camera</h3>
                <div class="manual-meta-row">
                  <span class="badge badge-primary" id="manual-set-badge">
                    Hiệp ${this.currentSet}/${this.totalSets}
                  </span>
                  <span class="manual-meta-ex-name" id="manual-ex-name-label">
                    ${this.exerciseName}
                  </span>
                </div>

                <div class="manual-card-box">
                  <div class="manual-reps-label">SỐ REPS HIỆP NÀY</div>
                  <div id="manual-rep-counter">0</div>
                  <div id="manual-target-label">Mục tiêu: ${this.targetReps} reps</div>
                </div>

                <div class="manual-rep-buttons-row">
                  <button class="btn btn-outline manual-rep-btn" id="btn-manual-rep-minus">➖ 1 Rep</button>
                  <button class="btn btn-primary manual-rep-btn" id="btn-manual-rep-plus1">➕ 1 Rep</button>
                  <button class="btn btn-primary manual-rep-btn" id="btn-manual-rep-plus5" style="background: var(--accent-emerald); border-color: var(--accent-emerald);">➕ 5 Reps</button>
                  <button class="btn btn-outline manual-rep-btn" id="btn-manual-rep-reset">🔄 Reset</button>
                </div>

                <div class="manual-actions-row">
                  <button class="btn btn-emerald manual-action-btn" id="btn-manual-finish-set">
                    ✅ Hoàn thành hiệp
                  </button>
                  <button class="btn btn-outline manual-action-btn" id="btn-manual-trigger-rest">
                    ⏱️ Bật nghỉ (${this.restDurationSec}s)
                  </button>
                  <button class="btn btn-outline manual-action-btn" id="btn-manual-finish-workout">
                    🏁 Kết thúc buổi tập
                  </button>
                </div>
              </div>
            </div>

            <!-- Live Technical Metrics Bar (Exact matching the Old Web format) -->
            <div class="hud-tech-metrics-panel" id="hud-tech-metrics">
              <div class="tech-metrics-header">
                <div style="display: flex; align-items: center; gap: 0.6rem;">
                  <span style="font-size: 0.95rem;">⚙️</span>
                  <strong style="font-size: 0.85rem; color: var(--text-primary);">Thông số Kỹ thuật AI Thời gian thực (Live Joints)</strong>
                  <span class="badge badge-beginner" style="font-size: 0.72rem; padding: 0.15rem 0.55rem;" id="tech-fps-badge">FPS: —</span>
                </div>
                <div style="font-size: 0.82rem; color: var(--accent-cyan); font-weight: 600;" id="tech-ai-status">
                  Sẵn sàng bật camera hoặc tải video.
                </div>
              </div>

              <div class="tech-joints-grid">
                <div class="joint-reading-card">
                  <span class="joint-name">💪 Khuỷu trái</span>
                  <span class="joint-val" id="val-elbow-left">—</span>
                </div>
                <div class="joint-reading-card">
                  <span class="joint-name">💪 Khuỷu phải</span>
                  <span class="joint-val" id="val-elbow-right">—</span>
                </div>
                <div class="joint-reading-card">
                  <span class="joint-name">🦵 Gối trái</span>
                  <span class="joint-val" id="val-knee-left">—</span>
                </div>
                <div class="joint-reading-card">
                  <span class="joint-name">🦵 Gối phải</span>
                  <span class="joint-val" id="val-knee-right">—</span>
                </div>
              </div>
            </div>

            <!-- SCRUM-19: Up Next List Panel (Danh sách bài tập hôm nay) -->
            <div class="hud-up-next-panel" id="hud-up-next-panel">
              <div class="up-next-header">
                <div style="display: flex; align-items: center; gap: 0.65rem;">
                  <span style="font-size: 1.15rem;">📋</span>
                  <h4 style="font-size: 1.05rem; font-weight: 800; color: var(--text-primary); margin: 0;">
                    Danh sách Bài tập Hôm nay (Up Next List)
                  </h4>
                  <span class="badge badge-info" id="up-next-progress-badge">Bài 1/3</span>
                </div>
                <div style="font-size: 0.82rem; color: var(--text-muted);">
                  Tự động chuyển bài khi xong đủ ${this.totalSets} hiệp
                </div>
              </div>

              <div class="up-next-list" id="up-next-cards-container">
                <!-- Dynamically rendered via renderUpNextListUI() -->
              </div>
            </div>
          </div>

          <!-- Right Column: HUD Sidebar Controls -->
          <div class="hud-sidebar">
            <!-- Rep Dial Card -->
            <div class="rep-dial-card">
              <div class="rep-circle-wrap">
                <svg class="rep-circle-svg" viewBox="0 0 160 160">
                  <defs>
                    <linearGradient id="cyanEmeraldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stop-color="#38bdf8" />
                      <stop offset="100%" stop-color="#4ade80" />
                    </linearGradient>
                  </defs>
                  <circle class="rep-circle-bg" cx="80" cy="80" r="70" />
                  <circle class="rep-circle-progress" id="rep-progress-circle" cx="80" cy="80" r="70" />
                </svg>
                <div class="rep-counter-number">
                  <span class="rep-num" id="hud-rep-count">0</span>
                  <span class="rep-label">/ ${this.targetReps} REPS</span>
                </div>
              </div>

              <!-- Depth Progress Bar -->
              <div class="angle-depth-meter">
                <div class="angle-row">
                  <span>Độ sâu bài tập</span>
                  <strong id="hud-depth-percent">0%</strong>
                </div>
                <div class="depth-bar-bg">
                  <div class="depth-bar-fill" id="hud-depth-bar"></div>
                </div>
              </div>
            </div>

            <!-- Actions Card -->
            <div class="hud-actions-card">
              <!-- Primary Action: Finish set & Trigger Rest Timer -->
              <button class="btn btn-emerald" id="btn-sidebar-finish-set" style="font-weight: 800; padding: 0.85rem 1rem; box-shadow: 0 0 16px rgba(74, 222, 128, 0.3);">
                ✅ Hoàn thành hiệp
              </button>

              <button class="btn btn-outline" id="btn-sidebar-trigger-rest" style="font-weight: 700;">
                ⏱️ Bật đồng hồ nghỉ (${this.restDurationSec}s)
              </button>

              <button class="btn btn-outline" id="btn-toggle-workout" style="font-weight: 700;">
                ⏸️ Tạm dừng tập
              </button>

              <div class="hud-actions-row">
                <button class="btn btn-outline" style="flex: 1; font-weight: 700;" id="btn-toggle-camera">
                  📷 Bật Camera
                </button>
                <button class="btn btn-outline" style="flex: 1; font-weight: 700;" id="btn-sidebar-upload-video">
                  📁 Tải Video
                </button>
              </div>

              <button type="button" class="voice-coach-toggle" id="btn-toggle-voice" aria-pressed="false">
                <span style="font-weight: 600;"><span id="voice-toggle-icon" aria-hidden="true">🔇</span> HLV Giọng nói Tiếng Việt</span>
                <span class="badge" id="voice-status-tag">TẮT</span>
              </button>
              <small id="voice-playback-status" role="status"></small>

              <button class="btn btn-primary" id="btn-finish-workout" style="margin-top: 0.5rem; font-weight: 700;">
                🏁 Hoàn thành buổi tập
              </button>
              <button class="btn btn-outline" id="btn-abandon-workout" style="margin-top: 0.5rem;">
                Bỏ dở buổi tập
              </button>
            </div>
          </div>
        </div>
      </div>
    `;

    this.videoEl = container.querySelector("#hud-video");
    this.canvasEl = container.querySelector("#hud-canvas");
    this.ctx = this.canvasEl?.getContext("2d");

    // Pre-warm detector in background
    getPoseDetector().catch((e) => console.debug("Detector warming:", e));

    this.bindEvents();
  },

  bindEvents() {
    const container = document.getElementById("view-workout");
    if (!container) return;

    // Toggle workout start/pause
    container.querySelector("#btn-toggle-workout")?.addEventListener("click", () => {
      if (this.isWorkingOut) {
        this.pauseWorkout();
      } else {
        this.startWorkout();
      }
    });

    // Camera buttons
    const handleCameraClick = () => {
      if (this.videoSourceType === "camera") {
        this.stopVideoSource();
      } else {
        this.startCamera();
      }
    };
    container.querySelector("#btn-hero-camera")?.addEventListener("click", handleCameraClick);
    container.querySelector("#btn-toggle-camera")?.addEventListener("click", handleCameraClick);

    // Video Upload buttons
    const fileInput = container.querySelector("#video-file-input");
    const handleUploadClick = () => fileInput?.click();
    container.querySelector("#btn-hero-upload")?.addEventListener("click", handleUploadClick);
    container.querySelector("#btn-sidebar-upload-video")?.addEventListener("click", handleUploadClick);

    fileInput?.addEventListener("change", (e) => {
      const file = e.target.files?.[0];
      if (file) {
        this.loadVideoFile(file);
      }
      fileInput.value = "";
    });

    // Toggle Voice Coach
    this.updateVoiceToggle();
    container.querySelector("#btn-toggle-voice")?.addEventListener("click", () => {
      this.stopStatusSpeech();
      this.voiceCoach.toggle();
    });

    // Finish Workout
    container.querySelector("#btn-finish-workout")?.addEventListener("click", () => {
      this.finishWorkout();
    });
    container.querySelector("#btn-abandon-workout")?.addEventListener("click", () => {
      this.finishWorkout("abandoned");
    });

    // Mode Switcher (AI Vision vs Manual Mode)
    const btnCameraMode = container.querySelector("#btn-mode-camera");
    const btnManualMode = container.querySelector("#btn-mode-manual");
    const manualPanel = container.querySelector("#manual-panel");
    const coachBanner = container.querySelector("#hud-coach-banner");
    const topOverlay = container.querySelector("#hud-overlay-top");
    const techMetrics = container.querySelector("#hud-tech-metrics");
    const manualCounter = container.querySelector("#manual-rep-counter");

    const updateManualDisplay = () => {
      if (manualCounter) manualCounter.textContent = this.repCount;
      this.updateHUDDisplay(null, this.currentState, 0, null);
    };

    const standbyOverlay = container.querySelector("#stage-standby");

    btnCameraMode?.addEventListener("click", async () => {
      if (!await this.selectWorkoutMode("ai")) return;
      btnCameraMode.classList.add("active");
      btnManualMode?.classList.remove("active");
      if (manualPanel) manualPanel.style.display = "none";

      if (this.isCameraRunning || this.videoSourceType === "file") {
        if (standbyOverlay) {
          standbyOverlay.classList.add("hidden");
          standbyOverlay.style.display = "none";
        }
        if (coachBanner) coachBanner.style.display = "flex";
        if (topOverlay) topOverlay.style.display = "flex";
      } else {
        if (standbyOverlay) {
          standbyOverlay.classList.remove("hidden");
          standbyOverlay.style.display = "flex";
        }
        if (coachBanner) coachBanner.style.display = "none";
        if (topOverlay) topOverlay.style.display = "none";
      }
      if (techMetrics) techMetrics.style.display = "";
      this.updateSetsDisplay();
    });

    btnManualMode?.addEventListener("click", async () => {
      if (!await this.selectWorkoutMode("manual")) return;
      btnManualMode.classList.add("active");
      btnCameraMode?.classList.remove("active");
      this.positionMonitor?.reset();

      // Strictly isolate manual mode: show manual panel, hide all camera HUDs
      if (manualPanel) manualPanel.style.display = "flex";
      if (standbyOverlay) {
        standbyOverlay.classList.add("hidden");
        standbyOverlay.style.display = "none";
      }
      if (coachBanner) coachBanner.style.display = "none";
      if (topOverlay) topOverlay.style.display = "none";
      if (techMetrics) techMetrics.style.display = "none";

      updateManualDisplay();
      this.updateSetsDisplay();
      if (!this.isWorkingOut) void this.startWorkout();
    });

    for (const [name, delta] of [["plus1", 1], ["plus5", 5], ["minus", -1], ["reset", null]]) {
      container.querySelector(`#btn-manual-rep-${name}`)?.addEventListener("click", () => {
        if (!this.changeManualReps(delta)) return;
        updateManualDisplay();
        if (delta > 0 && this.repCount >= this.targetReps) {
          Toast.success(`Đạt chỉ tiêu hiệp ${this.currentSet}/${this.totalSets}! Bấm "Hoàn thành hiệp" để tiếp tục.`);
        }
      });
    }

    container.querySelector("#btn-manual-finish-workout")?.addEventListener("click", () => {
      this.finishWorkout();
    });

    // SCRUM-19: Finish Set & Rest Timer Actions
    container.querySelector("#btn-sidebar-finish-set")?.addEventListener("click", () => {
      this.completeCurrentSet();
    });

    container.querySelector("#btn-sidebar-trigger-rest")?.addEventListener("click", () => {
      this.startRestTimer(this.restDurationSec);
    });

    container.querySelector("#btn-manual-finish-set")?.addEventListener("click", () => {
      this.completeCurrentSet();
    });

    container.querySelector("#btn-manual-trigger-rest")?.addEventListener("click", () => {
      this.startRestTimer(this.restDurationSec);
    });

    container.querySelector("#btn-top-skip-ex")?.addEventListener("click", () => {
      this.skipToNextExercise();
    });

    // Rest Timer Overlay Controls
    container.querySelector("#btn-skip-rest-now")?.addEventListener("click", () => {
      this.skipRestTimer();
    });

    container.querySelector("#btn-rest-minus-15")?.addEventListener("click", () => {
      this.adjustRestTimer(-15);
    });

    container.querySelector("#btn-rest-plus-15")?.addEventListener("click", () => {
      this.adjustRestTimer(15);
    });

    container.querySelectorAll(".rest-preset-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const sec = parseInt(btn.getAttribute("data-sec")) || 60;
        this.setRestTimerPreset(sec);
      });
    });
  },

  async startSession(
    exerciseId,
    exerciseName,
    targetReps = 12,
    day = null,
    exerciseList = [],
    prescription = {}
  ) {
    this.leave();
    this.sessionStartTime = 0;
    this.sessionId = null;
    this.poseRequest = null;
    this.sessionStartRequest = null;
    this.modeSessions = new Map();
    this.workoutMode = "ai";
    this.sessionClosed = this.sessionClosing = false;
    this.frameId = 0;
    this.manualSetReps = new Map();
    this.exerciseId = exerciseId || "squat";
    this.exerciseName = exerciseName || "Bodyweight Squat";
    this.targetReps = targetReps || 12;
    this.holdSeconds = prescription.hold_seconds ?? 0;
    this.restSeconds = prescription.rest_sec ?? 60;
    this.restDurationSec = this.restSeconds;
    this.day = day;
    this.repCount = 0;
    this.currentSet = 1;
    this.totalSets = 3;
    this.isResting = false;
    this.videoSourceType = "none";

    // Initialize exercise list
    if (exerciseList && exerciseList.length > 0) {
      this.exerciseList = JSON.parse(JSON.stringify(exerciseList));
      const idx = this.exerciseList.findIndex(
        (e) => (e.id && e.id === exerciseId) || (e.name && e.name === exerciseName)
      );
      this.currentExerciseIdx = idx !== -1 ? idx : 0;
      const curEx = this.exerciseList[this.currentExerciseIdx];
      if (curEx) {
        this.totalSets = parseInt(curEx.sets) || 3;
        this.targetReps = parseInt(curEx.reps) || this.targetReps;
        this.holdSeconds = curEx.hold_seconds ?? this.holdSeconds;
        this.restSeconds = curEx.rest_sec ?? this.restSeconds;
        this.restDurationSec = this.restSeconds;
      }
    } else {
      this.exerciseList = JSON.parse(JSON.stringify(DEFAULT_SESSION_EXERCISES));
      const idx = this.exerciseList.findIndex((e) => e.id === exerciseId);
      this.currentExerciseIdx = idx !== -1 ? idx : 0;
      const curEx = this.exerciseList[this.currentExerciseIdx];
      if (curEx) {
        this.totalSets = parseInt(curEx.sets) || 3;
        this.targetReps = parseInt(curEx.reps) || this.targetReps;
        this.holdSeconds = curEx.hold_seconds ?? this.holdSeconds;
        this.restSeconds = curEx.rest_sec ?? this.restSeconds;
        this.restDurationSec = this.restSeconds;
      }
    }

    await this.render();
    this.renderUpNextListUI();
    this.updateSetsDisplay();

    try {
      if (this.exerciseId === "custom" || (this.exerciseId || "").startsWith("custom")) {
        setTimeout(() => {
          const btnManual = document.getElementById("btn-mode-manual");
          btnManual?.click();
          Toast.info("🎯 Bài tập tùy chỉnh: Đã tự động chuyển sang Chế độ Không dùng Camera (Tự do).");
        }, 50);
      } else {
        if (!await this.ensureWorkoutSession()) return;
        Toast.success(`Sẵn sàng cho bài tập ${this.exerciseName} (Hiệp 1/${this.totalSets})!`);
        this.speak(`Chào bạn! Hãy chuẩn bị bắt đầu bài tập ${this.exerciseName}, hiệp một trên ${this.totalSets}.`);
      }
    } catch (e) {
      console.warn("Could not create backend session:", e);
    }
  },

  createWorkoutSession(mode, currentSet) {
    return API.session.start(
      this.exerciseId, this.targetReps, this.day, this.exerciseList, this.totalSets, currentSet,
      {mode, exerciseIndex: this.currentExerciseIdx},
    );
  },

  async ensureWorkoutSession() {
    if (this.sessionClosed) return false;
    if (this.sessionId) return true;
    if (!this.sessionStartRequest) {
      const request = this.createWorkoutSession(this.workoutMode, this.currentSet).then(data => {
        if (this.sessionStartRequest !== request) return false;
        this.sessionId = data.session_id;
        return true;
      }).catch(() => {
        Toast.error("Không thể mở phiên tập. Hãy thử lại.");
        return false;
      }).finally(() => {
        if (this.sessionStartRequest === request) this.sessionStartRequest = null;
      });
      this.sessionStartRequest = request;
    }
    return this.sessionStartRequest;
  },

  async selectWorkoutMode(mode) {
    if (this.modeRequest || this.sessionClosing) return false;
    if (mode === this.workoutMode) return this.ensureWorkoutSession();
    const request = this.changeWorkoutMode(mode);
    this.modeRequest = request;
    try {
      return await request;
    } finally {
      if (this.modeRequest === request) this.modeRequest = null;
    }
  },

  async changeWorkoutMode(mode) {
    const sessions = this.modeSessions;
    await this.sessionStartRequest;
    if (sessions !== this.modeSessions) return false;
    const paused = this.leave();
    const epoch = this.poseEpoch;
    await paused;
    if (sessions !== this.modeSessions || epoch !== this.poseEpoch) return false;
    const fields = [
      "sessionId", "exerciseId", "exerciseName", "exerciseList", "currentExerciseIdx", "currentSet",
      "totalSets", "targetReps", "holdSeconds", "restSeconds", "restDurationSec", "restRemainingSec",
      "isResting", "restNextInfo", "onRestFinishCallback", "repCount", "manualSetReps", "frameId",
      "sessionStartTime", "sessionClosed",
    ];
    const previous = Object.fromEntries(fields.map(field => [field, this[field]]));
    const saved = this.modeSessions.get(mode);
    if (saved && !saved.sessionClosed) {
      Object.assign(this, saved);
    } else {
      try {
        const data = await this.createWorkoutSession(mode, 1);
        if (sessions !== this.modeSessions || epoch !== this.poseEpoch) return false;
        this.sessionId = data.session_id;
      } catch {
        Toast.error("Không thể chuyển chế độ tập. Hãy thử lại.");
        return false;
      }
      this.exerciseList = structuredClone(this.exerciseList);
      this.currentSet = 1;
      this.repCount = 0;
      this.frameId = 0;
      this.isResting = false;
      this.onRestFinishCallback = null;
      this.sessionStartTime = 0;
      this.sessionClosed = false;
      this.manualSetReps = new Map();
    }
    this.modeSessions.set(this.workoutMode, previous);
    this.workoutMode = mode;
    const restOverlay = document.getElementById("hud-rest-overlay");
    if (restOverlay) restOverlay.style.display = this.isResting ? "flex" : "none";
    this.renderUpNextListUI();
    return true;
  },

  manualSetKey() {
    return JSON.stringify([this.currentExerciseIdx, this.exerciseId, this.currentSet]);
  },

  changeManualReps(delta) {
    if (this.workoutMode !== "manual" || !this.isWorkingOut || this.isResting || this.sessionClosing) return false;
    this.repCount = delta === null ? 0 : Math.max(0, this.repCount + delta);
    this.manualSetReps.set(this.manualSetKey(), this.repCount);
    if (delta > 0) this.playVoiceEvent({kind: "rep", count: this.repCount});
    return true;
  },

  startRestTimer(seconds = null, nextInfo = "", onFinishCallback = null) {
    this.isResting = true;
    this.restDurationSec = seconds ?? this.restDurationSec ?? 60;
    this.restSeconds = this.restDurationSec;
    this.restRemainingSec = this.restDurationSec;
    this.restSoundPlayed = { 3: false, 2: false, 1: false, 0: false };
    this.onRestFinishCallback = onFinishCallback;
    this.restNextInfo = nextInfo;

    clearInterval(this.restTimerInterval);
    if (this.restDurationSec === 0) {
      this.finishRestPeriod();
      return;
    }

    const overlay = document.getElementById("hud-rest-overlay");
    const nextInfoEl = document.getElementById("rest-next-info");
    const manualRestBtn = document.getElementById("btn-manual-trigger-rest");

    if (nextInfoEl) {
      nextInfoEl.textContent = nextInfo || `Chuẩn bị: Hiệp ${this.currentSet}/${this.totalSets} — ${this.exerciseName}`;
    }

    if (overlay) {
      overlay.style.display = "flex";
    }

    this.speak(`Bắt đầu nghỉ giữa hiệp ${this.restRemainingSec} giây.`);
    this.updateRestDisplay();

    const interval = setInterval(() => {
      this.restRemainingSec = Math.max(0, this.restRemainingSec - 1);
      this.updateRestDisplay();

      const rem = this.restRemainingSec;

      if (rem === 3 && !this.restSoundPlayed[3]) {
        this.restSoundPlayed[3] = true;
        this.playBeep(587, 0.2);
        this.speak("Ba");
      } else if (rem === 2 && !this.restSoundPlayed[2]) {
        this.restSoundPlayed[2] = true;
        this.playBeep(659, 0.2);
        this.speak("Hai");
      } else if (rem === 1 && !this.restSoundPlayed[1]) {
        this.restSoundPlayed[1] = true;
        this.playBeep(880, 0.25);
        this.speak("Một");
      } else if (rem === 0 && !this.restSoundPlayed[0]) {
        this.restSoundPlayed[0] = true;
        this.playChime();
        this.speak("Hết giờ nghỉ! Vào hiệp mới nào!");
        Toast.success("🔔 Hết giờ nghỉ! Sẵn sàng vào hiệp mới!");
        clearInterval(this.restTimerInterval);
        setTimeout(() => {
          if (this.restTimerInterval === interval) this.finishRestPeriod();
        }, 800);
      }
    }, 1000);
    this.restTimerInterval = interval;
  },

  updateRestDisplay() {
    const rem = this.restRemainingSec;
    const total = Math.max(1, this.restDurationSec);
    const m = String(Math.floor(rem / 60)).padStart(2, "0");
    const s = String(rem % 60).padStart(2, "0");
    const formatted = `${m}:${s}`;

    const countdownEl = document.getElementById("rest-countdown-val");
    if (countdownEl) {
      countdownEl.textContent = formatted;
      if (rem <= 5) {
        countdownEl.classList.add("urgent");
      } else {
        countdownEl.classList.remove("urgent");
      }
    }

    const progressBar = document.getElementById("rest-progress-bar");
    if (progressBar) {
      const pct = Math.max(0, Math.min(100, (rem / total) * 100));
      progressBar.style.width = `${pct}%`;
      if (rem <= 5) {
        progressBar.style.background = "linear-gradient(90deg, #f59e0b, #ef4444)";
      } else {
        progressBar.style.background = "linear-gradient(90deg, #38bdf8, #4ade80)";
      }
    }

    const manualRestBtn = document.getElementById("btn-manual-trigger-rest");
    if (manualRestBtn) {
      manualRestBtn.textContent = this.isResting ? `⏱️ Đang nghỉ: ${formatted}` : `⏱️ Bật nghỉ (${this.restDurationSec}s)`;
    }

    const sidebarRestBtn = document.getElementById("btn-sidebar-trigger-rest");
    if (sidebarRestBtn) {
      sidebarRestBtn.textContent = this.isResting ? `⏱️ Đang nghỉ: ${formatted}` : `⏱️ Bật đồng hồ nghỉ (${this.restDurationSec}s)`;
    }
  },

  finishRestPeriod() {
    clearInterval(this.restTimerInterval);
    this.restTimerInterval = null;
    this.isResting = false;

    const overlay = document.getElementById("hud-rest-overlay");
    if (overlay) {
      overlay.style.display = "none";
    }

    const manualRestBtn = document.getElementById("btn-manual-trigger-rest");
    if (manualRestBtn) {
      manualRestBtn.textContent = `⏱️ Bật nghỉ (${this.restDurationSec}s)`;
    }

    const sidebarRestBtn = document.getElementById("btn-sidebar-trigger-rest");
    if (sidebarRestBtn) {
      sidebarRestBtn.textContent = `⏱️ Bật đồng hồ nghỉ (${this.restDurationSec}s)`;
    }

    if (this.onRestFinishCallback) {
      const cb = this.onRestFinishCallback;
      this.onRestFinishCallback = null;
      cb();
    } else {
      this.updateSetsDisplay();
      this.speak(`Bắt đầu hiệp ${this.currentSet}! Cố lên!`);
    }
  },

  adjustRestTimer(secondsDelta) {
    this.restRemainingSec = Math.max(5, this.restRemainingSec + secondsDelta);
    this.restDurationSec = Math.max(this.restRemainingSec, this.restDurationSec);
    this.updateRestDisplay();
    Toast.info(`Đã điều chỉnh thời gian nghỉ: ${this.restRemainingSec}s`);
  },

  setRestTimerPreset(seconds) {
    this.restDurationSec = seconds;
    this.restRemainingSec = seconds;
    this.restSoundPlayed = { 3: false, 2: false, 1: false, 0: false };
    this.updateRestDisplay();
    Toast.info(`Đặt thời gian nghỉ: ${seconds}s`);
  },

  skipRestTimer() {
    this.finishRestPeriod();
    Toast.info("Đã bỏ qua thời gian nghỉ! Bắt đầu hiệp mới.");
  },

  completeCurrentSet() {
    clearTimeout(this.setCompletionTimer);
    this.setCompletionTimer = null;
    if (this.isResting) {
      this.skipRestTimer();
      return;
    }

    if (this.currentSet < this.totalSets) {
      this.poseEpoch++;
      this.stopVoice();
      const finishedSet = this.currentSet;
      this.currentSet++;
      this.repCount = this.workoutMode === "manual" ? this.manualSetReps.get(this.manualSetKey()) ?? 0 : 0;
      this.updateSetsDisplay();
      this.renderUpNextListUI();
      Toast.success(`✅ Hoàn thành hiệp ${finishedSet}/${this.totalSets}! Nghỉ ngơi hồi phục.`);
      this.startRestTimer(
        this.restDurationSec,
        `Chuẩn bị: Hiệp ${this.currentSet}/${this.totalSets} — ${this.exerciseName}`
      );
    } else {
      Toast.success(`🎉 Xuất sắc! Hoàn thành toàn bộ ${this.totalSets} hiệp ${this.exerciseName}!`);
      this.speak(`Xuất sắc! Bạn đã hoàn thành toàn bộ các hiệp của bài ${this.exerciseName}.`);

      if (this.currentExerciseIdx + 1 < this.exerciseList.length) {
        const nextEx = this.exerciseList[this.currentExerciseIdx + 1];
        this.startRestTimer(
          nextEx.rest_sec ?? 60,
          `Chuẩn bị bài tiếp theo: ${nextEx.name} (Hiệp 1/${nextEx.sets || 3})`,
          () => {
            this.skipToNextExercise();
          }
        );
      } else {
        setTimeout(() => {
          this.finishWorkout();
        }, 1000);
      }
    }
  },

  skipToNextExercise() {
    if (this.currentExerciseIdx + 1 < this.exerciseList.length) {
      this.jumpToExercise(this.currentExerciseIdx + 1);
    } else {
      if (this.isResting) {
        clearInterval(this.restTimerInterval);
        this.isResting = false;
        const overlay = document.getElementById("hud-rest-overlay");
        if (overlay) overlay.style.display = "none";
      }
      Toast.info("Đây đã là bài tập cuối cùng trong buổi hôm nay!");
    }
  },

  async jumpToExercise(targetIdx) {
    if (targetIdx < 0 || targetIdx >= this.exerciseList.length) return;

    const targetEx = this.exerciseList[targetIdx];
    const exerciseId = targetEx.id || "squat";
    const exerciseName = targetEx.name || "Bài tập";
    const targetReps = parseInt(targetEx.reps) || 12;
    const totalSets = parseInt(targetEx.sets) || 3;
    const switched = await this.syncPoseExercise(exerciseId, exerciseName, targetReps, 1, totalSets, targetIdx);
    if (!switched) return;

    clearInterval(this.restTimerInterval);
    this.restTimerInterval = null;
    this.isResting = false;
    const overlay = document.getElementById("hud-rest-overlay");
    if (overlay) overlay.style.display = "none";

    this.currentExerciseIdx = targetIdx;
    this.exerciseId = exerciseId;
    this.exerciseName = exerciseName;
    this.targetReps = targetReps;
    this.totalSets = totalSets;
    this.holdSeconds = targetEx.hold_seconds ?? 0;
    this.restSeconds = targetEx.rest_sec ?? 60;
    this.restDurationSec = this.restSeconds;
    this.currentSet = 1;
    this.repCount = this.workoutMode === "manual"
      ? this.manualSetReps.get(this.manualSetKey()) ?? 0
      : switched.rep_count ?? 0;

    this.updateSetsDisplay();
    this.renderUpNextListUI();

    Toast.success(`🎯 Chuyển sang bài: ${this.exerciseName}!`);
    this.speak(`Bắt đầu bài tập ${this.exerciseName}. Mục tiêu ${this.targetReps} lần.`);
  },

  async swapCurrentExercise(substituteName, substituteId = null) {
    if (!substituteName) return;
    const switched = await this.syncPoseExercise(
      substituteId || this.exerciseId, substituteName, this.targetReps, this.currentSet, this.totalSets
    );
    if (!switched) return;
    const currentEx = this.exerciseList[this.currentExerciseIdx];
    if (currentEx) {
      currentEx.originalName = currentEx.originalName || currentEx.name;
      currentEx.name = substituteName;
      if (substituteId) currentEx.id = substituteId;
    }
    this.exerciseName = substituteName;
    if (substituteId) this.exerciseId = substituteId;
    this.repCount = this.workoutMode === "manual"
      ? this.manualSetReps.get(this.manualSetKey()) ?? 0
      : switched.rep_count ?? 0;

    this.updateSetsDisplay();
    this.renderUpNextListUI();

    Toast.success(`🔄 Đã đổi sang bài tập: ${substituteName}!`);
    this.speak(`Đã đổi sang bài ${substituteName}.`);
  },

  updateSetsDisplay() {
    const titleText = document.getElementById("hud-exercise-title-text");
    if (titleText) titleText.textContent = this.exerciseName;

    const targetEl = document.getElementById("hud-target-text");
    if (targetEl) {
      targetEl.textContent = `Mục tiêu: ${this.targetReps} reps${this.holdSeconds ? ` · Giữ ${this.holdSeconds}s mỗi rep` : ""} · Nghỉ ${this.restSeconds}s`;
    }

    const setBadge = document.getElementById("hud-set-badge");
    if (setBadge) setBadge.textContent = `Hiệp ${this.currentSet}/${this.totalSets}`;

    const manualSetBadge = document.getElementById("manual-set-badge");
    if (manualSetBadge) manualSetBadge.textContent = `Hiệp ${this.currentSet}/${this.totalSets}`;

    const manualExName = document.getElementById("manual-ex-name-label");
    if (manualExName) manualExName.textContent = this.exerciseName;

    const manualTarget = document.getElementById("manual-target-label");
    if (manualTarget) manualTarget.textContent = `Mục tiêu: ${this.targetReps} reps`;

    const manualCounter = document.getElementById("manual-rep-counter");
    if (manualCounter) manualCounter.textContent = this.repCount;

    const circleLabel = document.querySelector(".rep-label");
    if (circleLabel) circleLabel.textContent = `/ ${this.targetReps} REPS`;

    const countEl = document.getElementById("hud-rep-count");
    if (countEl) countEl.textContent = this.repCount;

    this.updateHUDDisplay(this.currentAngle, this.currentState, false, this.currentDepthPct, null);
  },

  renderUpNextListUI() {
    const container = document.getElementById("up-next-cards-container");
    const progressBadge = document.getElementById("up-next-progress-badge");
    if (!container) return;

    if (progressBadge) {
      progressBadge.textContent = `Bài ${this.currentExerciseIdx + 1}/${this.exerciseList.length}`;
    }

    if (!this.exerciseList || this.exerciseList.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem; padding: 0.5rem 0;">Không có bài tập tiếp theo.</div>`;
      return;
    }

    container.innerHTML = this.exerciseList.map((ex, idx) => {
      const isCompleted = idx < this.currentExerciseIdx;
      const isActive = idx === this.currentExerciseIdx;
      const isUpcoming = idx > this.currentExerciseIdx;

      const totalSets = ex.sets || 3;
      const reps = ex.reps || 12;
      const restSec = ex.rest_sec || 60;
      const muscle = ex.primary_muscle || "Toàn thân";
      const substitute = ex.substitute || "Biến thể tương đương";
      const substituteId = ex.substitute_id || null;

      if (isCompleted) {
        return `
          <div class="up-next-item completed">
            <div class="up-next-item-main">
              <div class="up-next-title-row">
                <span class="up-next-name">✅ ${idx + 1}. ${ex.name}</span>
                <span class="badge badge-success" style="font-size: 0.72rem; padding: 0.15rem 0.5rem;">ĐÃ HOÀN THÀNH</span>
              </div>
              <div class="up-next-sub">
                ${totalSets}/${totalSets} sets • ${reps} reps • ${muscle}
              </div>
            </div>
          </div>
        `;
      } else if (isActive) {
        return `
          <div class="up-next-item active">
            <div class="up-next-item-main">
              <div class="up-next-title-row">
                <span class="up-next-name active-glow">🎯 ${idx + 1}. ${ex.name}</span>
                <span class="badge badge-primary" style="font-size: 0.72rem; padding: 0.15rem 0.5rem;">ĐANG TẬP</span>
              </div>
              <div class="up-next-sub">
                <b>Tiến độ:</b> Hiệp ${this.currentSet}/${totalSets} • <b>Mục tiêu:</b> ${reps} reps • Nghỉ: ${restSec}s • ${muscle}
              </div>
              ${ex.form_tip ? `<div class="up-next-tip">💡 ${ex.form_tip}</div>` : ""}
            </div>
          </div>
        `;
      } else {
        return `
          <div class="up-next-item upcoming">
            <div class="up-next-item-main">
              <div class="up-next-title-row">
                <span class="up-next-name">⏳ ${idx + 1}. ${ex.name}</span>
                <span class="badge badge-outline" style="font-size: 0.72rem; padding: 0.15rem 0.5rem;">SẮP TỚI</span>
              </div>
              <div class="up-next-sub">
                ${totalSets} sets × ${reps} reps • Nghỉ: ${restSec}s • ${muscle}
              </div>
            </div>
            <div class="up-next-actions">
              <button class="btn btn-outline btn-xs btn-jump-exercise" data-idx="${idx}" title="Chuyển ngay sang bài tập này">
                🎯 Tập bài này ngay
              </button>
            </div>
          </div>
        `;
      }
    }).join("");

    // Bind dynamic click events for jump to exercise
    container.querySelectorAll(".btn-jump-exercise").forEach((btn) => {
      btn.addEventListener("click", () => {
        const idx = parseInt(btn.getAttribute("data-idx"));
        this.jumpToExercise(idx);
      });
    });
  },

  async startWorkout() {
    if (this.sessionClosing) return false;
    const epoch = this.poseEpoch;
    if (!await this.ensureWorkoutSession() || epoch !== this.poseEpoch ||
        !await this.queueSessionPause(false) || epoch !== this.poseEpoch) return false;
    this.isWorkingOut = true;
    if (this.isResting && this.restTimerInterval === null) {
      this.startRestTimer(this.restRemainingSec, this.restNextInfo, this.onRestFinishCallback);
    }
    const btn = document.getElementById("btn-toggle-workout");
    if (btn) {
      btn.innerHTML = "⏸️ Tạm dừng tập";
      btn.className = "btn btn-outline";
    }

    if (this.videoEl && this.videoSourceType === "file" && this.videoEl.paused) {
      this.videoEl.play().catch(() => {});
    }

    if (!this.sessionStartTime) {
      this.sessionStartTime = Date.now();
    }

    clearInterval(this.sessionTimerInterval);
    this.sessionTimerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - this.sessionStartTime) / 1000);
      const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const s = String(elapsed % 60).padStart(2, "0");
      const timerEl = document.getElementById("hud-timer");
      if (timerEl) timerEl.textContent = `${m}:${s}`;

      const calEl = document.getElementById("hud-calories");
      if (calEl) {
        const cal = (this.repCount * 0.4 + (elapsed / 60) * 4).toFixed(1);
        calEl.textContent = `${cal} kcal`;
      }
    }, 1000);

    Toast.info("Buổi tập bắt đầu! Giữ đúng nhịp thở và kiểm soát tư thế.");
    this.speak("Buổi tập bắt đầu!");
    return true;
  },

  pauseWorkout() {
    this.isWorkingOut = false;
    this.poseEpoch++;
    this.stopVoice();
    clearInterval(this.sessionTimerInterval);
    clearInterval(this.restTimerInterval);
    this.restTimerInterval = null;

    if (this.videoEl && this.videoSourceType === "file" && !this.videoEl.paused) {
      this.videoEl.pause();
    }

    const btn = document.getElementById("btn-toggle-workout");
    if (btn) {
      btn.innerHTML = "▶️ Tiếp tục tập";
      btn.className = "btn btn-emerald";
    }
    Toast.info("Đã tạm dừng buổi tập.");
    return this.queueSessionPause(true);
  },

  async startCamera() {
    if (!await this.selectWorkoutMode("ai")) return;
    document.getElementById("btn-mode-camera")?.click();
    this.stopVideoSource();

    const stage = document.getElementById("hud-stage");
    const standby = document.getElementById("stage-standby");
    const btnCam = document.getElementById("btn-toggle-camera");
    const liveText = document.getElementById("hud-live-text");
    const statusText = document.getElementById("tech-ai-status");

    if (statusText) statusText.textContent = "⏳ Đang kết nối camera và khởi tạo MediaPipe AI...";

    try {
      const generation = this.poseEpoch;
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 30, min: 25 },
          facingMode: "user",
        },
        audio: false,
      });
      if (this.workoutMode !== "ai" || this.poseEpoch !== generation) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      this.stream = stream;

      if (this.videoEl) {
        this.videoEl.srcObject = this.stream;
        await this.videoEl.play();
      }

      this.videoSourceType = "camera";
      this.isCameraRunning = true;

      // Mirror canvas for webcam mode
      if (this.canvasEl) this.canvasEl.style.transform = "scaleX(-1)";

      if (standby) {
        standby.classList.add("hidden");
        standby.style.display = "none";
      }
      const coachBanner = document.getElementById("hud-coach-banner");
      const topOverlay = document.getElementById("hud-overlay-top");
      if (coachBanner) coachBanner.style.display = "flex";
      if (topOverlay) topOverlay.style.display = "flex";
      if (stage) stage.classList.add("active");
      if (btnCam) btnCam.textContent = "⏹️ Tắt Camera";
      if (liveText) liveText.textContent = "LIVE CAMERA FEED";

      if (!this.isWorkingOut && !await this.startWorkout()) {
        this.stopVideoSource();
        return;
      }
      this.startFrameAnalysisLoop();
      Toast.success("Đã bật Camera thành công! AI đang quét khung xương khớp...");
      this.speak("Đã kết nối camera. Hãy lùi lại để AI nhận diện tư thế.");
    } catch (err) {
      console.warn("Camera access failed:", err);
      Toast.error("Không thể mở Camera: Vui lòng cấp quyền webcam hoặc sử dụng tính năng 'Tải lên Video'.");
      if (standby) standby.classList.remove("hidden");
      if (statusText) statusText.textContent = "Không tìm thấy camera hoặc bị chặn quyền.";
    }
  },

  async loadVideoFile(file) {
    if (!await this.selectWorkoutMode("ai")) return;
    document.getElementById("btn-mode-camera")?.click();
    this.stopVideoSource();

    const stage = document.getElementById("hud-stage");
    const standby = document.getElementById("stage-standby");
    const btnSidebarUpload = document.getElementById("btn-sidebar-upload-video");
    const btnCam = document.getElementById("btn-toggle-camera");
    const liveText = document.getElementById("hud-live-text");
    const statusText = document.getElementById("tech-ai-status");

    this.activeVideoUrl = URL.createObjectURL(file);
    this.videoFileName = file.name;
    this.videoSourceType = "file";

    // Do NOT mirror uploaded video file
    if (this.canvasEl) this.canvasEl.style.transform = "scaleX(1)";

    if (this.videoEl) {
      this.videoEl.srcObject = null;
      this.videoEl.src = this.activeVideoUrl;
      this.videoEl.loop = false;

      this.videoEl.onended = () => {
        Toast.info(`Video "${this.videoFileName}" đã phát xong! Bạn đã hoàn thành ${this.repCount} reps.`);
        this.speak(`Đã phát xong video. Bạn đã hoàn thành ${this.repCount} lần lặp!`);
      };

      try {
        await this.videoEl.play();
      } catch (err) {
        console.warn("Video autoplay blocked:", err);
      }
    }

    if (standby) {
      standby.classList.add("hidden");
      standby.style.display = "none";
    }
    const coachBanner = document.getElementById("hud-coach-banner");
    const topOverlay = document.getElementById("hud-overlay-top");
    if (coachBanner) coachBanner.style.display = "flex";
    if (topOverlay) topOverlay.style.display = "flex";
    if (stage) stage.classList.add("active");
    if (btnCam) btnCam.textContent = "⏹️ Dừng Video";
    if (btnSidebarUpload) btnSidebarUpload.textContent = "📁 Đổi Video";
    if (liveText) liveText.textContent = `VIDEO: ${this.videoFileName.slice(0, 18)}`;
    if (statusText) statusText.textContent = `Đang phân tích khung xương video: ${this.videoFileName}`;

    if (!this.isWorkingOut && !await this.startWorkout()) {
      this.stopVideoSource();
      return;
    }
    this.startFrameAnalysisLoop();
    Toast.success(`Đã tải video: ${file.name}. AI bắt đầu phân tích từng khung hình!`);
    this.speak(`Đã tải video bài tập. AI đang theo dõi chuyển động.`);
  },

  stopVideoSource() {
    this.positionMonitor?.reset();
    if (this.videoSourceType !== "none") this.resetPoseFeedback();
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }

    if (this.activeVideoUrl) {
      URL.revokeObjectURL(this.activeVideoUrl);
      this.activeVideoUrl = null;
    }

    if (this.videoEl) {
      this.videoEl.pause();
      this.videoEl.srcObject = null;
      this.videoEl.removeAttribute("src");
      this.videoEl.load();
    }

    if (this.ctx && this.canvasEl) {
      this.ctx.clearRect(0, 0, this.canvasEl.width, this.canvasEl.height);
    }

    cancelAnimationFrame(this.animationLoopId);
    this.videoSourceType = "none";
    this.isCameraRunning = false;
    this.posePositionWarning = null;
    this.poseWarningCandidate = null;
    this.poseWarningCandidateTime = 0;
    this.resetXGesture();

    const stage = document.getElementById("hud-stage");
    const standby = document.getElementById("stage-standby");
    const btnCam = document.getElementById("btn-toggle-camera");
    const btnSidebarUpload = document.getElementById("btn-sidebar-upload-video");
    const liveText = document.getElementById("hud-live-text");
    const statusText = document.getElementById("tech-ai-status");
    const fpsBadge = document.getElementById("tech-fps-badge");

    const isCameraMode = document.getElementById("btn-mode-camera")?.classList.contains("active");
    if (stage) stage.classList.remove("active");
    if (standby) {
      if (isCameraMode) {
        standby.classList.remove("hidden");
        standby.style.display = "flex";
      } else {
        standby.classList.add("hidden");
        standby.style.display = "none";
      }
    }
    const coachBanner = document.getElementById("hud-coach-banner");
    const topOverlay = document.getElementById("hud-overlay-top");
    if (coachBanner) coachBanner.style.display = "none";
    if (topOverlay) topOverlay.style.display = "none";
    if (btnCam) btnCam.textContent = "📷 Bật Camera";
    if (btnSidebarUpload) btnSidebarUpload.textContent = "📁 Tải Video";
    if (liveText) liveText.textContent = "AI VISION READY";
    if (statusText) statusText.textContent = "Sẵn sàng bật camera hoặc tải video.";
    if (fpsBadge) fpsBadge.textContent = "FPS: —";

    this.resetTechnicalMetrics();
  },

  resetTechnicalMetrics() {
    const ids = ["val-elbow-left", "val-elbow-right", "val-knee-left", "val-knee-right"];
    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.textContent = "—";
    });
  },

  startFrameAnalysisLoop() {
    cancelAnimationFrame(this.animationLoopId);

    let lastDispatchTime = 0;
    const DISPATCH_INTERVAL_MS = 120; // Throttled calls to backend FSM
    this.frameCount = 0;
    this.lastFpsTime = performance.now();

    // SCRUM-18 Performance Optimizations: Adaptive Frame Budgeting & Cached Pose
    let detectCostMs = 0;
    let skipNextDetection = false;
    const DETECT_BUDGET_MS = 24; // ms target per inference
    let cachedPose = null;
    let cachedPoints = [];
    let cachedAngles = null;
    let cachedDetectedAngle = null;
    let lastVideoTime = null;
    let lastVideoFrameAt = performance.now();
    let pendingTrackingLoss = false;
    let trackingLossSent = false;

    const sendTrackedAngle = (angle, now, landmarkType) => {
      if (angle === null) {
        if (!trackingLossSent) pendingTrackingLoss = true;
      } else {
        trackingLossSent = false;
      }
      if (pendingTrackingLoss) {
        if (this.dispatchAngleToFSM(null, now, landmarkType, true)) {
          pendingTrackingLoss = false;
          trackingLossSent = true;
          lastDispatchTime = now;
        }
      } else if (angle !== null && now - lastDispatchTime >= DISPATCH_INTERVAL_MS &&
                 this.dispatchAngleToFSM(angle, now, landmarkType)) {
        lastDispatchTime = now;
      }
    };

    const step = () => {
      if (this.videoSourceType === "none" || !this.videoEl || !this.canvasEl || !this.ctx) return;

      const v = this.videoEl;
      const ctx = this.ctx;
      const canvas = this.canvasEl;
      const now = performance.now();
      if (v.readyState < 2 || v.paused || v.ended || v.currentTime === lastVideoTime) {
        if (v.ended || now - lastVideoFrameAt >= 250) sendTrackedAngle(null, now, "knee");
        this.animationLoopId = requestAnimationFrame(step);
        return;
      }
      lastVideoTime = v.currentTime;
      lastVideoFrameAt = now;

      if (v.readyState >= 2 && !v.paused && !v.ended) {
        const w = v.videoWidth || 640;
        const h = v.videoHeight || 480;

        if (canvas.width !== w || canvas.height !== h) {
          canvas.width = w;
          canvas.height = h;
        }

        // 1. Draw video frame directly onto canvas
        ctx.drawImage(v, 0, 0, w, h);

        // 2. Compute FPS
        this.frameCount++;
        if (now - this.lastFpsTime >= 1000) {
          const fps = ((this.frameCount * 1000) / (now - this.lastFpsTime)).toFixed(1);
          const fpsBadge = document.getElementById("tech-fps-badge");
          if (fpsBadge) fpsBadge.textContent = `FPS: ${fps}`;
          this.frameCount = 0;
          this.lastFpsTime = now;
        }

        // 3. Pose Detection with Adaptive Frame Budgeting (SCRUM-18)
        if (poseDetectorInstance) {
          try {
            const shouldDetect = detectCostMs <= DETECT_BUDGET_MS || !skipNextDetection;
            skipNextDetection = !skipNextDetection;

            if (shouldDetect) {
              const detectStart = performance.now();
              const results = poseDetectorInstance.detectForVideo(v, now);
              const currentDetectCost = performance.now() - detectStart;
              detectCostMs = detectCostMs === 0
                ? currentDetectCost
                : 0.85 * detectCostMs + 0.15 * currentDetectCost;

              const pose = results?.landmarks?.[0] || null;
              if (this.videoSourceType === "camera" &&
                  document.getElementById("btn-mode-camera")?.classList.contains("active")) {
                this.positionMonitor?.update(pose, this.exerciseId, w, h, now);
              }

              if (pose && pose.length >= 29) {
                cachedPose = pose;
                // Convert landmarks to pixel points with smoothing to eliminate micro-jitter
                const newPoints = pose.map((p) => ((p.visibility ?? 1) >= 0.35 ? { x: p.x * w, y: p.y * h } : null));
                if (cachedPoints.length === newPoints.length) {
                  cachedPoints = newPoints.map((np, idx) => {
                    if (!np) return null;
                    const cp = cachedPoints[idx];
                    if (!cp) return np;
                    return { x: 0.75 * np.x + 0.25 * cp.x, y: 0.75 * np.y + 0.25 * cp.y };
                  });
                } else {
                  cachedPoints = newPoints;
                }

                cachedAngles = this.updateTechnicalMetrics(cachedPoints);

                cachedDetectedAngle = this.measureTrackedAngle(pose, w, h, usesElbowAngle(this.exerciseId));
              } else {
                cachedPose = null;
                cachedPoints = [];
                cachedAngles = null;
                cachedDetectedAngle = null;
              }
              sendTrackedAngle(cachedDetectedAngle, now, usesElbowAngle(this.exerciseId) ? "elbow" : "knee");
            }

            if (cachedPose && cachedPoints.length >= 29) {
              const points = cachedPoints;
              const pose = cachedPose;
              const angles = cachedAngles || this.updateTechnicalMetrics(points);

              // Draw interactive skeleton bones (Left: Cyan #38bdf8, Right: Orange #fb923c, Center: Lime #4ade80)
              ctx.lineWidth = 3;
              ctx.lineCap = "round";
              for (const [start, end] of POSE_BONES) {
                const a = points[start];
                const b = points[end];
                if (!a || !b) continue;

                const isLeft = start % 2 === 1 && end % 2 === 1;
                const isRight = start % 2 === 0 && end % 2 === 0 && start >= 11 && end >= 11;
                ctx.strokeStyle = isLeft ? "#38bdf8" : (isRight ? "#fb923c" : "#4ade80");

                ctx.beginPath();
                ctx.moveTo(a.x, a.y);
                ctx.lineTo(b.x, b.y);
                ctx.stroke();
              }

              // Draw joint dots with Knee Valgus check
              const isKneeValgus = points[25] && points[26] && points[27] && points[28] &&
                Math.abs(points[27].x - points[28].x) > 0 &&
                Math.abs(points[25].x - points[26].x) < 0.72 * Math.abs(points[27].x - points[28].x);

              for (let i = 0; i < points.length; i++) {
                const p = points[i];
                if (!p) continue;
                ctx.beginPath();
                ctx.arc(p.x, p.y, 4.5, 0, Math.PI * 2);
                if ((i === 25 || i === 26) && isKneeValgus) {
                  ctx.fillStyle = "#ef4444"; // Knee Valgus warning
                } else {
                  ctx.fillStyle = i < 11 ? "#ffffff" : (i % 2 === 1 ? "#38bdf8" : "#fb923c");
                }
                ctx.fill();
                ctx.strokeStyle = "#ffffff";
                ctx.lineWidth = 1.5;
                ctx.stroke();
              }

              const isUpper = usesElbowAngle(this.exerciseId);
              const detectedAngle = cachedDetectedAngle;

              // Evaluate real-time positioning: too_close or bad_angle (SCRUM-19 Smart Warnings)
              const isPositionValid = this.evaluatePosePositioning(pose, points, w, h, isUpper, angles, detectedAngle, now);

              // Check Dual-Gesture: Crossed Wrists 'X' to finish set & start rest timer
              this.checkXGesture(points, now);

              // Draw joint angle text overlay right on active joint
              const activeJoint = isUpper ? (points[13] || points[14]) : (points[25] || points[26]);
              if (activeJoint && detectedAngle !== null && isPositionValid) {
                ctx.save();
                // If canvas is mirrored, flip text context so angle reads naturally
                if (this.videoSourceType === "camera") {
                  ctx.scale(-1, 1);
                  ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
                  ctx.fillRect(-activeJoint.x - 70, activeJoint.y - 25, 65, 24);
                  ctx.font = "bold 15px monospace";
                  ctx.fillStyle = isKneeValgus ? "#ef4444" : "#f59e0b";
                  ctx.fillText(`${Math.round(detectedAngle)}°`, -activeJoint.x - 64, activeJoint.y - 8);
                } else {
                  ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
                  ctx.fillRect(activeJoint.x + 10, activeJoint.y - 25, 65, 24);
                  ctx.font = "bold 15px monospace";
                  ctx.fillStyle = isKneeValgus ? "#ef4444" : "#f59e0b";
                  ctx.fillText(`${Math.round(detectedAngle)}°`, activeJoint.x + 16, activeJoint.y - 8);
                }
                ctx.restore();
              }

            } else {
              this.evaluatePosePositioning(null, [], w, h, false, null, null, now);
              if (this.videoSourceType === "camera" &&
                  document.getElementById("btn-mode-camera")?.classList.contains("active")) {
                this.positionMonitor?.update(null, this.exerciseId, w, h, now);
              }
              this.resetXGesture();
            }
          } catch (detErr) {
            sendTrackedAngle(null, now, "knee");
          }
        } else {
          // Detector still loading
          getPoseDetector().catch(() => {});
        }
      }

      this.animationLoopId = requestAnimationFrame(step);
    };

    this.animationLoopId = requestAnimationFrame(step);
  },

  measureTrackedAngle(pose, width, height, isUpper) {
    const chains = isUpper ? [[11, 13, 15], [12, 14, 16]] : [[23, 25, 27], [24, 26, 28]];
    const trackedPoint = index => {
      const point = pose[index];
      if (!point || (point.visibility ?? 0) < 0.6 || (point.presence ?? 1) < 0.6 ||
          !(point.x >= 0 && point.x <= 1 && point.y >= 0 && point.y <= 1)) return null;
      return {x: point.x * width, y: point.y * height};
    };
    for (const chain of chains) {
      const angle = angleAt(...chain.map(trackedPoint));
      if (Number.isFinite(angle)) return angle;
    }
    return null;
  },

  // SCRUM-19: Real-time Camera Pose & Standing Position Warnings (Yêu cầu 30 & 38)
  evaluatePosePositioning(pose, points, w, h, isUpper, angles, detectedAngle, now) {
    let detectedWarning = null; // null | 'too_close' | 'bad_angle' | 'out_of_frame'

    if (!pose || pose.length < 15 || !points || points.length === 0 || (!points[11] && !points[12] && !points[0])) {
      detectedWarning = "out_of_frame";
    } else {
      const hasValidLegChain = angles && (angles.leftKnee !== null || angles.rightKnee !== null);
      const hasValidArmChain = angles && (angles.leftElbow !== null || angles.rightElbow !== null);

      if (!isUpper) {
        // Bài tập thân dưới (Squat, Lunge):
        if (hasValidLegChain) {
          // Khớp gối và toàn bộ chuỗi Hông - Gối - Cổ chân đều đã thấy đủ và đo được góc chuẩn!
          detectedWarning = null;
        } else {
          // Không tính được góc gối: Xác định lý do cụ thể
          const hasUpper = Boolean(points[11] || points[12] || points[0]);
          const hasAnyLegPoints = Boolean(points[25] || points[26] || points[27] || points[28] || points[31] || points[32]);

          if (hasUpper && !hasAnyLegPoints) {
            // Thấy thân trên nhưng mất hoàn toàn phần chân bên dưới -> ĐỨNG QUÁ GẦN
            detectedWarning = "too_close";
          } else {
            // Có thấy chân nhưng không tính được góc gối do góc đứng bị che khuất -> ĐỨNG SAI GÓC
            detectedWarning = "bad_angle";
          }
        }
      } else {
        // Bài tập thân trên (Push-up, Dip, Tay):
        if (hasValidArmChain) {
          detectedWarning = null;
        } else {
          const hasUpper = Boolean(points[11] || points[12]);
          const hasAnyArm = Boolean(points[13] || points[14] || points[15] || points[16]);

          if (!hasUpper && !hasAnyArm) {
            detectedWarning = "too_close";
          } else {
            detectedWarning = "bad_angle";
          }
        }
      }
    }

    // Debounce: Chống nhấp nháy, duy trì liên tục >= 1200ms mới kích hoạt cảnh báo
    if (detectedWarning !== this.poseWarningCandidate) {
      this.poseWarningCandidate = detectedWarning;
      this.poseWarningCandidateTime = now;
    }

    const candidateDuration = now - this.poseWarningCandidateTime;

    if (detectedWarning === null) {
      // Khi tư thế đã chuẩn, xóa cảnh báo ngay sau 250ms
      if (candidateDuration >= 250) {
        this.posePositionWarning = null;
      }
    } else {
      // Chỉ khi sai liên tục >= 1200ms mới hiển thị cảnh báo
      if (candidateDuration >= 1200) {
        this.posePositionWarning = detectedWarning;
      }
    }

    const statusEl = document.getElementById("tech-ai-status");
    const banner = document.getElementById("hud-coach-banner");

    if (this.posePositionWarning === "too_close") {
      if (statusEl) {
        statusEl.textContent = "⚠️ Bạn đang đứng quá gần: Vui lòng lùi lại 2m–2.5m để thấy rõ từ đầu đến chân.";
        statusEl.style.color = "var(--accent-amber)";
      }
      if (banner) {
        banner.textContent = "⚠️ Hãy lùi lại 2m–2.5m để camera nhìn rõ toàn thân";
        banner.className = "hud-coach-banner warn";
      }
      // Voice cue with 15s cooldown
      if (now - this.lastSpokenWarningTime > 15000 || this.lastSpokenWarning !== "too_close") {
        this.speak("Bạn đang đứng hơi gần, hãy lùi lại một chút để camera thấy rõ toàn thân nhé.");
        this.lastSpokenWarning = "too_close";
        this.lastSpokenWarningTime = now;
      }
      return false;
    } else if (this.posePositionWarning === "bad_angle") {
      const tipText = isUpper
        ? "⚠️ Chưa thấy rõ khuỷu tay: Hãy xoay ngang góc máy để AI theo dõi khớp tay."
        : "⚠️ Chưa thấy rõ khớp gối: Hãy xoay người góc nghiêng (45°–90°) để AI thấy rõ khớp gối.";
      const bannerText = isUpper
        ? "⚠️ Xoay ngang góc máy để thấy rõ khuỷu tay"
        : "⚠️ Xoay người hơi nghiêng (45°–90°) để thấy rõ khớp gối";

      if (statusEl) {
        statusEl.textContent = tipText;
        statusEl.style.color = "var(--accent-amber)";
      }
      if (banner) {
        banner.textContent = bannerText;
        banner.className = "hud-coach-banner warn";
      }
      // Voice cue with 15s cooldown
      if (now - this.lastSpokenWarningTime > 15000 || this.lastSpokenWarning !== "bad_angle") {
        const voiceTip = isUpper
          ? "Hãy điều chỉnh góc máy ngang thân người để thấy rõ khuỷu tay nhé."
          : "Hãy xoay người hơi nghiêng một chút để camera nhìn rõ khớp gối nhé.";
        this.speak(voiceTip);
        this.lastSpokenWarning = "bad_angle";
        this.lastSpokenWarningTime = now;
      }
      return false;
    } else if (this.posePositionWarning === "out_of_frame") {
      if (statusEl) {
        statusEl.textContent = "👀 Hãy đứng vào khung hình để camera bắt đầu nhận diện.";
        statusEl.style.color = "var(--text-muted)";
      }
      return false;
    } else {
      // Normal state: CÁC KHỚP ĐÃ ĐỦ VÀ CHUẨN XÁC -> KHÔI PHỤC GIAO DIỆN BÌNH THƯỜNG
      if (statusEl) {
        statusEl.style.color = "var(--accent-cyan)";
        const activeAngle = (detectedAngle !== undefined && detectedAngle !== null) ? detectedAngle : null;
        statusEl.textContent = activeAngle !== null
          ? `🎯 Đã nhận diện toàn thân · Góc đo rep (${isUpper ? 'Khuỷu tay' : 'Khớp gối'}): ${Math.round(activeAngle)}°`
          : `🎯 Đã nhận diện toàn thân · Sẵn sàng vào bài tập`;
      }
      if (banner && banner.classList.contains("warn")) {
        banner.className = "hud-coach-banner";
        banner.textContent = "🎯 Chuẩn bị sẵn sàng: Đứng thẳng trước camera để bắt đầu";
      }
      return true;
    }
  },

  // SCRUM-16 & SCRUM-19: Dual Gesture - Crossed Wrists 'X' to finish set & start rest timer
  checkXGesture(points, now) {
    if (!this.isWorkingOut || this.isResting || !points || points.length < 25) {
      this.resetXGesture();
      return;
    }

    const leftWrist = points[15];
    const rightWrist = points[16];
    const leftShoulder = points[11];
    const rightShoulder = points[12];
    const leftHip = points[23];
    const rightHip = points[24];

    let isXActive = false;

    if (leftWrist && rightWrist && leftShoulder && rightShoulder && leftHip && rightHip) {
      const shoulderY = (leftShoulder.y + rightShoulder.y) / 2;
      const hipY = (leftHip.y + rightHip.y) / 2;
      const bodyWidth = Math.abs(rightShoulder.x - leftShoulder.x);

      // Both wrists are vertically in torso region (between shoulders and hips)
      const inVerticalZone = (leftWrist.y > shoulderY && leftWrist.y < hipY &&
                              rightWrist.y > shoulderY && rightWrist.y < hipY);

      // Wrists are crossed or close to each other (distance < 35% of shoulder width)
      const wristDistance = Math.abs(leftWrist.x - rightWrist.x);
      const isCrossedOrClose = wristDistance < 0.35 * bodyWidth;

      if (bodyWidth > 0 && shoulderY < hipY && inVerticalZone && isCrossedOrClose) {
        isXActive = true;
      }
    }

    const HOLD_DURATION_MS = 1500; // Hold for 1.5 seconds per spec
    const indicator = document.getElementById("hud-x-indicator");
    const fill = document.getElementById("x-gesture-fill");
    const timeLabel = document.getElementById("x-gesture-time");

    if (isXActive) {
      if (!this.xGestureStartTime) {
        this.xGestureStartTime = now;
      }

      const elapsed = now - this.xGestureStartTime;
      const progress = Math.min(1.0, elapsed / HOLD_DURATION_MS);
      const remainingSec = Math.max(0, ((HOLD_DURATION_MS - elapsed) / 1000)).toFixed(1);

      if (indicator) indicator.style.display = "flex";
      if (fill) fill.style.width = `${progress * 100}%`;
      if (timeLabel) timeLabel.textContent = `${remainingSec}s`;

      if (elapsed >= HOLD_DURATION_MS && !this.xGestureTriggered) {
        this.xGestureTriggered = true;
        this.resetXGesture();
        this.triggerXGestureComplete();
      }
    } else {
      this.resetXGesture();
    }
  },

  resetXGesture() {
    this.xGestureStartTime = null;
    const indicator = document.getElementById("hud-x-indicator");
    const fill = document.getElementById("x-gesture-fill");
    if (indicator) indicator.style.display = "none";
    if (fill) fill.style.width = "0%";
  },

  triggerXGestureComplete() {
    Toast.success("🙅 Cử chỉ chữ X: Hoàn thành hiệp & Bật nghỉ!");
    this.speak("Đã nhận diện cử chỉ chữ X. Bắt đầu nghỉ giữa hiệp.");

    // Complete current set -> triggers Rest Timer -> advances to next set
    this.completeCurrentSet();

    setTimeout(() => {
      this.xGestureTriggered = false;
    }, 2500);
  },

  updateTechnicalMetrics(points) {
    const leftElbow = angleAt(points[11], points[13], points[15]);
    const rightElbow = angleAt(points[12], points[14], points[16]);
    const leftKnee = angleAt(points[23], points[25], points[27]);
    const rightKnee = angleAt(points[24], points[26], points[28]);

    const elElbowL = document.getElementById("val-elbow-left");
    const elElbowR = document.getElementById("val-elbow-right");
    const elKneeL = document.getElementById("val-knee-left");
    const elKneeR = document.getElementById("val-knee-right");

    if (elElbowL) elElbowL.textContent = leftElbow !== null ? `${Math.round(leftElbow)}°` : "—";
    if (elElbowR) elElbowR.textContent = rightElbow !== null ? `${Math.round(rightElbow)}°` : "—";
    if (elKneeL) elKneeL.textContent = leftKnee !== null ? `${Math.round(leftKnee)}°` : "—";
    if (elKneeR) elKneeR.textContent = rightKnee !== null ? `${Math.round(rightKnee)}°` : "—";

    const statusEl = document.getElementById("tech-ai-status");
    if (statusEl && !this.posePositionWarning) {
      statusEl.style.color = "var(--accent-cyan)";
      const isUpper = usesElbowAngle(this.exerciseId);
      const activeAngle = isUpper
        ? (leftElbow ?? rightElbow)
        : (leftKnee ?? rightKnee);
      statusEl.textContent = activeAngle !== null
        ? `🎯 Đã nhận diện toàn thân · Góc đo rep (${isUpper ? "Khuỷu tay" : "Khớp gối"}): ${Math.round(activeAngle)}°`
        : `👀 Hãy đứng trong khung hình để thấy rõ khớp.`;
    }

    return { leftElbow, rightElbow, leftKnee, rightKnee };
  },

  dispatchAngleToFSM(angle, capturedAt, landmarkType = "knee", trackingInterrupted = false) {
    if (this.workoutMode !== "ai" || !this.isWorkingOut || this.isResting || !this.sessionId ||
        this.poseRequest || this.setCompletionTimer) return false;
    const sessionId = this.sessionId, epoch = this.poseEpoch, currentSet = this.currentSet;
    const request = API.session.sendAngle(
      sessionId, angle, landmarkType, trackingInterrupted, currentSet, this.currentExerciseIdx, ++this.frameId,
    ).then(data => {
      if (sessionId !== this.sessionId || epoch !== this.poseEpoch || currentSet !== this.currentSet ||
          !this.isWorkingOut || this.isResting) return;
      this.repCount = data.rep_count;
      this.updateHUDDisplay(data.angle, data.state, data.depth_pct, data.cue);
      const trackingLost = data.status === "paused" || data.tracking_lost === true;
      if (trackingLost && !this.poseTrackingLost) this.stopVoice();
      this.poseTrackingLost = trackingLost;
      if (data.voice_event) this.playVoiceEvent({...data.voice_event, captured_at: capturedAt});
      if (data.rep_incremented) this.onRepCounted();
    }).catch(() => {}).finally(() => {
      if (this.poseRequest === request) this.poseRequest = null;
    });
    this.poseRequest = request;
    return true;
  },

  syncPoseExercise(exerciseId, exerciseName, targetReps, currentSet, totalSets, exerciseIndex = this.currentExerciseIdx) {
    if (this.poseSwitchRequest) return false;
    clearTimeout(this.setCompletionTimer);
    this.setCompletionTimer = null;
    const sessionId = this.sessionId, epoch = ++this.poseEpoch;
    this.stopVoice();
    if (!sessionId) return true;
    const request = Promise.resolve(this.poseRequest).then(async () => {
      if (sessionId !== this.sessionId || epoch !== this.poseEpoch) return false;
      const data = await API.session.switchExercise(
        sessionId, exerciseId, exerciseName, targetReps, currentSet, totalSets, exerciseIndex,
      );
      return sessionId === this.sessionId && data;
    }).catch(() => {
      if (sessionId === this.sessionId) Toast.error("Không thể đổi bài tập. Hãy thử lại.");
      return false;
    }).finally(() => {
      if (this.poseRequest === request) this.poseRequest = null;
      if (this.poseSwitchRequest === request) this.poseSwitchRequest = null;
    });
    this.poseRequest = this.poseSwitchRequest = request;
    return request;
  },

  resetPoseFeedback() {
    this.poseEpoch++;
    this.stopVoice();
    const sessionId = this.sessionId, epoch = this.poseEpoch, currentSet = this.currentSet;
    if (!sessionId || this.workoutMode !== "ai" || this.sessionClosed) return;
    const exerciseIndex = this.currentExerciseIdx;
    const request = Promise.resolve(this.poseRequest).then(() => {
      if (sessionId === this.sessionId && epoch === this.poseEpoch) {
        return API.session.sendAngle(sessionId, null, "knee", true, currentSet, exerciseIndex, ++this.frameId);
      }
    }).then(data => {
      if (data && sessionId === this.sessionId && epoch === this.poseEpoch) {
        this.repCount = data.rep_count;
        this.updateHUDDisplay(null, data.state, 0, null);
      }
    }).catch(() => {}).finally(() => {
      if (this.poseRequest === request) this.poseRequest = null;
    });
    this.poseRequest = request;
  },

  queueSessionPause(paused) {
    const sessionId = this.sessionId;
    if (!sessionId || this.sessionClosed) return Promise.resolve(false);
    const request = Promise.resolve(this.poseRequest).then(async () => {
      const data = await API.session.setPaused(sessionId, paused);
      if (sessionId !== this.sessionId) return false;
      if (this.workoutMode === "ai" && data.current_set === this.currentSet &&
          data.exercise_index === this.currentExerciseIdx) {
        this.repCount = data.rep_count;
        this.updateSetsDisplay();
      }
      return true;
    }).catch(() => {
      if (sessionId === this.sessionId) Toast.error("Không thể cập nhật trạng thái phiên tập. Hãy thử lại.");
      return false;
    }).finally(() => {
      if (this.poseRequest === request) this.poseRequest = null;
    });
    this.poseRequest = request;
    return request;
  },

  updateHUDDisplay(angle, state, depthPct, cue) {
    this.currentAngle = angle;
    this.currentState = state;
    this.currentDepthPct = depthPct;

    const angleEl = document.getElementById("hud-angle-val");
    if (angleEl) angleEl.textContent = Number.isFinite(angle) ? `${Math.round(angle)}°` : "—";

    const fsmEl = document.getElementById("hud-fsm-badge");
    if (fsmEl) fsmEl.textContent = state;

    const bar = document.getElementById("hud-depth-bar");
    const barPct = document.getElementById("hud-depth-percent");
    if (bar) bar.style.width = `${depthPct}%`;
    if (barPct) barPct.textContent = `${Math.round(depthPct)}%`;

    const circle = document.getElementById("rep-progress-circle");
    if (circle) {
      const pct = Math.min(1, this.repCount / this.targetReps);
      circle.style.strokeDashoffset = `${440 - 440 * pct}`;
    }

    const countEl = document.getElementById("hud-rep-count");
    if (countEl) countEl.textContent = this.repCount;

    const banner = document.getElementById("hud-coach-banner");
    if (banner) {
      if (cue) {
        banner.textContent = `📢 ${cue}`;
        banner.className = "hud-coach-banner perfect";
      } else if (state === "STATE_DOWN") {
        banner.textContent = "✨ Độ sâu rất chuẩn! Đẩy thẳng người lên!";
        banner.className = "hud-coach-banner perfect";
      } else if (state === "STATE_GOING_DOWN") {
        banner.textContent = "🔻 Hạ thấp người thêm nữa nào!";
        banner.className = "hud-coach-banner warn";
      } else {
        banner.textContent = "";
      }
    }
  },

  onRepCounted() {
    Toast.success(`+1 Rep! Hoàn thành rep thứ ${this.repCount}! 🔥`);

    const repDial = document.querySelector(".rep-dial-card");
    if (repDial) {
      repDial.style.transform = "scale(1.05)";
      repDial.style.borderColor = "var(--accent-emerald)";
      setTimeout(() => {
        repDial.style.transform = "";
        repDial.style.borderColor = "";
      }, 250);
    }

    if (this.repCount >= this.targetReps && !this.setCompletionTimer) {
      if (this.currentSet < this.totalSets) {
        this.speak(`Tuyệt vời! Đã hoàn thành hiệp ${this.currentSet}. Hãy nghỉ ngơi phục hồi.`);
        Toast.success(`Chúc mừng bạn đã đạt chỉ tiêu hiệp ${this.currentSet}/${this.totalSets}!`);
      } else {
        this.speak(`Tuyệt vời! Bạn đã hoàn thành toàn bộ ${this.totalSets} hiệp bài ${this.exerciseName}!`);
        Toast.success(`Chúc mừng bạn đã hoàn thành bài ${this.exerciseName}!`);
      }
      this.setCompletionTimer = setTimeout(() => {
        this.setCompletionTimer = null;
        if (!this.isResting && this.isWorkingOut) this.completeCurrentSet();
      }, 1200);
    }
  },

  updateVoiceToggle() {
    const enabled = this.voiceCoach.enabled;
    const button = document.getElementById("btn-toggle-voice");
    button?.setAttribute("aria-pressed", String(enabled));
    if (button) button.disabled = !this.voiceCoach.supported;
    const icon = document.getElementById("voice-toggle-icon");
    if (icon) icon.textContent = enabled ? "🔊" : "🔇";
    const tag = document.getElementById("voice-status-tag");
    if (tag) {
      tag.textContent = enabled ? "BẬT" : "TẮT";
      tag.classList.toggle("badge-beginner", enabled);
    }
  },

  playVoiceEvent(event) {
    if (!this.voiceCoach?.enabled) return;
    this.stopStatusSpeech();
    this.voiceCoach.receive(event);
  },

  stopStatusSpeech() {
    if (!this.statusSpeech) return;
    this.statusSpeech = null;
    window.speechSynthesis.cancel();
  },

  stopVoice() {
    this.voiceCoach?.stop();
    this.stopStatusSpeech();
  },

  leave() {
    this.isWorkingOut = false;
    this.poseEpoch++;
    clearTimeout(this.setCompletionTimer);
    this.setCompletionTimer = null;
    this.poseSwitchRequest = null;
    clearInterval(this.sessionTimerInterval);
    clearInterval(this.restCountdownTimer);
    clearInterval(this.restTimerInterval);
    this.restTimerInterval = null;
    this.stopVoice();
    this.stopVideoSource();
    const button = document.getElementById("btn-toggle-workout");
    if (button) {
      button.innerHTML = "▶️ Tiếp tục tập";
      button.className = "btn btn-emerald";
    }
    return this.queueSessionPause(true);
  },

  speak(text) {
    const synth = window.speechSynthesis;
    if (!this.voiceCoach?.enabled || this.voiceCoach.busy || this.statusSpeech || !synth) return;
    const voice = synth.getVoices().find(candidate => /^vi(?:-|$)/i.test(candidate.lang));
    if (!voice) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = voice.lang;
    utterance.voice = voice;
    utterance.onend = utterance.onerror = () => {
      if (this.statusSpeech === utterance) this.statusSpeech = null;
    };
    this.statusSpeech = utterance;
    try {
      synth.speak(utterance);
    } catch {
      this.statusSpeech = null;
    }
  },

  async finishWorkout(outcome = "completed") {
    if (this.sessionClosing || this.sessionClosed || !this.sessionId) return;
    const sessionId = this.sessionId;
    this.sessionClosing = true;
    try {
      await this.leave();
      const elapsed = this.sessionStartTime ? Math.floor((Date.now() - this.sessionStartTime) / 1000) : 0;
      const reps = this.workoutMode === "ai"
        ? (await API.session.summary(sessionId)).total_reps
        : [...this.manualSetReps.values()].reduce((total, count) => total + count, 0);
      if (sessionId !== this.sessionId) return;
      this.openRPEEvaluationModal(reps, elapsed, outcome);
    } catch {
      Toast.error("Không thể lấy kết quả buổi tập. Hãy thử lại.");
    } finally {
      this.sessionClosing = false;
    }
  },

  async saveWorkoutResult(reps, durationSeconds, rpe, notes, outcome) {
    const sessionId = this.sessionId;
    const result = await API.session.finish({
      sessionId,
      exerciseId: this.exerciseId,
      completedReps: this.workoutMode === "manual" ? reps : undefined,
      durationSeconds, rpe, notes, day: this.day, outcome,
    });
    if (sessionId !== this.sessionId) return result;
    this.sessionClosed = true;
    this.isResting = false;
    const overlay = document.getElementById("hud-rest-overlay");
    if (overlay) overlay.style.display = "none";
    Toast.success(outcome === "abandoned" ? "Đã lưu buổi tập với trạng thái bỏ dở." : "Đã ghi nhận buổi tập vào nhật ký!");
    await window.navigateTo("progress", true);
    return result;
  },

  openRPEEvaluationModal(reps, durationSec, outcome = "completed") {
    const sessionId = this.sessionId;
    const modal = document.getElementById("modal-rpe");
    const body = document.getElementById("rpe-modal-body");
    if (!modal || !body) return;
    const abandoned = outcome === "abandoned";

    body.innerHTML = `
      <div style="text-align: center; margin-bottom: 1.5rem;">
        <h3 style="font-size: 1.4rem; font-weight: 800; color: var(--text-primary);">
          ${abandoned ? "Bỏ dở buổi tập?" : "Hoàn thành buổi tập"}
        </h3>
        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.2rem;">
          Bạn đã ghi nhận <b>${reps} reps</b> trong <b>${Math.floor(durationSec / 60)}p ${durationSec % 60}s</b>.
        </p>
      </div>

      ${abandoned ? "" : `<div style="margin-bottom: 1.5rem;">
        <label class="form-label" style="font-size: 0.95rem;">
          Đánh giá mức độ kiệt sức RPE (Borg Scale 1 - 10):
        </label>
        <div style="display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem;">
          <input type="range" id="rpe-slider" min="1" max="10" value="5" style="flex: 1; accent-color: var(--accent-cyan);" />
          <span id="rpe-display-val" style="font-size: 1.5rem; font-weight: 800; color: var(--accent-cyan); width: 40px; text-align: center;">5</span>
        </div>
        <div id="rpe-modal-desc" style="font-size: 0.85rem; color: var(--accent-amber); font-weight: 600; margin-top: 0.35rem; text-align: center;">
          😤 Vừa sức lý tưởng (Nhịp tập ổn định)
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-top: 0.4rem;">
          <span>1: Rất nhẹ 😌</span>
          <span>5: Vừa sức 😤</span>
          <span>10: Kiệt sức 🤯</span>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Ghi chú cảm nhận cơ bắp (tùy chọn):</label>
        <textarea class="form-input" id="rpe-notes" rows="2" placeholder="VD: Khớp gối êm, cơ đùi trước căng mỏi tốt..."></textarea>
      </div>`}

      <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
        ${abandoned ? '<button class="btn btn-outline" id="btn-cancel-abandon">Quay lại</button>' : ""}
        <button class="btn btn-emerald" id="btn-submit-rpe" style="width: 100%;">
          ${abandoned ? "Xác nhận bỏ dở" : "💾 Lưu kết quả & Mở Màn hình Đánh giá Phục hồi"}
        </button>
      </div>
    `;

    modal.classList.add("active");

    const slider = body.querySelector("#rpe-slider");
    const valDisp = body.querySelector("#rpe-display-val");
    const descDisp = body.querySelector("#rpe-modal-desc");
    const rpeDescs = {
      1: "😌 Rất nhẹ (Gần như không thấy mệt)",
      2: "🙂 Nhẹ nhàng, hít thở thoải mái",
      3: "😊 Vừa phải (Bắt đầu làm nóng cơ thể)",
      4: "😉 Hơi thử thách nhẹ, còn rất nhiều sức",
      5: "😤 Vừa sức lý tưởng (Nhịp tập ổn định)",
      6: "😅 Khá mệt nhưng vẫn kiểm soát kỹ thuật",
      7: "😓 Nặng (Cơ bắp bắt đầu mỏi rõ rệt)",
      8: "😫 Rất mệt (Thở dốc, cần tập trung cao)",
      9: "🥵 Cực kỳ nặng (Gần ngưỡng chịu đựng)",
      10: "🤯 Kiệt sức hoàn toàn (Không thể làm thêm 1 rep)"
    };
    slider?.addEventListener("input", (e) => {
      const v = parseInt(e.target.value) || 5;
      if (valDisp) valDisp.textContent = v;
      if (descDisp) descDisp.textContent = rpeDescs[v] || "";
    });
    body.querySelector("#btn-cancel-abandon")?.addEventListener("click", () => modal.classList.remove("active"));

    body.querySelector("#btn-submit-rpe")?.addEventListener("click", async () => {
      if (sessionId !== this.sessionId || this.sessionClosing || this.sessionClosed) return;
      this.sessionClosing = true;
      const rpeVal = parseInt(slider?.value) || 5;
      const notes = body.querySelector("#rpe-notes")?.value || "";

      try {
        await this.saveWorkoutResult(reps, durationSec, rpeVal, notes, outcome);
        modal.classList.remove("active");
      } catch (e) {
        Toast.error("Lỗi lưu kết quả: " + e.message);
      } finally {
        this.sessionClosing = false;
      }
    });
  },
};
