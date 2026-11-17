/**
 * FitSense Live Workout HUD & AI Vision View
 * Full MediaPipe Pose Tracking (Skeleton & Joints), Live Joint Angles, Real Webcam & Video Upload
 */

import { API } from "../api.js";
import { Toast } from "../components/toast.js";

// Helper: Calculate joint angle in degrees from three 2D/3D points [0, 180]
function angleAt(a, b, c) {
  if (!a || !b || !c) return null;
  const ux = a.x - b.x, uy = a.y - b.y;
  const vx = c.x - b.x, vy = c.y - b.y;
  if ((!ux && !uy) || (!vx && !vy)) return null;
  return Math.atan2(Math.abs(ux * vy - uy * vx), ux * vx + uy * vy) * (180 / Math.PI);
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
  exerciseId: "squat",
  exerciseName: "Bodyweight Squat",
  targetReps: 12,
  day: null,

  repCount: 0,
  currentAngle: 175,
  currentDepthPct: 0,
  currentState: "STATE_UP",
  isWorkingOut: false,
  isCameraRunning: false,
  videoSourceType: "none", // 'none' | 'camera' | 'file'
  videoFileName: "",
  isVoiceCoachEnabled: true,

  videoEl: null,
  canvasEl: null,
  ctx: null,
  stream: null,
  activeVideoUrl: null,
  animationLoopId: null,

  // Technical FPS tracker
  frameCount: 0,
  lastFpsTime: 0,

  sessionStartTime: 0,
  sessionTimerInterval: null,

  async render() {
    const container = document.getElementById("view-workout");
    if (!container) return;

    container.innerHTML = `
      <div class="workout-hud-container">
        <!-- Top HUD Bar -->
        <div class="hud-topbar">
          <div class="hud-ex-info">
            <h3 id="hud-exercise-title">🏋️ ${this.exerciseName}</h3>
            <span class="hud-ex-target" id="hud-target-text">Mục tiêu: ${this.targetReps} reps • Calisthenics chuẩn khoa học</span>
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
          <!-- Left Column: Stage & Tech Metrics Bar -->
          <div style="display: flex; flex-direction: column; width: 100%;">
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
                <div class="hud-gesture-badge">
                  <span>🤖 FSM: <b id="hud-fsm-badge">STATE_UP</b></span>
                </div>
              </div>

              <!-- Form Coach Banner (Camera/Video AI mode only, hidden on standby/manual) -->
              <div class="hud-coach-banner" id="hud-coach-banner" style="display: none;">
                🎯 Chuẩn bị sẵn sàng: Đứng thẳng trước camera để bắt đầu
              </div>

              <!-- Stage Standby / Hero Card (Prominent Call to Action) -->
              <div class="stage-standby-overlay" id="stage-standby">
                <div class="standby-icon-pulse">
                  <span style="font-size: 3rem;">📹</span>
                </div>
                <h3 class="standby-title">Màn hình Giám sát Chuyển động AI (Live Feed)</h3>
                <p class="standby-desc">
                  Bật camera trực tiếp hoặc tải file video bài tập lên để AI tự động vẽ khớp, đo góc chuyển động và đếm số rep.
                </p>
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
                <div style="font-size: 3rem; margin-bottom: 0.5rem;">📝</div>
                <h3 style="font-size: 1.4rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0.25rem;">
                  Chế độ Không dùng Camera
                </h3>
                <p style="font-size: 0.88rem; color: var(--text-secondary); max-width: 440px; margin-bottom: 1.5rem;">
                  Tự điều chỉnh hiệp tập và ghi nhận số reps hoàn thành thủ công.
                </p>

                <div class="manual-card-box" style="border: 2px solid var(--accent-cyan); border-radius: var(--radius-lg); padding: 1.5rem 2.5rem; margin-bottom: 1.5rem;">
                  <div style="font-size: 0.85rem; font-weight: 700; color: var(--accent-cyan); margin-bottom: 0.5rem;">SỐ REPS HIỆN TẠI</div>
                  <div style="font-size: 3.5rem; font-weight: 900; color: var(--text-primary);" id="manual-rep-counter">0</div>
                  <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;" id="manual-target-label">Mục tiêu: ${this.targetReps} reps</div>
                </div>

                <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; justify-content: center; margin-bottom: 1.5rem;">
                  <button class="btn btn-outline" id="btn-manual-rep-minus" style="font-size: 1.05rem; padding: 0.55rem 1.25rem; border-radius: var(--radius-full);">➖ 1 Rep</button>
                  <button class="btn btn-primary" id="btn-manual-rep-plus1" style="font-size: 1.05rem; padding: 0.55rem 1.5rem; font-weight: 800; border-radius: var(--radius-full);">➕ 1 Rep</button>
                  <button class="btn btn-primary" id="btn-manual-rep-plus5" style="font-size: 1.05rem; padding: 0.55rem 1.5rem; font-weight: 800; background: var(--accent-emerald); border-color: var(--accent-emerald); border-radius: var(--radius-full);">➕ 5 Reps</button>
                  <button class="btn btn-outline" id="btn-manual-rep-reset" style="padding: 0.55rem 1rem; border-radius: var(--radius-full);">🔄 Reset</button>
                </div>

                <div style="display: flex; gap: 1rem; align-items: center; justify-content: center; margin-top: 0.5rem;">
                  <button class="btn btn-outline btn-sm" id="btn-manual-rest-timer" style="border-radius: var(--radius-full);">⏱️ Nghỉ 60 giây</button>
                  <button class="btn btn-emerald" id="btn-manual-finish-workout" style="border-radius: var(--radius-full); font-weight: 700;">🏁 Hoàn thành buổi tập</button>
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
              <button class="btn btn-emerald" id="btn-toggle-workout" style="font-weight: 800; padding: 0.75rem 1rem;">
                ▶️ Bắt đầu tập luyện
              </button>

              <div class="hud-actions-row">
                <button class="btn btn-outline" style="flex: 1; font-weight: 700;" id="btn-toggle-camera">
                  📷 Bật Camera
                </button>
                <button class="btn btn-outline" style="flex: 1; font-weight: 700;" id="btn-sidebar-upload-video">
                  📁 Tải Video
                </button>
              </div>

              <div class="voice-coach-toggle" id="btn-toggle-voice">
                <span style="font-weight: 600;">🔊 HLV Giọng nói Tiếng Việt</span>
                <span class="badge badge-beginner" id="voice-status-tag">BẬT</span>
              </div>

              <button class="btn btn-primary" id="btn-finish-workout" style="margin-top: 0.5rem; font-weight: 700;">
                🏁 Hoàn thành buổi tập
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
    container.querySelector("#btn-toggle-voice")?.addEventListener("click", () => {
      this.isVoiceCoachEnabled = !this.isVoiceCoachEnabled;
      const tag = container.querySelector("#voice-status-tag");
      if (tag) {
        tag.textContent = this.isVoiceCoachEnabled ? "BẬT" : "TẮT";
        tag.className = this.isVoiceCoachEnabled ? "badge badge-beginner" : "badge";
      }
      Toast.info(this.isVoiceCoachEnabled ? "Đã bật HLV Giọng nói tiếng Việt" : "Đã tắt HLV Giọng nói");
    });

    // Finish Workout
    container.querySelector("#btn-finish-workout")?.addEventListener("click", () => {
      this.finishWorkout();
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
      this.updateHUDDisplay(this.currentAngle, this.currentState, false, this.currentDepthPct, null);
    };

    const standbyOverlay = container.querySelector("#stage-standby");

    btnCameraMode?.addEventListener("click", () => {
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
    });

    btnManualMode?.addEventListener("click", () => {
      btnManualMode.classList.add("active");
      btnCameraMode?.classList.remove("active");

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
      if (!this.isWorkingOut) this.startWorkout();
    });

    // Manual rep buttons
    container.querySelector("#btn-manual-rep-plus1")?.addEventListener("click", () => {
      this.repCount += 1;
      updateManualDisplay();
      this.speak(`${this.repCount}`);
      if (this.repCount >= this.targetReps) {
        Toast.success("Chúc mừng bạn đã đạt chỉ tiêu hiệp tập!");
      }
    });

    container.querySelector("#btn-manual-rep-plus5")?.addEventListener("click", () => {
      this.repCount += 5;
      updateManualDisplay();
      this.speak(`${this.repCount}`);
      if (this.repCount >= this.targetReps) {
        Toast.success("Chúc mừng bạn đã đạt chỉ tiêu hiệp tập!");
      }
    });

    container.querySelector("#btn-manual-rep-minus")?.addEventListener("click", () => {
      this.repCount = Math.max(0, this.repCount - 1);
      updateManualDisplay();
    });

    container.querySelector("#btn-manual-rep-reset")?.addEventListener("click", () => {
      this.repCount = 0;
      updateManualDisplay();
    });

    container.querySelector("#btn-manual-finish-workout")?.addEventListener("click", () => {
      this.finishWorkout();
    });

    let restCountdownTimer = null;
    container.querySelector("#btn-manual-rest-timer")?.addEventListener("click", () => {
      const restBtn = container.querySelector("#btn-manual-rest-timer");
      clearInterval(restCountdownTimer);
      let secondsLeft = 60;
      this.speak("Bắt đầu nghỉ giữa hiệp 60 giây.");
      restBtn.textContent = `⏱️ Đang nghỉ: ${secondsLeft}s`;
      restCountdownTimer = setInterval(() => {
        secondsLeft -= 1;
        if (secondsLeft <= 0) {
          clearInterval(restCountdownTimer);
          restBtn.textContent = "⏱️ Nghỉ 60 giây";
          this.speak("Hết thời gian nghỉ! Hãy vào hiệp tiếp theo.");
          Toast.info("Hết thời gian nghỉ! Sẵn sàng cho hiệp tiếp theo nhé!");
        } else {
          restBtn.textContent = `⏱️ Đang nghỉ: ${secondsLeft}s`;
        }
      }, 1000);
    });
  },

  async startSession(exerciseId, exerciseName, targetReps = 12, day = null) {
    this.exerciseId = exerciseId || "squat";
    this.exerciseName = exerciseName || "Bodyweight Squat";
    this.targetReps = targetReps || 12;
    this.day = day;
    this.repCount = 0;
    this.videoSourceType = "none";

    await this.render();

    try {
      const res = await API.session.start(this.exerciseId, this.targetReps, this.day);
      this.sessionId = res.session_id;
      Toast.success(`Sẵn sàng cho bài tập ${this.exerciseName}!`);
      this.speak(`Chào bạn! Hãy chuẩn bị bắt đầu bài tập ${this.exerciseName}.`);
    } catch (e) {
      console.warn("Could not create backend session:", e);
    }
  },

  startWorkout() {
    this.isWorkingOut = true;
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
  },

  pauseWorkout() {
    this.isWorkingOut = false;
    clearInterval(this.sessionTimerInterval);

    if (this.videoEl && this.videoSourceType === "file" && !this.videoEl.paused) {
      this.videoEl.pause();
    }

    const btn = document.getElementById("btn-toggle-workout");
    if (btn) {
      btn.innerHTML = "▶️ Tiếp tục tập";
      btn.className = "btn btn-emerald";
    }
    Toast.info("Đã tạm dừng buổi tập.");
  },

  async startCamera() {
    this.stopVideoSource();

    const stage = document.getElementById("hud-stage");
    const standby = document.getElementById("stage-standby");
    const btnCam = document.getElementById("btn-toggle-camera");
    const liveText = document.getElementById("hud-live-text");
    const statusText = document.getElementById("tech-ai-status");

    if (statusText) statusText.textContent = "⏳ Đang kết nối camera và khởi tạo MediaPipe AI...";

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: false,
      });

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

      if (!this.isWorkingOut) this.startWorkout();
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

    if (!this.isWorkingOut) this.startWorkout();
    this.startFrameAnalysisLoop();
    Toast.success(`Đã tải video: ${file.name}. AI bắt đầu phân tích từng khung hình!`);
    this.speak(`Đã tải video bài tập. AI đang theo dõi chuyển động.`);
  },

  stopVideoSource() {
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
    const DISPATCH_INTERVAL_MS = 100; // ~10 FPS calls to backend FSM
    this.frameCount = 0;
    this.lastFpsTime = performance.now();

    const step = () => {
      if (this.videoSourceType === "none" || !this.videoEl || !this.canvasEl || !this.ctx) return;

      const v = this.videoEl;
      const ctx = this.ctx;
      const canvas = this.canvasEl;

      if (v.readyState >= 2 && !v.paused && !v.ended) {
        const w = v.videoWidth || 640;
        const h = v.videoHeight || 360;

        if (canvas.width !== w || canvas.height !== h) {
          canvas.width = w;
          canvas.height = h;
        }

        // 1. Draw video frame directly onto canvas
        ctx.drawImage(v, 0, 0, w, h);

        // 2. Compute FPS
        this.frameCount++;
        const now = performance.now();
        if (now - this.lastFpsTime >= 1000) {
          const fps = ((this.frameCount * 1000) / (now - this.lastFpsTime)).toFixed(1);
          const fpsBadge = document.getElementById("tech-fps-badge");
          if (fpsBadge) fpsBadge.textContent = `FPS: ${fps}`;
          this.frameCount = 0;
          this.lastFpsTime = now;
        }

        // 3. Pose Detection
        if (poseDetectorInstance) {
          try {
            const results = poseDetectorInstance.detectForVideo(v, now);
            const pose = results?.landmarks?.[0] || null;

            if (pose && pose.length >= 29) {
              // Convert landmarks to pixel points
              const points = pose.map((p) => ((p.visibility ?? 1) >= 0.35 ? { x: p.x * w, y: p.y * h } : null));

              // Draw green skeleton bones
              ctx.strokeStyle = "#60ed86";
              ctx.lineWidth = 3;
              ctx.lineCap = "round";
              ctx.beginPath();
              for (const [start, end] of POSE_BONES) {
                const a = points[start];
                const b = points[end];
                if (!a || !b) continue;
                ctx.moveTo(a.x, a.y);
                ctx.lineTo(b.x, b.y);
              }
              ctx.stroke();

              // Draw amber joint dots
              ctx.fillStyle = "#ffbe36";
              for (const p of points.filter(Boolean)) {
                ctx.beginPath();
                ctx.arc(p.x, p.y, 4.5, 0, Math.PI * 2);
                ctx.fill();
                ctx.strokeStyle = "#ffffff";
                ctx.lineWidth = 1.5;
                ctx.stroke();
              }

              // Update Live Technical Metrics Panel
              const angles = this.updateTechnicalMetrics(points);

              // Calculate active exercise angle
              const isUpper = (this.exerciseId || "").toLowerCase().includes("pushup") ||
                              (this.exerciseId || "").toLowerCase().includes("dip") ||
                              (this.exerciseId || "").toLowerCase().includes("hit_dat");

              const detectedAngle = isUpper
                ? (angles.leftElbow || angles.rightElbow || this.currentAngle)
                : (angles.leftKnee || angles.rightKnee || this.currentAngle);

              // Draw joint angle text overlay right on active joint
              const activeJoint = isUpper ? (points[13] || points[14]) : (points[25] || points[26]);
              if (activeJoint && detectedAngle !== null) {
                ctx.save();
                // If canvas is mirrored, flip text context so angle reads naturally
                if (this.videoSourceType === "camera") {
                  ctx.scale(-1, 1);
                  ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
                  ctx.fillRect(-activeJoint.x - 70, activeJoint.y - 25, 65, 24);
                  ctx.font = "bold 15px monospace";
                  ctx.fillStyle = "#f59e0b";
                  ctx.fillText(`${Math.round(detectedAngle)}°`, -activeJoint.x - 64, activeJoint.y - 8);
                } else {
                  ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
                  ctx.fillRect(activeJoint.x + 10, activeJoint.y - 25, 65, 24);
                  ctx.font = "bold 15px monospace";
                  ctx.fillStyle = "#f59e0b";
                  ctx.fillText(`${Math.round(detectedAngle)}°`, activeJoint.x + 16, activeJoint.y - 8);
                }
                ctx.restore();
              }

              // Send to backend FSM rep counter
              if (now - lastDispatchTime > DISPATCH_INTERVAL_MS) {
                lastDispatchTime = now;
                if (this.isWorkingOut && this.sessionId && detectedAngle !== null) {
                  this.dispatchAngleToFSM(detectedAngle);
                }
              }
            } else {
              const statusEl = document.getElementById("tech-ai-status");
              if (statusEl) statusEl.textContent = "👀 Hãy đứng lùi lại để thấy rõ toàn thân trong khung hình.";
            }
          } catch (detErr) {
            // Frame detection error handled gracefully
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

  updateTechnicalMetrics(points) {
    let leftElbow = null;
    let rightElbow = null;
    let leftKnee = null;
    let rightKnee = null;

    if (points[11] && points[13] && points[15]) {
      leftElbow = Math.round(angleAt(points[11], points[13], points[15]));
    }
    if (points[12] && points[14] && points[16]) {
      rightElbow = Math.round(angleAt(points[12], points[14], points[16]));
    }
    if (points[23] && points[25] && points[27]) {
      leftKnee = Math.round(angleAt(points[23], points[25], points[27]));
    }
    if (points[24] && points[26] && points[28]) {
      rightKnee = Math.round(angleAt(points[24], points[26], points[28]));
    }

    const elElbowL = document.getElementById("val-elbow-left");
    const elElbowR = document.getElementById("val-elbow-right");
    const elKneeL = document.getElementById("val-knee-left");
    const elKneeR = document.getElementById("val-knee-right");

    if (elElbowL) elElbowL.textContent = leftElbow !== null ? `${leftElbow}°` : "—";
    if (elElbowR) elElbowR.textContent = rightElbow !== null ? `${rightElbow}°` : "—";
    if (elKneeL) elKneeL.textContent = leftKnee !== null ? `${leftKnee}°` : "—";
    if (elKneeR) elKneeR.textContent = rightKnee !== null ? `${rightKnee}°` : "—";

    const statusEl = document.getElementById("tech-ai-status");
    if (statusEl) {
      const activeAngle = (this.exerciseId.includes("pushup") || this.exerciseId.includes("dip"))
        ? (leftElbow || rightElbow)
        : (leftKnee || rightKnee);
      statusEl.textContent = activeAngle !== null
        ? `🎯 Đã nhận diện toàn thân · Góc đo rep: ${activeAngle}°`
        : `👀 Hãy đứng trong khung hình để thấy rõ khớp.`;
    }

    return { leftElbow, rightElbow, leftKnee, rightKnee };
  },

  async dispatchAngleToFSM(angle) {
    if (!this.sessionId) return;

    try {
      const data = await API.session.sendAngle(this.sessionId, angle);
      this.updateHUDDisplay(data.angle, data.state, data.rep_incremented, data.depth_pct, data.cue);

      if (data.rep_incremented) {
        this.repCount = data.rep_count;
        this.onRepCounted();
      }
    } catch (e) {
      // Backend FSM error handled gracefully
    }
  },

  updateHUDDisplay(angle, state, repIncremented, depthPct, cue) {
    this.currentAngle = angle;
    this.currentState = state;
    this.currentDepthPct = depthPct;

    const angleEl = document.getElementById("hud-angle-val");
    if (angleEl && angle !== null && !isNaN(angle)) {
      angleEl.textContent = `${Math.round(angle)}°`;
    }

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
        if (repIncremented) {
          this.speak(cue);
        }
      } else if (state === "STATE_DOWN") {
        banner.textContent = "✨ Độ sâu rất chuẩn! Đẩy thẳng người lên!";
        banner.className = "hud-coach-banner perfect";
      } else if (state === "STATE_GOING_DOWN") {
        banner.textContent = "🔻 Hạ thấp người thêm nữa nào!";
        banner.className = "hud-coach-banner warn";
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

    if (this.repCount >= this.targetReps) {
      this.speak(`Tuyệt vời! Bạn đã hoàn thành toàn bộ ${this.targetReps} reps!`);
      Toast.success("Chúc mừng bạn đã đạt chỉ tiêu hiệp tập!");
    }
  },

  speak(text) {
    if (!this.isVoiceCoachEnabled || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "vi-VN";
      utterance.rate = 1.05;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("TTS error:", e);
    }
  },

  async finishWorkout() {
    this.pauseWorkout();
    this.stopVideoSource();

    const elapsed = this.sessionStartTime ? Math.floor((Date.now() - this.sessionStartTime) / 1000) : 60;
    this.openRPEEvaluationModal(this.repCount, elapsed);
  },

  openRPEEvaluationModal(reps, durationSec) {
    const modal = document.getElementById("modal-rpe");
    const body = document.getElementById("rpe-modal-body");
    if (!modal || !body) return;

    body.innerHTML = `
      <div style="text-align: center; margin-bottom: 1.5rem;">
        <div style="font-size: 3rem; margin-bottom: 0.5rem;">🎉</div>
        <h3 style="font-size: 1.4rem; font-weight: 800; color: var(--text-primary);">Hoàn Thành Bài Tập!</h3>
        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.2rem;">
          Bạn đã ghi nhận <b>${reps} reps</b> trong <b>${Math.floor(durationSec / 60)}p ${durationSec % 60}s</b>.
        </p>
      </div>

      <div style="margin-bottom: 1.5rem;">
        <label class="form-label" style="font-size: 0.95rem;">
          Đánh giá mức độ kiệt sức RPE (Rate of Perceived Exertion: 1 - 10):
        </label>
        <div style="display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem;">
          <input type="range" id="rpe-slider" min="1" max="10" value="7" style="flex: 1; accent-color: var(--accent-cyan);" />
          <span id="rpe-display-val" style="font-size: 1.5rem; font-weight: 800; color: var(--accent-cyan); width: 40px; text-align: center;">7</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem;">
          <span>1: Rất nhẹ</span>
          <span>5: Vừa phải</span>
          <span>10: Kiệt sức tối đa</span>
        </div>
      </div>

      <div class="form-group">
        <label class="form-label">Ghi chú cảm nhận cơ bắp (tùy chọn):</label>
        <textarea class="form-input" id="rpe-notes" rows="2" placeholder="VD: Khớp gối êm, cơ đùi trước căng mỏi tốt..."></textarea>
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
        <button class="btn btn-emerald" id="btn-submit-rpe" style="width: 100%;">
          💾 Lưu kết quả & Cập nhật ma trận phục hồi
        </button>
      </div>
    `;

    modal.classList.add("active");

    const slider = body.querySelector("#rpe-slider");
    const valDisp = body.querySelector("#rpe-display-val");
    slider?.addEventListener("input", (e) => {
      if (valDisp) valDisp.textContent = e.target.value;
    });

    body.querySelector("#btn-submit-rpe")?.addEventListener("click", async () => {
      const rpeVal = parseInt(slider.value) || 7;
      const notes = body.querySelector("#rpe-notes")?.value || "";

      try {
        await API.session.finish({
          sessionId: this.sessionId || "local-session",
          exerciseId: this.exerciseId,
          completedReps: reps,
          durationSeconds: durationSec,
          rpe: rpeVal,
          notes,
          day: this.day,
          targetReps: this.targetReps,
        });

        modal.classList.remove("active");
        Toast.success("Đã ghi nhận buổi tập thành công vào nhật ký!");

        import("../components/capybara.js").then((m) => m.Capybara.refresh());
        window.navigateTo("progress");
      } catch (e) {
        Toast.error("Lỗi lưu kết quả: " + e.message);
      }
    });
  },
};
