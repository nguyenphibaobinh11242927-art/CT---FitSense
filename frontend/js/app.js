/**
 * FitSense Main Application Entry Point
 * SPA View Router, Authentication Controller, Theme Manager & Event Coordinator
 */

import { API } from "./api.js?v=3.0.0";
import { Store } from "./state.js?v=3.0.0";
import { Toast } from "./components/toast.js?v=3.0.0";
import { Capybara } from "./components/capybara.js?v=3.0.0";

import { DashboardView } from "./views/dashboard.js?v=3.0.0";
import { PlannerView } from "./views/planner.js?v=3.0.0";
import { LibraryView } from "./views/library.js?v=3.0.0";
import { WorkoutView } from "./views/workout.js?v=3.0.0";
import { ProgressView } from "./views/progress.js?v=3.0.0";
import { ProfileView } from "./views/profile.js?v=3.0.0";

const VIEWS = {
  dashboard: DashboardView,
  planner: PlannerView,
  library: LibraryView,
  workout: WorkoutView,
  progress: ProgressView,
  profile: ProfileView,
};

class FitSenseApp {
  constructor() {
    this.currentView = "dashboard";
    this.pendingGoogleUser = null;
  }

  async init() {
    console.log("⚡ Initializing FitSense Calisthenics Modern Web Platform...");

    // Setup Theme
    this.setupTheme();

    // Setup Navigation Listeners
    this.setupNavigation();

    // Setup Authentication Events (Login, Register, Google OAuth, Auth Gate)
    this.setupAuthHandlers();
    this.initGoogleIdentity();

    // Close Modals when clicking backdrop or close buttons
    this.setupModals();

    // Global helper methods for cross-view navigation
    window.navigateTo = (viewName, forceRefresh = false) => this.switchView(viewName, true, forceRefresh);
    window.startWorkoutSession = (
      exId,
      exName,
      reps,
      day,
      exerciseListOrPrescription = [],
      prescription = {}
    ) => {
      const exerciseList = Array.isArray(exerciseListOrPrescription)
        ? exerciseListOrPrescription
        : [];
      const selectedPrescription = Array.isArray(exerciseListOrPrescription)
        ? prescription
        : exerciseListOrPrescription || prescription;
      this.switchView("workout");
      WorkoutView.startSession(exId, exName, reps, day, exerciseList, selectedPrescription);
    };

    // Check Authentication Status:
    // If not logged in, enforce Auth Gate and DO NOT show app wrapper or stats!
    try {
      const auth = await API.auth.me();
      if (auth && auth.is_logged_in && auth.user) {
        await this.showApp(auth.user);
      } else {
        this.showAuthGate();
      }
    } catch (e) {
      console.warn("Could not check authentication status:", e);
      this.showAuthGate();
    }
  }

  showAuthGate() {
    this._activeUserEmail = null;
    ProgressView.resetState();
    const gate = document.getElementById("auth-gate-screen");
    const appWrapper = document.getElementById("app-wrapper");
    if (gate) gate.style.display = "flex";
    if (appWrapper) appWrapper.style.display = "none";
  }

  async showApp(user) {
    const nextEmail = user?.email || null;
    if (this._activeUserEmail !== nextEmail) {
      ProgressView.resetState();
      this._activeUserEmail = nextEmail;
    }
    const gate = document.getElementById("auth-gate-screen");
    const appWrapper = document.getElementById("app-wrapper");
    if (gate) gate.style.display = "none";
    if (appWrapper) appWrapper.style.display = "block";

    // Check API Health
    await this.checkSystemHealth();

    // Initialize Capybara Mascot
    await Capybara.init();

    // Load initial user state into Header
    await this.loadUserProfileHeader();

    // Route based on URL hash or default to dashboard
    const initialHash = window.location.hash.replace("#", "") || "dashboard";
    await this.switchView(VIEWS[initialHash] ? initialHash : "dashboard");

    // Pre-warm other tabs silently in background so switching tabs is 0ms instantaneous
    this.prewarmAllViews();

    // Check and show daily welcome popup
    await this.checkAndShowDailyWelcome();
  }

  prewarmAllViews() {
    const order = ["workout", "planner", "library", "progress", "profile", "dashboard"];
    order.forEach((viewKey, idx) => {
      if (viewKey === this.currentView) return;
      setTimeout(() => {
        const sec = document.getElementById(`view-${viewKey}`);
        if (sec && sec.children.length === 0 && VIEWS[viewKey]) {
          VIEWS[viewKey].render(false).catch(() => {});
        }
      }, 150 + idx * 180);
    });
  }

  async checkAndShowDailyWelcome() {
    if (sessionStorage.getItem("fitsense_welcome_shown")) return;

    try {
      const [weekData, user] = await Promise.all([
        API.planner.getWeek(),
        API.profile.get().catch(() => null),
      ]);

      const todayName = weekData.today_name || "Thứ 2";
      const schedule = weekData.schedule || [];
      const todayDay = schedule.find((d) => d.day.toLowerCase() === todayName.toLowerCase()) || schedule[0];

      if (!todayDay) return;

      const modal = document.getElementById("modal-welcome-daily");
      const body = document.getElementById("welcome-daily-body");
      if (!modal || !body) return;

      const userName = user ? user.name : "Vận động viên";

      body.innerHTML = `
        <div style="text-align: center; margin-bottom: 1.25rem;">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">⚡</div>
          <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0.25rem;">
            Chào mừng trở lại, ${userName}!
          </h3>
          <p style="font-size: 0.88rem; color: var(--text-secondary);">
            Hôm nay là <b>${todayName}</b>. Cùng xem kế hoạch rèn luyện hôm nay của bạn nhé:
          </p>
        </div>

        <div class="fitsense-card" style="margin-bottom: 1.25rem; border-color: var(--accent-cyan); background: rgba(56, 189, 248, 0.05);">
          <div style="font-size: 0.8rem; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase;">
            Trọng tâm ${todayDay.day}:
          </div>
          <div style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary); margin: 0.25rem 0;">
            ${todayDay.focus}
          </div>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">
            💡 ${todayDay.ai_reason}
          </div>
        </div>

        ${todayDay.is_rest ? `
          <div style="text-align: center; padding: 1.5rem 1rem; color: var(--text-muted); background: var(--surface-card); border-radius: var(--radius-md); margin-bottom: 1.5rem;">
            <div style="font-size: 2rem; margin-bottom: 0.3rem;">🛌</div>
            <div style="font-weight: 700; color: var(--text-primary);">Hôm nay là Ngày Nghỉ Ngơi Phục Hồi!</div>
            <p style="font-size: 0.85rem; margin-top: 0.2rem;">Hãy đi dạo nhẹ nhàng hoặc thả lỏng để cơ bắp phục hồi nhé.</p>
          </div>
        ` : `
          <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted); margin-bottom: 0.5rem;">
              DANH SÁCH BÀI TẬP (${todayDay.exercises?.length || 0} bài):
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem; max-height: 200px; overflow-y: auto;">
              ${(todayDay.exercises || []).map((ex) => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0.8rem; background: var(--surface-card); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
                  <div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: var(--text-primary);">${ex.name}</div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">${ex.primary_muscle || "Toàn thân"} • ${ex.equipment || "Bodyweight"}</div>
                  </div>
                  <span class="badge badge-beginner" style="font-size: 0.78rem;">${ex.sets} sets × ${ex.reps}</span>
                </div>
              `).join("")}
            </div>
          </div>
        `}

        <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
          <button class="btn btn-outline" id="btn-close-daily-welcome">
            Để sau
          </button>
          ${todayDay.is_rest ? "" : `
            <button class="btn btn-emerald" id="btn-start-daily-welcome">
              🚀 Bắt đầu ngay buổi hôm nay
            </button>
          `}
        </div>
      `;

      modal.classList.add("active");
      sessionStorage.setItem("fitsense_welcome_shown", "true");

      body.querySelector("#btn-close-daily-welcome")?.addEventListener("click", () => {
        modal.classList.remove("active");
      });

      body.querySelector("#btn-start-daily-welcome")?.addEventListener("click", () => {
        modal.classList.remove("active");
        const firstEx = todayDay.exercises?.[0];
        if (firstEx) {
          window.startWorkoutSession(firstEx.id || "squat", firstEx.name, parseInt(firstEx.reps) || 12, todayDay.day);
        }
      });
    } catch (e) {
      console.warn("Could not show daily welcome modal:", e);
    }
  }

  setupTheme() {
    const savedTheme = localStorage.getItem("fitsense_theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);

    const themeToggleBtn = document.getElementById("btn-theme-toggle");
    if (themeToggleBtn) {
      themeToggleBtn.textContent = savedTheme === "dark" ? "🌙" : "☀️";
      themeToggleBtn.addEventListener("click", () => {
        const curr = document.documentElement.getAttribute("data-theme") || "dark";
        const next = curr === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        localStorage.setItem("fitsense_theme", next);
        themeToggleBtn.textContent = next === "dark" ? "🌙" : "☀️";
        Toast.info(`Đã chuyển sang chế độ ${next === "dark" ? "Obsidian Dark" : "Frost Light"}`);
      });
    }
  }

  setupNavigation() {
    document.querySelectorAll(".nav-item").forEach((btn) => {
      // Switch immediately on pointerdown for 0ms perceived latency
      btn.addEventListener("pointerdown", (e) => {
        if (e.button !== undefined && e.button !== 0) return;
        const view = btn.getAttribute("data-view");
        if (view && view !== this.currentView) {
          this.switchView(view);
        }
      });

      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const view = btn.getAttribute("data-view");
        if (view && view !== this.currentView) {
          this.switchView(view);
        }
      });
    });

    window.addEventListener("hashchange", () => {
      const hash = window.location.hash.replace("#", "");
      if (VIEWS[hash] && hash !== this.currentView) {
        this.switchView(hash, false);
      }
    });
  }

  async switchView(viewName, updateHash = true, forceRefresh = false) {
    if (!VIEWS[viewName]) return;

    if (this.currentView === "workout" && viewName !== "workout") WorkoutView.leave();
    this.currentView = viewName;
    if (updateHash && window.location.hash !== `#${viewName}`) {
      history.replaceState(null, "", `#${viewName}`);
    }

    // Update active nav button immediately
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-view") === viewName);
    });

    const targetSection = document.getElementById(`view-${viewName}`);
    const isFirstTime = !targetSection || targetSection.children.length === 0;

    // Immediately show target section and hide other sections (0ms latency)
    document.querySelectorAll(".view-section").forEach((sec) => {
      if (sec !== targetSection) {
        sec.classList.remove("active");
      }
    });

    if (targetSection) {
      targetSection.classList.add("active");
    }

    // Fast scroll reset without locking smooth animation hitch
    if (window.scrollY > 40) {
      window.scrollTo(0, 0);
    }

    // Yield one frame so the browser paints the newly switched tab at 0ms before running any render logic
    if (!isFirstTime && !forceRefresh) {
      setTimeout(() => {
        VIEWS[viewName].render(false).catch((err) => {
          console.error(`Error refreshing view ${viewName}:`, err);
        });
      }, 0);
    } else {
      try {
        await VIEWS[viewName].render(true);
        if (forceRefresh && viewName === "progress") void Capybara.refresh();
      } catch (err) {
        console.error(`Error rendering view ${viewName}:`, err);
      }
    }
  }

  async checkSystemHealth() {
    try {
      const health = await API.health();
      const statusPill = document.getElementById("server-status-pill");
      if (statusPill) {
        statusPill.innerHTML = `
          <span class="status-dot"></span>
          <span>Trực tuyến</span>
        `;
      }
    } catch (e) {
      const statusPill = document.getElementById("server-status-pill");
      if (statusPill) {
        statusPill.innerHTML = `
          <span class="status-dot" style="background: var(--accent-crimson);"></span>
          <span style="color: var(--accent-crimson);">Mất kết nối</span>
        `;
      }
    }
  }

  async loadUserProfileHeader() {
    const container = document.getElementById("nav-auth-container");
    if (!container) return;

    try {
      const auth = await API.auth.me();
      if (auth.is_logged_in && auth.user) {
        const user = auth.user;
        const initial = (user.name || "U").charAt(0).toUpperCase();

        container.innerHTML = `
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div class="user-profile-badge" id="nav-user-chip" title="Xem hồ sơ cá nhân">
              <div class="user-avatar">${initial}</div>
              <span class="user-name">${user.name}</span>
            </div>
            <button class="btn-logout-small" id="btn-header-logout" title="Đăng xuất">
              Đăng xuất
            </button>
          </div>
        `;

        container.querySelector("#nav-user-chip")?.addEventListener("click", () => {
          this.switchView("profile");
        });

        container.querySelector("#btn-header-logout")?.addEventListener("click", async () => {
          await API.auth.logout();
          Toast.info("Đã đăng xuất khỏi tài khoản.");
          this.showAuthGate();
        });
      } else {
        // Unauthenticated State (No Demo User)
        container.innerHTML = `
          <button class="btn-auth-trigger" id="btn-header-login">
            <span>🔐</span>
            <span>Đăng nhập</span>
          </button>
        `;

        container.querySelector("#btn-header-login")?.addEventListener("click", () => {
          this.openAuthModal();
        });
      }
    } catch (e) {
      container.innerHTML = `
        <button class="btn-auth-trigger" id="btn-header-login">
          <span>🔐</span>
          <span>Đăng nhập</span>
        </button>
      `;
      container.querySelector("#btn-header-login")?.addEventListener("click", () => {
        this.openAuthModal();
      });
    }
  }

  openAuthModal(defaultTab = "login") {
    const modal = document.getElementById("modal-auth");
    if (!modal) return;
    this.switchAuthTab(defaultTab);
    modal.classList.add("active");
  }

  switchAuthTab(tab) {
    const btnLogin = document.getElementById("tab-btn-login");
    const btnReg = document.getElementById("tab-btn-register");
    const panelLogin = document.getElementById("panel-login");
    const panelReg = document.getElementById("panel-register");

    if (tab === "login") {
      btnLogin?.classList.add("active");
      btnReg?.classList.remove("active");
      panelLogin?.classList.add("active");
      panelReg?.classList.remove("active");
    } else {
      btnReg?.classList.add("active");
      btnLogin?.classList.remove("active");
      panelReg?.classList.add("active");
      panelLogin?.classList.remove("active");
    }
  }

  switchGateAuthTab(tab) {
    const btnLogin = document.getElementById("gate-tab-login");
    const btnReg = document.getElementById("gate-tab-register");
    const panelLogin = document.getElementById("gate-panel-login");
    const panelReg = document.getElementById("gate-panel-register");

    if (tab === "login") {
      btnLogin?.classList.add("active");
      btnReg?.classList.remove("active");
      panelLogin?.classList.add("active");
      panelReg?.classList.remove("active");
    } else {
      btnReg?.classList.add("active");
      btnLogin?.classList.remove("active");
      panelReg?.classList.add("active");
      panelLogin?.classList.remove("active");
    }
  }

  setupAuthHandlers() {
    // Gate Tab switching
    document.getElementById("gate-tab-login")?.addEventListener("click", () => this.switchGateAuthTab("login"));
    document.getElementById("gate-tab-register")?.addEventListener("click", () => this.switchGateAuthTab("register"));

    // Gate Form Login Submit
    document.getElementById("gate-form-login")?.addEventListener("submit", async () => {
      const email = document.getElementById("gate-login-email")?.value.trim();
      const password = document.getElementById("gate-login-password")?.value;

      if (!email || !password) {
        Toast.error("Vui lòng điền đầy đủ Email và Mật khẩu!");
        return;
      }

      try {
        const res = await API.auth.login(email, password);
        Toast.success(res.message || "Đăng nhập thành công!");
        await this.showApp(res.user);
      } catch (err) {
        Toast.error(err.message);
      }
    });

    // Gate Form Register Submit
    document.getElementById("gate-form-register")?.addEventListener("submit", async () => {
      const name = document.getElementById("gate-reg-name")?.value.trim();
      const email = document.getElementById("gate-reg-email")?.value.trim();
      const password = document.getElementById("gate-reg-password")?.value;
      const confirm = document.getElementById("gate-reg-password-confirm")?.value;

      if (!name || !email || !password) {
        Toast.error("Vui lòng điền đủ Họ tên, Email và Mật khẩu!");
        return;
      }
      if (password.length < 6) {
        Toast.error("Mật khẩu phải có tối thiểu 6 ký tự!");
        return;
      }
      if (password !== confirm) {
        Toast.error("Mật khẩu xác nhận không trùng khớp!");
        return;
      }

      try {
        const res = await API.auth.register({ name, email, password });
        Toast.success(res.message || "Tạo tài khoản thành công!");
        await this.showApp(res.user);
      } catch (err) {
        Toast.error(err.message);
      }
    });

    // Modal Tab switching
    document.getElementById("tab-btn-login")?.addEventListener("click", () => this.switchAuthTab("login"));
    document.getElementById("tab-btn-register")?.addEventListener("click", () => this.switchAuthTab("register"));

    // Form Login Submit
    document.getElementById("form-login")?.addEventListener("submit", async () => {
      const email = document.getElementById("login-email")?.value.trim();
      const password = document.getElementById("login-password")?.value;

      if (!email || !password) {
        Toast.error("Vui lòng điền đầy đủ Email và Mật khẩu!");
        return;
      }

      try {
        const res = await API.auth.login(email, password);
        Toast.success(res.message || "Đăng nhập thành công!");
        document.getElementById("modal-auth")?.classList.remove("active");
        await this.showApp(res.user);
      } catch (err) {
        Toast.error(err.message);
      }
    });

    // Form Register Submit
    document.getElementById("form-register")?.addEventListener("submit", async () => {
      const name = document.getElementById("reg-name")?.value.trim();
      const email = document.getElementById("reg-email")?.value.trim();
      const password = document.getElementById("reg-password")?.value;
      const confirm = document.getElementById("reg-password-confirm")?.value;

      if (!name || !email || !password) {
        Toast.error("Vui lòng điền đủ Họ tên, Email và Mật khẩu!");
        return;
      }
      if (password !== confirm) {
        Toast.error("Mật khẩu xác nhận không trùng khớp!");
        return;
      }

      try {
        const res = await API.auth.register({ name, email, password });
        Toast.success(res.message || "Tạo tài khoản thành công!");
        document.getElementById("modal-auth")?.classList.remove("active");
        await this.showApp(res.user);
      } catch (err) {
        Toast.error(err.message);
      }
    });

    // Google Sign-In Buttons -> Open Official Google Account Chooser
    const openGoogleChooser = () => {
      // If official Google Client ID is configured and Google GIS OAuth2 is loaded, trigger real Google OAuth popup!
      if (this.googleClientId && window.google?.accounts?.oauth2) {
        if (!this.googleTokenClient) {
          this.setupGoogleTokenClient(this.googleClientId);
        }
        if (this.googleTokenClient) {
          try {
            this.googleTokenClient.requestAccessToken({ prompt: "select_account" });
            return;
          } catch (err) {
            console.warn("Could not trigger Google OAuth popup:", err);
          }
        }
      }

      const customBox = document.getElementById("google-custom-account-box");
      if (customBox) customBox.style.display = "none";
      this.renderSavedGoogleAccounts();
      document.getElementById("modal-google-chooser")?.classList.add("active");
    };

    document.getElementById("gate-btn-google-login")?.addEventListener("click", openGoogleChooser);
    document.getElementById("gate-btn-google-register")?.addEventListener("click", openGoogleChooser);
    document.getElementById("btn-google-login")?.addEventListener("click", openGoogleChooser);
    document.getElementById("btn-google-register")?.addEventListener("click", openGoogleChooser);

    // Save & Activate Google Client ID from UI
    document.getElementById("btn-save-google-config-id")?.addEventListener("click", async () => {
      const cid = document.getElementById("google-config-client-id")?.value.trim() || "";
      const statusEl = document.getElementById("google-client-id-status");
      if (cid) {
        localStorage.setItem("fitsense_google_client_id", cid);
        try {
          await API.auth.saveConfig(cid);
        } catch {}
        this.googleClientId = cid;
        if (statusEl) {
          statusEl.innerHTML = `<span style="color: #137333; font-weight: 600;">🟢 Đã lưu và kích hoạt Google Client ID!</span>`;
        }
        this.setupGoogleTokenClient(cid);
        Toast.success("Đã kích hoạt Google OAuth chính thức thành công!");
      } else {
        localStorage.removeItem("fitsense_google_client_id");
        try {
          await API.auth.saveConfig("");
        } catch {}
        this.googleClientId = "";
        this.googleTokenClient = null;
        if (statusEl) {
          statusEl.innerHTML = `<span style="color: #5f6368;">Đã xóa Client ID cá nhân.</span>`;
        }
        Toast.info("Đã xóa Client ID.");
      }
    });

    // Cancel Custom Google Account Box
    document.getElementById("btn-cancel-custom-google")?.addEventListener("click", () => {
      const customBox = document.getElementById("google-custom-account-box");
      if (customBox) customBox.style.display = "none";
    });

    // Custom Google Sign-in Form Submit (Use another account)
    document.getElementById("btn-submit-google-login")?.addEventListener("click", () => {
      const email = document.getElementById("google-input-email")?.value.trim();
      let name = document.getElementById("google-input-name")?.value.trim();
      if (!email || !email.includes("@")) {
        Toast.error("Vui lòng nhập địa chỉ Email Google/Gmail hợp lệ!");
        return;
      }
      if (!name) {
        name = email.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
      }
      this.saveGoogleAccount({ email, name, avatar_url: null });
      this.processGoogleAuth(email, name);
    });

    document.getElementById("google-input-email")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        document.getElementById("btn-submit-google-login")?.click();
      }
    });

    document.getElementById("google-input-name")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        document.getElementById("btn-submit-google-login")?.click();
      }
    });

    // Google Onboarding Form Submit
    document.getElementById("form-google-onboarding")?.addEventListener("submit", async () => {
      if (!this.pendingGoogleUser) return;

      const height_cm = parseFloat(document.getElementById("onboard-height")?.value) || 170;
      const weight_kg = parseFloat(document.getElementById("onboard-weight")?.value) || 65;
      const age = parseInt(document.getElementById("onboard-age")?.value, 10) || 22;
      const gender = document.getElementById("onboard-gender")?.value || "Nam";
      const fitness_level = document.getElementById("onboard-level")?.value || "Beginner (Người mới bắt đầu)";
      const goal = document.getElementById("onboard-goal")?.value || "Tăng cơ & Sức mạnh";

      try {
        const payload = {
          email: this.pendingGoogleUser.email,
          name: this.pendingGoogleUser.name,
          avatar_url: this.pendingGoogleUser.avatar_url,
          height_cm,
          weight_kg,
          age,
          gender,
          fitness_level,
          goal,
          environment: "Tại nhà (Home Workout)",
          restrictions: ["Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)"],
          equipment: ["Không có dụng cụ (Chỉ tập Bodyweight)"],
          days_per_week: 4,
          session_duration_minutes: 45,
        };

        const res = await API.auth.googleComplete(payload);
        Toast.success(res.message || "Đăng ký thành công!");

        document.getElementById("modal-google-onboarding")?.classList.remove("active");
        document.getElementById("modal-auth")?.classList.remove("active");

        this.pendingGoogleUser = null;
        await this.showApp(res.user);
      } catch (err) {
        Toast.error("Lỗi hoàn tất đăng ký: " + err.message);
      }
    });
  }

  getSavedGoogleAccounts() {
    try {
      const stored = localStorage.getItem("fitsense_saved_google_users");
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    // Default available Google accounts on this machine (matching Image 2)
    return [
      {
        name: "nntkhanh2540",
        email: "nntkhanh2540@clc.fitus.edu.vn",
        avatar_url: null,
      },
      {
        name: "Thùy Khanh",
        email: "nguyenkhanhyu07@gmail.com",
        avatar_url: null,
      },
    ];
  }

  saveGoogleAccount(acc) {
    if (!acc || !acc.email) return;
    try {
      let list = this.getSavedGoogleAccounts();
      list = list.filter((item) => item.email.toLowerCase() !== acc.email.toLowerCase());
      list.unshift({
        email: acc.email.toLowerCase(),
        name: acc.name || acc.email.split("@")[0],
        avatar_url: acc.avatar_url || null,
        last_used: Date.now(),
      });
      if (list.length > 5) list = list.slice(0, 5);
      localStorage.setItem("fitsense_saved_google_users", JSON.stringify(list));
    } catch (e) {
      console.warn("Could not save google user:", e);
    }
  }

  removeSavedGoogleAccount(email) {
    try {
      let list = this.getSavedGoogleAccounts();
      list = list.filter((item) => item.email.toLowerCase() !== email.toLowerCase());
      localStorage.setItem("fitsense_saved_google_users", JSON.stringify(list));
      this.renderSavedGoogleAccounts();
    } catch (e) {
      console.warn("Could not remove google user:", e);
    }
  }

  renderSavedGoogleAccounts() {
    const container = document.getElementById("google-accounts-picker-list");
    if (!container) return;

    const accounts = this.getSavedGoogleAccounts();

    const rowsHtml = accounts
      .map((acc, idx) => {
        const initial = (acc.name || acc.email).charAt(0).toUpperCase();
        // Distinct avatar colors matching Image 2
        const avatarBg = idx === 0 ? "#0284c7" : "#0d9488";
        const avatarContent = acc.avatar_url
          ? `<img src="${acc.avatar_url}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;" />`
          : `<span style="font-weight: 700; font-size: 1.05rem; color: #ffffff;">${initial}</span>`;

        const hasCustomName = acc.name && acc.name.toLowerCase() !== acc.email.split("@")[0].toLowerCase();

        return `
          <div class="google-acc-row" data-email="${acc.email}" data-name="${acc.name || ""}" data-avatar="${acc.avatar_url || ""}" style="display: flex; align-items: center; padding: 14px 10px; cursor: pointer; border-bottom: 1px solid #e0e0e0; transition: background 0.15s; border-radius: 4px;">
            <div style="width: 36px; height: 36px; min-width: 36px; border-radius: 50%; background: ${avatarBg}; display: flex; align-items: center; justify-content: center; margin-right: 14px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.12);">
              ${avatarContent}
            </div>
            <div style="flex: 1; text-align: left; overflow: hidden;">
              ${hasCustomName ? `
                <div style="font-weight: 500; font-size: 0.95rem; color: #1f1f1f; line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${acc.name}</div>
                <div style="font-size: 0.82rem; color: #5f6368; line-height: 1.3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${acc.email}</div>
              ` : `
                <div style="font-weight: 500; font-size: 0.95rem; color: #1f1f1f; line-height: 1.35; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${acc.email}</div>
              `}
            </div>
          </div>
        `;
      })
      .join("");

    const useAnotherHtml = `
      <div id="btn-use-another-account" style="display: flex; align-items: center; padding: 14px 10px; cursor: pointer; transition: background 0.15s; border-radius: 4px;">
        <div style="width: 36px; height: 36px; min-width: 36px; border-radius: 50%; background: #f1f3f4; display: flex; align-items: center; justify-content: center; margin-right: 14px;">
          <svg viewBox="0 0 24 24" style="width: 20px; height: 20px; fill: #5f6368;">
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
          </svg>
        </div>
        <div style="font-weight: 500; font-size: 0.95rem; color: #1f1f1f;">
          Use another account
        </div>
      </div>
    `;

    container.innerHTML = rowsHtml + useAnotherHtml;

    container.querySelectorAll(".google-acc-row").forEach((row) => {
      row.addEventListener("mouseenter", () => (row.style.background = "#f8f9fa"));
      row.addEventListener("mouseleave", () => (row.style.background = "transparent"));
      row.addEventListener("click", () => {
        const email = row.getAttribute("data-email");
        const name = row.getAttribute("data-name");
        const avatar_url = row.getAttribute("data-avatar");
        this.processGoogleAuth(email, name, avatar_url);
      });
    });

    const btnAnother = container.querySelector("#btn-use-another-account");
    if (btnAnother) {
      btnAnother.addEventListener("mouseenter", () => (btnAnother.style.background = "#f8f9fa"));
      btnAnother.addEventListener("mouseleave", () => (btnAnother.style.background = "transparent"));
      btnAnother.addEventListener("click", () => {
        const customBox = document.getElementById("google-custom-account-box");
        if (customBox) {
          customBox.style.display = customBox.style.display === "none" ? "block" : "none";
          if (customBox.style.display === "block") {
            document.getElementById("google-input-email")?.focus();
          }
        }
      });
    }
  }

  setupGoogleTokenClient(clientId) {
    if (!window.google?.accounts?.oauth2 || !clientId) return;
    try {
      this.googleTokenClient = window.google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope: "email profile openid",
        callback: async (tokenResponse) => {
          if (tokenResponse && tokenResponse.access_token) {
            try {
              const res = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
                headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
              });
              const userInfo = await res.json();
              this.saveGoogleAccount({
                email: userInfo.email,
                name: userInfo.name,
                avatar_url: userInfo.picture,
              });
              await this.processGoogleAuth(
                userInfo.email,
                userInfo.name,
                userInfo.picture,
                userInfo.sub
              );
            } catch (err) {
              console.error("Lỗi lấy thông tin Google:", err);
              Toast.error("Không thể lấy thông tin tài khoản Google: " + err.message);
            }
          } else if (tokenResponse && tokenResponse.error) {
            console.warn("Google OAuth response error:", tokenResponse);
            if (tokenResponse.error !== "popup_closed_by_user") {
              Toast.warning("Google OAuth: " + (tokenResponse.error_description || tokenResponse.error));
            }
          }
        },
        error_callback: (err) => {
          console.warn("Google Token Client error:", err);
          if (err?.type === "popup_failed_to_open") {
            Toast.warning("Trình duyệt đang chặn cửa sổ Popup. Vui lòng cho phép popup để chọn tài khoản Google.");
          }
        },
      });
      console.log("⚡ Google OAuth Token Client initialized with Client ID:", clientId.slice(0, 16) + "...");
    } catch (e) {
      console.warn("setupGoogleTokenClient error:", e);
    }
  }

  async initGoogleIdentity() {
    try {
      let clientId = "";
      try {
        const cfg = await API.auth.config();
        if (cfg && cfg.google_client_id) {
          clientId = cfg.google_client_id;
        }
      } catch {
        // Ignore network err
      }

      if (!clientId) {
        clientId = localStorage.getItem("fitsense_google_client_id") || "211629740739-utd4fhgshgoddif6puq44bq69tl5up8m.apps.googleusercontent.com";
      }

      this.googleClientId = clientId || "";
      if (clientId) {
        localStorage.setItem("fitsense_google_client_id", clientId);
      }

      const inputEl = document.getElementById("google-config-client-id");
      const statusEl = document.getElementById("google-client-id-status");
      if (inputEl && clientId) {
        inputEl.value = clientId;
      }
      if (statusEl) {
        if (clientId) {
          statusEl.innerHTML = `<span style="color: #137333; font-weight: 600;">🟢 Đang sử dụng Google OAuth Client ID (${clientId.slice(0, 16)}...)</span>`;
        } else {
          statusEl.innerHTML = `<span style="color: #5f6368;">Chưa cấu hình Client ID. (Đang dùng chế độ chọn tài khoản nội bộ)</span>`;
        }
      }

      if (!clientId) return;

      const setupGsi = () => {
        if (window.google?.accounts?.oauth2) {
          this.setupGoogleTokenClient(clientId);
        }
        if (!window.google?.accounts?.id) return;
        try {
          window.google.accounts.id.initialize({
            client_id: clientId,
            callback: (response) => this.handleGoogleCredentialResponse(response),
          });

          const container = document.getElementById("google-gsi-official-container");
          if (container) {
            container.innerHTML = "";
            container.style.display = "flex";
            window.google.accounts.id.renderButton(container, {
              theme: "outline",
              size: "large",
              text: "continue_with",
              shape: "rectangular",
              width: 380,
            });
          }
        } catch (err) {
          console.warn("Google Identity Services initialization warning:", err);
        }
      };

      if (window.google?.accounts?.id || window.google?.accounts?.oauth2) {
        setupGsi();
      } else {
        window.addEventListener("load", setupGsi);
        setTimeout(setupGsi, 1500);
      }
    } catch (e) {
      console.warn("initGoogleIdentity error:", e);
    }
  }

  async handleGoogleCredentialResponse(response) {
    if (!response || !response.credential) return;
    try {
      const base64Url = response.credential.split(".")[1];
      const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split("")
          .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join("")
      );
      const data = JSON.parse(jsonPayload);
      const email = data.email;
      const name = data.name || email.split("@")[0];
      const avatar_url = data.picture || null;
      const google_id = data.sub || null;

      this.saveGoogleAccount({ email, name, avatar_url });
      await this.processGoogleAuth(email, name, avatar_url, google_id);
    } catch (err) {
      console.error("Lỗi giải mã Google Token:", err);
      Toast.error("Không thể xử lý xác thực từ Google!");
    }
  }

  async processGoogleAuth(email, name, avatar_url = null, google_id = null) {
    document.getElementById("modal-google-chooser")?.classList.remove("active");

    try {
      const res = await API.auth.google({ email, name, avatar_url, google_id });

      if (res.is_new_user) {
        // Step 2: New Google Account -> Show Onboarding Modal
        this.pendingGoogleUser = res.google_data;
        const onboardName = document.getElementById("onboard-google-name");
        const onboardEmail = document.getElementById("onboard-google-email");
        const onboardAvatar = document.getElementById("onboard-google-avatar");

        if (onboardName) onboardName.textContent = res.google_data.name;
        if (onboardEmail) onboardEmail.textContent = res.google_data.email;
        if (onboardAvatar) {
          if (res.google_data.avatar_url) {
            onboardAvatar.innerHTML = `<img src="${res.google_data.avatar_url}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%;" />`;
          } else {
            onboardAvatar.textContent = (res.google_data.name || "G").charAt(0).toUpperCase();
          }
        }

        document.getElementById("modal-google-onboarding")?.classList.add("active");
      } else {
        // Existing User -> Login complete
        Toast.success(res.message || `Đăng nhập thành công với ${email}!`);
        document.getElementById("modal-auth")?.classList.remove("active");
        await this.showApp(res.user);
      }
    } catch (err) {
      Toast.error("Đăng nhập Google thất bại: " + err.message);
    }
  }

  setupModals() {
    document.querySelectorAll(".modal-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("click", (e) => {
        if (e.target === backdrop) {
          backdrop.classList.remove("active");
        }
      });
    });

    document.querySelectorAll(".modal-close-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const modal = btn.closest(".modal-backdrop");
        if (modal) modal.classList.remove("active");
      });
    });
  }
}

// Instantiate and start app on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  const app = new FitSenseApp();
  app.init();
});
