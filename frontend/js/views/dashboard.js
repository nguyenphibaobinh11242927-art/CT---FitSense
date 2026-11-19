/**
 * FitSense Dashboard View
 */

import { API } from "../api.js";
import { Store } from "../state.js";

export const DashboardView = {
  lastRenderTime: 0,

  async render(forceRefresh = false) {
    const container = document.getElementById("view-dashboard");
    if (!container) return;

    const now = Date.now();
    if (!forceRefresh && container.children.length > 0 && (now - this.lastRenderTime < 30000)) {
      return;
    }

    try {
      const [stats, weekData, user] = await Promise.all([
        API.progress.stats(),
        API.planner.getWeek(),
        API.profile.get(),
      ]);
      this.lastRenderTime = Date.now();

      const todayName = weekData.today_name;
      const todaySchedule = weekData.schedule.find(
        (d) => d.day.toLowerCase() === todayName.toLowerCase()
      ) || weekData.schedule[0];

      const userName = user?.name || "Vận động viên";
      const userGoal = user?.goal || "Tăng cơ & Sức mạnh";

      const brandLogoSvg = (document.querySelector(".brand-logo")?.innerHTML || "")
        .replace(/hdrPinkG/g, "homeBannerPinkG")
        .replace(/hdrBlueG/g, "homeBannerBlueG");

      container.innerHTML = `
        <!-- Top Brand Hero Banner (Automatically adapts background to Light / Dark theme) -->
        <div class="home-hero-banner">
          <div class="home-banner-left">
            <div class="home-banner-emblem" title="FitSense Infinity Kinetic Flow">
              ${brandLogoSvg}
            </div>
            <div class="home-banner-text">
              <h1 class="home-banner-title">FitSense</h1>
              <div class="home-banner-subtitle">CALISTHENICS &amp; AI VISION</div>
              <div class="home-banner-tagline">Nền tảng Huấn luyện viên Thể thao Cá nhân hóa &amp; Thị giác Máy tính AI</div>
            </div>
          </div>
          <div class="home-banner-accents" aria-hidden="true">
            <span style="width: 9px; height: 9px; border-radius: 50%; background: #f472b6; opacity: 0.8; display: inline-block;"></span>
            <span style="width: 13px; height: 13px; border-radius: 50%; background: #38bdf8; opacity: 0.9; display: inline-block;"></span>
            <span style="width: 7px; height: 7px; border-radius: 50%; background: #a855f7; opacity: 0.7; display: inline-block;"></span>
          </div>
        </div>

        <div class="view-header">
          <div class="view-title-group">
            <h2>⚡ Xin chào, ${userName}!</h2>
            <p>Hôm nay là <b>${todayName}</b>. Mục tiêu hiện tại của bạn: <b>${userGoal}</b>.</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-emerald" id="btn-dash-quick-workout">
              🚀 Vào phòng tập Live AI ngay
            </button>
          </div>
        </div>

        <!-- 4 Quick Stats (Reflects genuine user progress, starting from 0) -->
        <div class="stat-grid">
          <div class="stat-card">
            <div class="stat-icon amber">🔥</div>
            <div class="stat-info">
              <span class="stat-label">Chuỗi rèn luyện</span>
              <span class="stat-value">${stats.current_streak_days} ngày</span>
              <span class="stat-sub">${stats.has_worked_out_today ? "Đã hoàn thành hôm nay 🎉" : "Chưa hoàn thành hôm nay"}</span>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon cyan">🎯</div>
            <div class="stat-info">
              <span class="stat-label">Tổng số bài tập hoàn thành</span>
              <span class="stat-value">${stats.total_workouts} buổi</span>
              <span class="stat-sub">${stats.total_reps} reps tích lũy</span>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon emerald">⏱️</div>
            <div class="stat-info">
              <span class="stat-label">Thời gian tập luyện</span>
              <span class="stat-value">${stats.total_duration_min} phút</span>
              <span class="stat-sub">Độ chuẩn xác cao</span>
            </div>
          </div>

          <div class="stat-card">
            <div class="stat-icon purple">⚡</div>
            <div class="stat-info">
              <span class="stat-label">Năng lượng tiêu hao</span>
              <span class="stat-value">${stats.total_calories} kcal</span>
              <span class="stat-sub">${stats.total_workouts > 0 ? `RPE trung bình: ${stats.average_rpe}/10` : "Chưa ghi nhận buổi tập"}</span>
            </div>
          </div>
        </div>

        <!-- Today's Workout Focus -->
        <div class="fitsense-card" style="margin-bottom: 1.75rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <span style="font-size: 0.78rem; text-transform: uppercase; font-weight: 700; color: var(--accent-cyan); letter-spacing: 0.5px;">
                Lịch trình hôm nay (${todayName})
              </span>
              <h3 style="font-size: 1.3rem; font-weight: 800; margin-top: 0.2rem;">
                ${todaySchedule.focus}
              </h3>
            </div>
            ${todaySchedule.is_rest 
              ? `<span class="badge badge-beginner" style="font-size: 0.85rem; padding: 0.4rem 0.8rem;">🛌 Ngày nghỉ hồi phục</span>`
              : `<button class="btn btn-primary btn-sm" id="btn-start-today-session">▶️ Bắt đầu trọn bộ hôm nay</button>`
            }
          </div>

          <div class="ai-reason-box" style="margin-bottom: 1.25rem;">
            💡 <b>Ghi chú từ AI:</b> ${todaySchedule.ai_reason}
          </div>

          ${todaySchedule.exercises && todaySchedule.exercises.length > 0 
            ? `
              <div class="planner-exercise-grid">
                ${todaySchedule.exercises.map((ex, index) => `
                  <div class="planner-ex-card">
                    <div class="ex-card-top">
                      <div>
                        <div class="ex-card-title">${ex.name}</div>
                        <div style="font-size: 0.8rem; color: var(--text-muted); margin-top: 0.15rem;">
                          Thiết bị: ${ex.equipment || "Bodyweight"}
                        </div>
                      </div>
                      <span class="badge badge-intermediate">${ex.difficulty || "Beginner"}</span>
                    </div>

                    <div class="ex-card-metrics">
                      <span class="ex-metric">🔢 <strong>${ex.sets}</strong> hiệp</span>
                      <span class="ex-metric">🎯 <strong>${ex.reps}</strong> reps</span>
                      ${ex.hold_seconds > 0 ? `<span class="ex-metric">Giữ <strong>${ex.hold_seconds}s</strong> mỗi rep</span>` : ""}
                      <span class="ex-metric">⏱️ Nghỉ <strong>${ex.rest_sec ?? 60}s</strong></span>
                    </div>

                    <div class="ex-card-muscles">
                      <span class="muscle-pill">${ex.primary_muscle || "Toàn thân"}</span>
                      ${ex.secondary_muscle ? `<span class="muscle-pill">${ex.secondary_muscle}</span>` : ""}
                    </div>

                    <div class="ex-card-actions">
                      <button class="btn btn-outline btn-sm btn-dash-start-single" data-ex-index="${index}" ${ex.id ? "" : "disabled"}>
                        ▶️ Tập bài này
                      </button>
                    </div>
                  </div>
                `).join("")}
              </div>
            `
            : `
              <div style="text-align: center; padding: 2rem 1rem; color: var(--text-muted);">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🧘</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">Hôm nay là Ngày Nghỉ Ngơi (Rest Day)</div>
                <p style="font-size: 0.9rem; margin-top: 0.3rem;">Hãy để cơ bắp hồi phục và nạp năng lượng cho các buổi rèn luyện tiếp theo nhé!</p>
              </div>
            `
          }
        </div>

        <!-- Quick Access Banners -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.25rem;">
          <div class="fitsense-card" style="cursor: pointer;" id="card-nav-planner">
            <h4 style="font-size: 1.1rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
              📅 Kế hoạch & Tối ưu AI
            </h4>
            <p style="font-size: 0.88rem; color: var(--text-secondary);">
              Xem lịch tập 7 ngày, tạo giáo án mới bằng AI và đổi bài tập thông minh.
            </p>
          </div>

          <div class="fitsense-card" style="cursor: pointer;" id="card-nav-library">
            <h4 style="font-size: 1.1rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
              📚 Thư viện
            </h4>
            <p style="font-size: 0.88rem; color: var(--text-secondary);">
              Tra cứu kỹ thuật chuẩn, nhóm cơ tham gia, lỗi sai cần tránh và minh họa động tác.
            </p>
          </div>

          <div class="fitsense-card" style="cursor: pointer;" id="card-nav-progress">
            <h4 style="font-size: 1.1rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;">
              📊 Ma trận Phục hồi Cơ bắp
            </h4>
            <p style="font-size: 0.88rem; color: var(--text-secondary);">
              Theo dõi tình trạng hồi phục sinh học của 7 nhóm cơ và lịch sử các buổi tập.
            </p>
          </div>
        </div>
      `;

      // Event Listeners
      container.querySelector("#btn-dash-guest-login")?.addEventListener("click", () => {
        document.getElementById("modal-auth")?.classList.add("active");
      });

      container.querySelector("#btn-dash-quick-workout")?.addEventListener("click", () => {
        window.navigateTo("workout");
      });

      container.querySelector("#btn-start-today-session")?.addEventListener("click", () => {
        const firstEx = todaySchedule.exercises?.[0];
        if (firstEx) {
          window.startWorkoutSession(
            firstEx.id || "squat",
            firstEx.name,
            parseInt(firstEx.reps, 10) || 12,
            todaySchedule.day,
            todaySchedule.exercises || [],
            firstEx
          );
        } else {
          window.navigateTo("workout");
        }
      });

      container.querySelectorAll(".btn-dash-start-single").forEach((btn) => {
        btn.addEventListener("click", () => {
          const exercise = todaySchedule.exercises[Number(btn.dataset.exIndex)];
          if (!exercise) return;
          window.startWorkoutSession(
            exercise.id || "custom",
            exercise.name,
            parseInt(exercise.reps, 10) || 12,
            todaySchedule.day,
            [exercise, ...(todaySchedule.exercises || []).slice(Number(btn.dataset.exIndex) + 1)],
            exercise
          );
        });
      });

      container.querySelector("#card-nav-planner")?.addEventListener("click", () => window.navigateTo("planner"));
      container.querySelector("#card-nav-library")?.addEventListener("click", () => window.navigateTo("library"));
      container.querySelector("#card-nav-progress")?.addEventListener("click", () => window.navigateTo("progress"));
    } catch (err) {
      console.error("Dashboard render error:", err);
      container.innerHTML = `<div class="fitsense-card" style="color: var(--accent-crimson);">Lỗi tải bảng điều khiển: ${err.message}</div>`;
    }
  },
};
