/**
 * FitSense Progress, Evaluation & Muscle Recovery Heatmap View
 * Fully integrates Post-Workout Survey (RPE Borg Scale, Adaptive AI Deload/Overload),
 * Personal Records (PRs), Weekly Volume Chart, and 7-Muscle Heatmap Matrix.
 */

import { API } from "../api.js";
import { Toast } from "../components/toast.js";

export const ProgressView = {
  evalMeta: null,
  latestEvaluation: null,
  lastRenderTime: 0,

  async render(forceRefresh = false) {
    const container = document.getElementById("view-progress");
    if (!container) return;

    const now = Date.now();
    if (!forceRefresh && container.children.length > 0 && (now - this.lastRenderTime < 30000)) {
      return;
    }

    try {
      const [heatmapData, historyData, statsData, evalMetaData, evalsData, weekData] = await Promise.all([
        API.progress.heatmap(),
        API.progress.history(),
        API.progress.stats(),
        API.progress.evaluationMeta(),
        API.progress.evaluations(),
        API.planner.getWeek().catch(() => null),
      ]);
      this.lastRenderTime = Date.now();

      this.evalMeta = evalMetaData;
      const muscles = heatmapData.muscles || [];
      const history = historyData.history || [];
      const hasHistory = history.length > 0;
      const latestHistoryComp = hasHistory && history[0].completion_rate !== undefined
        ? Math.round(history[0].completion_rate)
        : 0;
      const evals = evalsData?.evaluations || [];
      this.evalsBySession = {};
      evals.forEach((ev) => {
        if (ev.session_id) {
          if (ev.scope === "exercise" && ev.exercise_id) {
            this.evalsBySession[`${ev.session_id}_${ev.exercise_id}`] = ev;
          } else {
            this.evalsBySession[ev.session_id] = ev;
          }
        }
      });
      if (this.latestEvaluation && this.latestEvaluation.session_id) {
        if (this.latestEvaluation.scope === "exercise" && this.latestEvaluation.exercise_id) {
          this.evalsBySession[`${this.latestEvaluation.session_id}_${this.latestEvaluation.exercise_id}`] = this.latestEvaluation;
        } else {
          this.evalsBySession[this.latestEvaluation.session_id] = this.latestEvaluation;
        }
      }

      // Xác định buổi tập đang chọn và kiểm tra xem buổi đó đã từng gửi khảo sát chưa
      const initialSelectedSessionId = this.selectedSessionId || (history.length > 0 ? history[0].id : null);
      this.selectedSessionId = initialSelectedSessionId;
      const initialEval = initialSelectedSessionId ? this.evalsBySession[initialSelectedSessionId] : null;
      const hasEvaluated = Boolean(initialEval);
      const selectedHistoryItem = history.find((h) => h.id === initialSelectedSessionId) || (history.length > 0 ? history[0] : null);
      const initialCompRate = selectedHistoryItem && selectedHistoryItem.completion_rate !== undefined
        ? Math.round(selectedHistoryItem.completion_rate)
        : latestHistoryComp;


      // Kiểm tra ngày nghỉ phục hồi (Rest Day) & điều kiện hiển thị khảo sát
      const schedule = weekData?.schedule || [];
      const todayName = weekData?.today_name || "";
      const todayPlan = schedule.find((d) => d.day === todayName);
      const isTodayRestDay = todayPlan
        ? Boolean(todayPlan.is_rest || !todayPlan.exercises || todayPlan.exercises.length === 0)
        : false;
      const todayIso = new Date().toISOString().slice(0, 10);
      const hasWorkoutToday = history.some((h) => {
        return h.actual_date === todayIso || h.day === todayName || h.day === "Hôm nay";
      }) || Boolean(statsData?.has_worked_out_today);
      const shouldShowSurvey = !isTodayRestDay || hasWorkoutToday;

      let recBadge = "badge-intermediate";
      let recStrategy = "Optimal Maintenance";
      let recTitle = "Khuyến nghị Giữ nguyên Nhịp độ (Optimal Maintenance) 😊";
      let recDesc = "Duy trì khối lượng và nhịp tập hiện tại để xây dựng nền tảng bền vững cho chu kỳ tuần tới!";
      let evalTime = "Vừa cập nhật";

      if (initialEval && initialEval.recommendation) {
        recBadge = initialEval.recommendation.badge || "badge-intermediate";
        recTitle = initialEval.recommendation.title || recTitle;
        recDesc = initialEval.recommendation.action || recDesc;
        const strat = initialEval.recommendation.strategy || initialEval.strategy || "maintenance";
        recStrategy = strat === "deload"
          ? "Deload -15%"
          : (strat === "overload" ? "Overload +10%" : (strat === "minor_deload" ? "Minor Deload -5%" : "Optimal Maintenance"));
        evalTime = initialEval.created_at || "Vừa cập nhật";
      }

      const prs = statsData.personal_records || {
        "Squat Thể dục": "Chưa ghi nhận",
        "Standard Push-up": "Chưa ghi nhận",
        "Plank Tĩnh": "Chưa ghi nhận",
        "Dips trên ghế": "Chưa ghi nhận",
      };
      const weeklyVolume = statsData.weekly_volume || [
        { week: "Tuần 1", reps: 0, minutes: 0 },
        { week: "Tuần 2", reps: 0, minutes: 0 },
        { week: "Tuần 3", reps: 0, minutes: 0 },
        { week: "Tuần 4", reps: 0, minutes: 0 },
        { week: "Tuần này", reps: 0, minutes: 0 },
      ];

      const totalWorkouts = history.length;
      const curStreak = statsData.current_streak_days ?? 0;
      const longestStreak = statsData.longest_streak_days ?? 0;
      const hasWorkedOut = statsData.has_worked_out_today ?? false;
      const avgCompletionRate = totalWorkouts > 0
        ? (statsData.average_completion_rate !== undefined ? statsData.average_completion_rate : 100)
        : 0;

      // Classify ready vs fatigued muscles
      const readyMuscles = muscles.filter((m) => m.recovery_pct >= 85);
      const fatiguedMuscles = muscles.filter((m) => m.recovery_pct < 85);

      container.innerHTML = `
        <div class="view-header">
          <div class="view-title-group">
            <h2>📊 Đánh giá & Ma trận Phục hồi Sinh học</h2>
            <p>Khảo sát thể lực RPE, khuyến nghị thích ứng tải trọng AI và theo dõi chu kỳ phục hồi 7 nhóm cơ.</p>
          </div>
        </div>

        <!-- 1. Top Metrics Summary Cards -->
        <div class="stats-grid" style="margin-bottom: 1.5rem;">
          <div class="stat-card">
            <span class="stat-icon">🔥</span>
            <div>
              <div class="stat-val">${curStreak} Ngày</div>
              <div class="stat-label">Chuỗi ngày (Streak) ${hasWorkedOut ? "• +1 hôm nay" : ""}</div>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">🏆</span>
            <div>
              <div class="stat-val">${longestStreak} Ngày</div>
              <div class="stat-label">Kỷ lục chuỗi dài nhất</div>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">✅</span>
            <div>
              <div class="stat-val">${totalWorkouts} Buổi</div>
              <div class="stat-label">Tổng buổi rèn luyện</div>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">⚡</span>
            <div>
              <div class="stat-val">${avgCompletionRate}%</div>
              <div class="stat-label">Tỉ lệ hoàn thành TB</div>
            </div>
          </div>
        </div>

        <!-- Fair Streak Rule Box -->
        <div class="ai-reason-box" style="margin-bottom: 1.75rem; border-color: var(--accent-cyan);">
          💡 <b>Quy tắc tính Streak thể thao công bằng:</b> Để tránh áp lực và bảo vệ sức khỏe khớp, bạn không bắt buộc phải hoàn thành 100% buổi tập. Chỉ cần hoàn thành từ <b>70% khối lượng bài tập trở lên</b>, hệ thống sẽ tự động ghi nhận duy trì Chuỗi ngày (Streak) thành công!
        </div>

        <!-- 2. Personal Records (PRs) Section -->
        <div style="margin-bottom: 2rem;">
          <h3 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
            🥇 Kỷ lục Động tác Tốt nhất (Personal Records - PRs)
          </h3>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
            ${Object.entries(prs).map(([name, val]) => `
              <div class="fitsense-card" style="padding: 1.1rem; text-align: center;">
                <div style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 0.3rem;">${name}</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: var(--accent-amber);">🥇 ${val}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem;">Kỷ lục cao nhất ghi nhận</div>
              </div>
            `).join("")}
          </div>
        </div>

        <!-- 3. Weekly Volume Chart Section -->
        <div class="fitsense-card" style="margin-bottom: 2rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <h3 style="font-size: 1.15rem; font-weight: 800;">📈 Biểu đồ Khối lượng Rèn luyện theo Tuần</h3>
              <p style="font-size: 0.82rem; color: var(--text-secondary);">Tăng tiến thể lực theo thời gian (Số Reps & Thời lượng)</p>
            </div>
            <span class="badge badge-emerald">Progressive Trend ↗️</span>
          </div>

          <div style="display: flex; align-items: flex-end; gap: 1.5rem; height: 180px; padding: 1rem 0; border-bottom: 1px solid var(--border-subtle); overflow-x: auto;">
            ${weeklyVolume.map((item) => {
              const maxReps = 400;
              const barHeightPct = Math.round((item.reps / maxReps) * 100);
              return `
                <div style="flex: 1; min-width: 65px; display: flex; flex-direction: column; align-items: center; height: 100%; justify-content: flex-end;">
                  <span style="font-size: 0.75rem; font-weight: 700; color: var(--accent-cyan); margin-bottom: 0.35rem;">${item.reps} rep</span>
                  <div style="width: 100%; max-width: 44px; height: ${barHeightPct}%; background: linear-gradient(180deg, var(--accent-cyan) 0%, rgba(56, 189, 248, 0.4) 100%); border-radius: 6px 6px 0 0; transition: height 0.4s ease;"></div>
                  <span style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 0.5rem;">${item.week}</span>
                </div>
              `;
            }).join("")}
          </div>
        </div>

        <!-- 4. Muscle Recovery Heatmap Matrix -->
        <div style="margin-bottom: 2rem;">
          <h3 style="font-size: 1.25rem; font-weight: 800; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
            🔥 Bảng nhiệt Phục hồi 7 Nhóm cơ (Muscle Recovery Heatmap)
          </h3>

          <div class="heatmap-grid" style="margin-bottom: 1.25rem;">
            ${muscles.map((m) => {
              const isFull = m.recovery_pct >= 90;
              const barColor = isFull ? "var(--accent-emerald)" : m.recovery_pct >= 70 ? "var(--accent-amber)" : "var(--accent-crimson)";
              return `
                <div class="heatmap-card">
                  <div class="heatmap-header">
                    <span class="heatmap-title">${m.name}</span>
                    <span class="heatmap-pct" style="color: ${barColor};">${m.recovery_pct}%</span>
                  </div>

                  <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: ${m.recovery_pct}%; background: ${barColor};"></div>
                  </div>

                  <div class="heatmap-footer">
                    <span style="font-weight: 600; color: ${barColor};">${m.status}</span>
                    <span>${m.hours_left > 0 ? `Còn ~${m.hours_left}h phục hồi` : "Phục hồi 100% ✨"}</span>
                  </div>
                </div>
              `;
            }).join("")}
          </div>

          <!-- Recommendations of what to train vs rest -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem;">
            <div class="fitsense-card" style="border-left: 4px solid var(--accent-emerald);">
              <h5 style="font-size: 0.95rem; font-weight: 700; color: var(--accent-emerald); margin-bottom: 0.4rem;">
                ✅ Nhóm cơ đã phục hồi hoàn toàn — NÊN TẬP HÔM NAY:
              </h5>
              <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                ${readyMuscles.length > 0 ? readyMuscles.map((m) => `<span class="muscle-pill" style="border-color: var(--accent-emerald);">${m.name}</span>`).join("") : "<span>Chưa có nhóm cơ nào đạt 100%</span>"}
              </div>
            </div>

            <div class="fitsense-card" style="border-left: 4px solid var(--accent-amber);">
              <h5 style="font-size: 0.95rem; font-weight: 700; color: var(--accent-amber); margin-bottom: 0.4rem;">
                ⚠️ Nhóm cơ đang mỏi — CẦN NGHỈ NGƠI:
              </h5>
              <div style="display: flex; gap: 0.4rem; flex-wrap: wrap;">
                ${fatiguedMuscles.length > 0 ? fatiguedMuscles.map((m) => `<span class="muscle-pill" style="border-color: var(--accent-amber);">${m.name}</span>`).join("") : "<span style='color: var(--text-muted);'>Tất cả các cơ đều đã sẵn sàng!</span>"}
              </div>
            </div>
          </div>
        </div>

        <!-- 5. Rest Day Notice or Post-Workout Survey Section -->
        ${!shouldShowSurvey ? `
          <div class="fitsense-card" style="margin-bottom: 2rem; border-left: 4px solid var(--accent-cyan); background: rgba(56, 189, 248, 0.04);" id="section-rest-day-card">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
              <div style="display: flex; align-items: center; gap: 1.15rem;">
                <span style="font-size: 2.2rem;">🛌</span>
                <div>
                  <h3 style="font-size: 1.15rem; font-weight: 800; margin: 0 0 0.35rem 0; color: var(--text-primary);">
                    Hôm nay là Ngày Nghỉ Phục Hồi Sinh Học (${todayName || "Hôm nay"})
                  </h3>
                  <p style="font-size: 0.88rem; color: var(--text-secondary); margin: 0; line-height: 1.55;">
                    💡 <b>Bạn muốn tập hôm nay?</b> Hãy vào tab <b>Kế hoạch</b> để đổi giáo án sang có bài tập.
                  </p>
                </div>
              </div>
              <button class="btn btn-primary btn-sm" id="btn-goto-planner" style="white-space: nowrap; border-radius: var(--radius-full); padding: 0.5rem 1.25rem;">
                📅 Mở Kế hoạch Tuần
              </button>
            </div>
          </div>
        ` : `
          <!-- 5. Post-Workout Survey & Adaptive AI Recommendations Section -->
          <div class="fitsense-card" style="margin-bottom: 2rem;" id="section-evaluation-survey">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.5rem;">
              <div>
                <h3 style="font-size: 1.25rem; font-weight: 800;">📝 Khảo sát Đánh giá Sau Buổi tập & Tối ưu Thích ứng Thể lực</h3>
                <p style="font-size: 0.85rem; color: var(--text-secondary);">
                  AI tự động đối chiếu tỉ lệ hoàn thành của <b>buổi tập được chọn</b>, kết hợp thang đo Borg RPE (1-10) để tự động điều chỉnh giáo án kế tiếp (Deload hoặc Tăng tiến).
                </p>
              </div>
              <span class="badge badge-intermediate">Adaptive AI Engine</span>
            </div>

            <form id="form-post-workout-evaluation" onsubmit="return false;">
              <!-- Scope Selector (Theo Buổi / Theo Bài) -->
              <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 1.25rem; padding: 0.65rem 0.9rem; background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border-color);">
                <div style="display: flex; align-items: center; gap: 0.65rem;">
                  <span style="font-weight: 700; font-size: 0.88rem; color: var(--text-primary);">🎯 Phạm vi khảo sát:</span>
                  <div style="display: inline-flex; background: var(--bg-surface); padding: 3px; border-radius: 8px; border: 1px solid var(--border-color);">
                    <button type="button" id="eval-scope-session-btn" class="btn btn-sm ${this.evalScope !== 'exercise' ? 'btn-primary' : 'btn-ghost'}" style="font-size: 0.78rem; padding: 0.25rem 0.75rem; border-radius: 6px; font-weight: 700;">
                      📋 Toàn bộ Buổi tập
                    </button>
                    <button type="button" id="eval-scope-exercise-btn" class="btn btn-sm ${this.evalScope === 'exercise' ? 'btn-primary' : 'btn-ghost'}" style="font-size: 0.78rem; padding: 0.25rem 0.75rem; border-radius: 6px; font-weight: 700;">
                      🎯 Từng Bài tập trong buổi
                    </button>
                  </div>
                </div>

                <div id="eval-exercise-select-wrapper" style="display: ${this.evalScope === 'exercise' ? 'flex' : 'none'}; align-items: center; gap: 0.5rem; flex: 1; min-width: 260px; justify-content: flex-end;">
                  <label style="font-size: 0.82rem; font-weight: 700; color: var(--accent-cyan); white-space: nowrap;">Chọn bài tập:</label>
                  <select class="form-control" id="eval-exercise-select" style="padding: 0.35rem 0.65rem; font-size: 0.85rem; max-width: 340px;">
                    ${selectedHistoryItem?.exercises?.map((ex, idx) => `
                      <option value="${ex.id}" data-comp="${ex.completion_rate || 100}" data-reps="${ex.reps}" data-target="${ex.target_reps || ex.reps}" data-muscle="${ex.primary_muscle || ''}" data-substitute="${ex.substitute || ''}" ${this.selectedExerciseId === ex.id || idx === 0 ? 'selected' : ''}>
                        Bài ${idx + 1}: ${ex.name.split('(')[0].trim()} (${ex.reps} reps · AI: ${ex.completion_rate || 100}%)
                      </option>
                    `).join("") || '<option value="none">Buổi này chưa có danh sách bài</option>'}
                  </select>
                </div>
              </div>

              <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.25rem; margin-bottom: 1.25rem;">
                <div class="form-group" style="margin-bottom: 0;">
                  <label class="form-label" style="font-weight: 700;">Chọn buổi tập cần đánh giá:</label>
                  <select class="form-control" id="eval-session-select">
                    ${hasHistory ? history.map((h, i) => {
                      const isSelected = initialSelectedSessionId ? (h.id === initialSelectedSessionId) : (i === 0);
                      const displayTitle = h.session_name || h.exercise_name;
                      return `
                      <option value="${h.id}" data-reps="${h.reps}" data-comp="${h.completion_rate !== undefined ? Math.round(h.completion_rate) : 0}" ${isSelected ? "selected" : ""}>
                        ${displayTitle} · 🕒 ${h.timestamp || h.actual_date} (${h.reps} reps · AI: ${h.completion_rate !== undefined ? Math.round(h.completion_rate) : 0}%)
                      </option>
                    `;}).join("") : `<option value="none" data-comp="0">Chưa ghi nhận dữ liệu buổi tập (0%)</option>`}
                  </select>
                </div>

                <!-- AI Estimated Completion Rate (Cố định khách quan cho 1 buổi tập hoặc 1 bài tập được chọn) -->
                <div class="form-group" style="margin-bottom: 0;">
                  <label class="form-label" style="display: flex; justify-content: space-between; align-items: center; font-weight: 700;">
                    <span id="eval-comp-label">🤖 ${this.evalScope === 'exercise' ? 'Tỉ lệ hoàn thành của bài tập này:' : 'Tỉ lệ hoàn thành của buổi tập này:'}</span>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                      <span class="badge ${hasHistory ? 'badge-intermediate' : 'badge-outline'}" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;" id="eval-comp-badge">${hasHistory ? '🔒 AI Verified' : 'Chưa có dữ liệu'}</span>
                      <strong id="eval-comp-rate-val" style="color: var(--accent-cyan); font-size: 1.15rem;">${initialCompRate}%</strong>
                    </div>
                  </label>
                  <!-- Thanh tiến trình cố định - đo đạc riêng cho 1 buổi tập hoặc bài tập -->
                  <div style="background: var(--bg-card); border-radius: 999px; height: 10px; overflow: hidden; margin-top: 0.6rem; border: 1px solid var(--border-color); position: relative;">
                    <div id="eval-comp-progress-fill" style="width: ${initialCompRate}%; height: 100%; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-emerald)); border-radius: 999px; transition: width 0.35s ease;"></div>
                  </div>
                  <input type="hidden" id="eval-comp-rate" value="${initialCompRate}" />
                  <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.4rem; display: flex; align-items: center; gap: 0.35rem;">
                    <span id="eval-comp-hint">${hasHistory ? "🔒 Đo đạc độc lập cho mục tiêu được chọn (không cộng dồn hay chia trung bình)." : "⚠️ Chưa ghi nhận dữ liệu buổi tập. Hãy hoàn thành buổi tập tại Phòng tập để AI đo đạc tỉ lệ thực tế."}</span>
                  </div>
                </div>
              </div>


            <!-- Borg RPE Slider (1 - 10) & Interactive Stepper -->
            <div class="form-group">
              <label class="form-label" style="display: flex; justify-content: space-between; align-items: center; font-weight: 700;">
                <span>Thang đo Mức độ Gắng sức RPE (Borg Scale 1 - 10):</span>
                <strong id="eval-rpe-display" style="color: var(--accent-amber); font-size: 1.15rem;">5/10</strong>
              </label>
              
              <input type="range" class="form-control" id="eval-rpe-slider" min="1" max="10" value="5" step="1" style="padding: 0; margin-bottom: 0.6rem;" />
              
              <!-- Interactive RPE Number Pills -->
              <div class="rpe-pills-row" id="rpe-pills-container">
                <button type="button" class="rpe-pill-btn" data-rpe="1">1</button>
                <button type="button" class="rpe-pill-btn" data-rpe="2">2</button>
                <button type="button" class="rpe-pill-btn" data-rpe="3">3</button>
                <button type="button" class="rpe-pill-btn" data-rpe="4">4</button>
                <button type="button" class="rpe-pill-btn active" data-rpe="5">5</button>
                <button type="button" class="rpe-pill-btn" data-rpe="6">6</button>
                <button type="button" class="rpe-pill-btn" data-rpe="7">7</button>
                <button type="button" class="rpe-pill-btn" data-rpe="8">8</button>
                <button type="button" class="rpe-pill-btn" data-rpe="9">9</button>
                <button type="button" class="rpe-pill-btn" data-rpe="10">10</button>
              </div>

              <div class="ai-reason-box" id="eval-rpe-desc-box" style="margin-top: 0.75rem; padding: 0.75rem 1rem; font-size: 0.88rem;">
                😤 <b>Mức RPE 5/10:</b> Vừa sức lý tưởng (Nhịp tập ổn định)
              </div>
            </div>

            <!-- Muscle Soreness Interactive Card Grid -->
            <div class="form-group">
              <label class="form-label" style="margin-bottom: 0.6rem; font-weight: 700;">
                Bộ phận cảm thấy mỏi hoặc căng cơ nhiều nhất:
              </label>
              
              <div class="soreness-grid" id="eval-soreness-grid">
                <label class="soreness-card" data-val="Cơ đùi trước (Quads)">
                  <input type="checkbox" name="soreness_item" value="Cơ đùi trước (Quads)" style="display: none;" />
                  <span class="soreness-icon">🦵</span>
                  <div class="soreness-info">
                    <div class="soreness-title">Cơ đùi trước (Quads)</div>
                    <div class="soreness-sub">Căng mỏi sau Squat/Lunge</div>
                  </div>
                  <span class="soreness-check-indicator"></span>
                </label>

                <label class="soreness-card" data-val="Cơ mông (Glutes)">
                  <input type="checkbox" name="soreness_item" value="Cơ mông (Glutes)" style="display: none;" />
                  <span class="soreness-icon">🍑</span>
                  <div class="soreness-info">
                    <div class="soreness-title">Cơ mông (Glutes)</div>
                    <div class="soreness-sub">Kích hoạt sâu nhóm cơ đẩy</div>
                  </div>
                  <span class="soreness-check-indicator"></span>
                </label>

                <label class="soreness-card" data-val="Cơ ngực (Chest)">
                  <input type="checkbox" name="soreness_item" value="Cơ ngực (Chest)" style="display: none;" />
                  <span class="soreness-icon">🏋️</span>
                  <div class="soreness-info">
                    <div class="soreness-title">Cơ ngực (Chest)</div>
                    <div class="soreness-sub">Căng cơ ngực sau Push-up</div>
                  </div>
                  <span class="soreness-check-indicator"></span>
                </label>

                <label class="soreness-card" data-val="Lưng & Cột sống">
                  <input type="checkbox" name="soreness_item" value="Lưng & Cột sống" style="display: none;" />
                  <span class="soreness-icon">🧘</span>
                  <div class="soreness-info">
                    <div class="soreness-title">Lưng & Cột sống</div>
                    <div class="soreness-sub">Mỏi lưng xô / cơ cốt lõi</div>
                  </div>
                  <span class="soreness-check-indicator"></span>
                </label>

                <label class="soreness-card" data-val="Khớp gối">
                  <input type="checkbox" name="soreness_item" value="Khớp gối" style="display: none;" />
                  <span class="soreness-icon">🦴</span>
                  <div class="soreness-info">
                    <div class="soreness-title">Khớp gối</div>
                    <div class="soreness-sub">Chú ý góc gập và tải trọng</div>
                  </div>
                  <span class="soreness-check-indicator"></span>
                </label>

                <label class="soreness-card" data-val="Cổ tay">
                  <input type="checkbox" name="soreness_item" value="Cổ tay" style="display: none;" />
                  <span class="soreness-icon">🖐️</span>
                  <div class="soreness-info">
                    <div class="soreness-title">Cổ tay</div>
                    <div class="soreness-sub">Áp lực khi chống đẩy</div>
                  </div>
                  <span class="soreness-check-indicator"></span>
                </label>

                <label class="soreness-card active recovery-card" data-val="Không đau mỏi gì đặc biệt" style="grid-column: 1 / -1;">
                  <input type="checkbox" name="soreness_item" value="Không đau mỏi gì đặc biệt" checked style="display: none;" />
                  <span class="soreness-icon">✨</span>
                  <div class="soreness-info">
                    <div class="soreness-title">Không đau mỏi gì đặc biệt</div>
                    <div class="soreness-sub">Thể trạng hoàn toàn khỏe mạnh, phục hồi tối ưu</div>
                  </div>
                  <span class="soreness-check-indicator"></span>
                </label>
              </div>
            </div>

            <!-- DOMS Severity & Satisfaction Rating (SCRUM-22 Yêu cầu 69) -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.25rem; margin-bottom: 1.25rem;">
              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label" style="font-weight: 700;">Mức độ mỏi cơ cục bộ (DOMS):</label>
                <select class="form-control" id="eval-doms-severity">
                  <option value="normal">🟢 Bình thường (Căng cơ nhẹ, phục hồi nhanh)</option>
                  <option value="moderate" selected>🟡 Vừa phải (Mỏi rõ rệt sau bài tập, cần nghỉ ngơi)</option>
                  <option value="intense">🔴 Đau nhức (Căng cứng khó chịu, cần giãn cơ & chườm)</option>
                </select>
              </div>

              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label" style="font-weight: 700;">Mức độ hài lòng về buổi tập:</label>
                <select class="form-control" id="eval-satisfaction">
                  <option value="very_satisfied">🌟 Rất hài lòng (Đúng kế hoạch, thể lực sung mãn)</option>
                  <option value="satisfied" selected>👍 Hài lòng (Hoàn thành tốt các hiệp chính)</option>
                  <option value="neutral">😐 Bình thường (Đạt yêu cầu tối thiểu)</option>
                  <option value="unsatisfied">⚡ Cần cải thiện (Đuối sức hoặc đứt quãng)</option>
                </select>
              </div>
            </div>

            <!-- User Note -->
            <div class="form-group">
              <label class="form-label" style="font-weight: 700;">Ghi chú cảm xúc & thể trạng (tùy chọn):</label>
              <textarea class="form-control" id="eval-user-note" rows="2" placeholder="Ví dụ: Hôm nay cơ đùi đáp ứng rất tốt, nhịp thở đều 💪..."></textarea>
            </div>

            <!-- Auto Apply & Submit Button -->
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-top: 1.25rem;">
              <label style="display: flex; align-items: center; gap: 0.55rem; font-size: 0.88rem; font-weight: 600; cursor: pointer; color: var(--text-secondary);">
                <input type="checkbox" id="eval-auto-apply" checked style="width: 18px; height: 18px; accent-color: var(--accent-cyan);" />
                <span>✨ Tự động áp dụng tối ưu hóa này vào Kế hoạch tuần tới</span>
              </label>

              <button class="btn btn-primary" id="btn-submit-evaluation" style="padding: 0.75rem 2.25rem; font-weight: 800; font-size: 0.95rem; border-radius: var(--radius-full);">
                💾 Gửi Khảo sát & Nhận Đề xuất AI
              </button>
            </div>
          </form>

          <!-- Adaptive AI Recommendation Result (Placed BELOW the survey; hidden until survey is completed) -->
          <div id="eval-recommendation-container" style="${hasEvaluated ? 'display: block;' : 'display: none;'} margin-top: 2rem; border-top: 1.5px dashed var(--border-color); padding-top: 1.75rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; flex-wrap: wrap; gap: 0.5rem;">
              <h4 style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary); display: flex; align-items: center; gap: 0.5rem; margin: 0;">
                💡 Khuyến nghị Tự động của Adaptive AI dành cho bạn
              </h4>
              <span class="badge ${recBadge}" id="badge-rec-status">${recStrategy}</span>
            </div>

            <div class="fitsense-card" id="box-adaptive-recommendation" style="background: var(--bg-surface); border: 1.5px solid var(--accent-cyan); padding: 1.35rem; border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);">
              <h5 id="rec-title" style="font-size: 1.1rem; font-weight: 800; color: var(--accent-cyan); margin-bottom: 0.4rem;">
                ${recTitle}
              </h5>
              <p id="rec-desc" style="font-size: 0.92rem; color: var(--text-secondary); line-height: 1.6; margin-bottom: 1rem;">
                ${recDesc}
              </p>

              <!-- Cool-down Stretches & Hydration Box -->
              <div id="rec-cooldown-box" style="margin-top: 1rem; padding: 1rem; background: var(--bg-card); border-radius: var(--radius-md); border-left: 3px solid var(--accent-emerald);">
                <div style="font-weight: 700; color: var(--accent-emerald); font-size: 0.92rem; margin-bottom: 0.4rem;">
                  🧘 Lời khuyên Phục hồi Sinh học (Cool-down & Bù nước)
                </div>
                <div id="rec-stretches-list" style="font-size: 0.86rem; color: var(--text-secondary); line-height: 1.6;">
                  ${initialEval?.recovery_items?.length ? initialEval.recovery_items.map(it => `<div>• <b>${it.target || it.muscle || "Vùng cơ"}:</b> ${it.stretch_name} (${it.guide}) - Nghỉ khuyến nghị: ${it.rest_hours}h</div>`).join("") : "<div>• <b>Toàn thân:</b> Giãn cơ thả lỏng nhẹ nhàng và hít thở sâu 3–5 phút.</div>"}
                </div>
                <div id="rec-hydration-text" style="font-size: 0.84rem; color: var(--accent-cyan); margin-top: 0.5rem; font-weight: 600;">
                  💧 ${initialEval?.hydration_advice || "Uống từng ngụm nhỏ 350ml–500ml nước lọc hoặc bù điện giải trong 30 phút sau khi tập."}
                </div>
              </div>

              <div style="padding-top: 0.75rem; border-top: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; font-size: 0.82rem; color: var(--text-muted); margin-top: 1rem;">
                <span style="color: var(--accent-emerald); font-weight: 600;">
                  ✨ Đã đồng bộ vào Kế hoạch tuần & Ma trận phục hồi sinh học
                </span>
                <span id="rec-timestamp">
                  🕒 ${evalTime}
                </span>
              </div>
            </div>
          </div>
        </div>
        `}

        <!-- 6. Detailed Workout History Table -->
        <div class="fitsense-card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <h3 style="font-size: 1.25rem; font-weight: 800;">📜 Nhật ký Rèn luyện Chi tiết</h3>
              <p style="font-size: 0.85rem; color: var(--text-secondary);">Ghi nhận toàn bộ các buổi tập với chỉ số RPE và calo tiêu hao</p>
            </div>
            <span class="badge badge-intermediate" style="font-size: 0.82rem; padding: 0.35rem 0.75rem;">
              Tổng: ${history.length} buổi ghi nhận
            </span>
          </div>

          <div class="table-wrapper">
            <table class="fitsense-table">
              <thead>
                <tr>
                  <th>Thời gian</th>
                  <th>Bài tập</th>
                  <th>Lịch tuần</th>
                  <th>Trạng thái</th>
                  <th>Số Reps</th>
                  <th>Thời lượng</th>
                  <th>Calo tiêu hao</th>
                  <th>RPE</th>
                  <th>Ghi chú</th>
                </tr>
              </thead>
              <tbody>
                ${history.length > 0 ? history.map((item) => `
                  <tr>
                    <td><b>${item.timestamp || item.actual_date}</b></td>
                    <td>
                      <div style="font-weight: 700; color: var(--accent-cyan); display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;">
                        <span>${item.session_name || item.exercise_name}</span>
                        ${item.exercises && item.exercises.length > 0 ? `<span class="badge badge-outline" style="font-size: 0.68rem; padding: 0.1rem 0.4rem;">${item.exercises.length} bài</span>` : ''}
                      </div>
                      ${item.exercises && item.exercises.length > 0 ? `
                        <div style="display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.35rem;">
                          ${item.exercises.map(ex => `
                            <span style="font-size: 0.72rem; background: var(--bg-card); border: 1px solid var(--border-color); padding: 0.15rem 0.45rem; border-radius: 4px; color: var(--text-secondary); display: inline-flex; align-items: center; gap: 0.3rem;">
                              <span>${ex.name.split('(')[0].trim()}</span>
                              <b style="color: var(--accent-emerald); font-weight: 700;">${ex.reps} reps</b>
                              ${ex.rpe ? `<span class="badge ${ex.rpe >= 8 ? 'badge-advanced' : ex.rpe >= 6 ? 'badge-intermediate' : 'badge-beginner'}" style="font-size: 0.65rem; padding: 0.05rem 0.25rem;">RPE ${ex.rpe}</span>` : ''}
                            </span>
                          `).join("")}
                        </div>
                      ` : ''}
                    </td>
                    <td><span class="badge badge-beginner">${item.day || "Tập tự do"}</span></td>
                    <td>${item.status === "abandoned" ? "Bỏ dở" : "Hoàn thành"}</td>
                    <td><strong>${item.reps}</strong> reps</td>
                    <td>${Math.floor((item.duration_sec || 0) / 60)}p ${(item.duration_sec || 0) % 60}s</td>
                    <td><span style="color: var(--accent-emerald); font-weight: 700;">${item.calories || 0} kcal</span></td>
                    <td style="text-align: center;">
                      ${item.rpe === null || item.rpe === undefined ? `<span style="color: var(--text-muted); font-size: 1.1rem; font-weight: 500;">—</span>` : `<span class="badge ${item.rpe >= 8 ? 'badge-advanced' : item.rpe >= 6 ? 'badge-intermediate' : 'badge-beginner'}">
                        RPE ${item.rpe}/10
                      </span>`}
                    </td>
                    <td style="color: var(--text-secondary); font-size: 0.82rem;">${item.notes || "—"}</td>
                  </tr>
                `).join("") : `
                  <tr>
                    <td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                      Chưa có dữ liệu buổi tập nào. Hãy vào phòng tập Live AI để ghi nhận buổi đầu tiên nhé!
                    </td>
                  </tr>
                `}
              </tbody>
            </table>
          </div>
        </div>
      `;

      this.bindEvaluationEvents(container);
    } catch (err) {
      console.error("Progress render error:", err);
      if (container) {
        container.innerHTML = `<div class="fitsense-card" style="color: var(--accent-crimson);">Lỗi tải bảng đánh giá: ${err.message}</div>`;
      }
    }
  },

  bindEvaluationEvents(container) {
    if (!container) container = document.getElementById("view-progress");
    if (!container) return;

    container.querySelector("#btn-goto-planner")?.addEventListener("click", () => {
      if (window.navigateTo) window.navigateTo("planner");
    });

    const rpeSlider = document.getElementById("eval-rpe-slider");
    if (!rpeSlider) return;
    const rpeDisplay = document.getElementById("eval-rpe-display");
    const rpeDescBox = document.getElementById("eval-rpe-desc-box");
    const compSlider = document.getElementById("eval-comp-rate");
    const compDisplay = document.getElementById("eval-comp-rate-val");

    const rpeDescriptions = this.evalMeta?.rpe_descriptions || {
      1: "😌 Rất nhẹ (Gần như không thấy mệt)",
      2: "🙂 Nhẹ nhàng, hít thở rất thoải mái",
      3: "😊 Vừa phải (Bắt đầu làm nóng cơ thể)",
      4: "😉 Hơi thử thách nhẹ, còn rất nhiều sức",
      5: "😤 Vừa sức lý tưởng (Nhịp tập ổn định)",
      6: "😅 Khá mệt nhưng vẫn kiểm soát kỹ thuật tốt",
      7: "😓 Nặng (Cơ bắp bắt đầu mỏi rõ rệt)",
      8: "😫 Rất mệt (Cần tập trung cao độ, thở dốc)",
      9: "🥵 Cực kỳ nặng (Gần ngưỡng chịu đựng tối đa)",
      10: "🤯 Kiệt sức hoàn toàn (Không thể làm thêm 1 rep)",
    };

    const updateAdaptivePreview = () => {
      const recContainer = document.getElementById("eval-recommendation-container");
      if (!recContainer || recContainer.style.display === "none") return;

      const rpe = parseInt(rpeSlider?.value || 5, 10);
      const comp = parseInt(compSlider?.value || 90, 10);

      const titleEl = document.getElementById("rec-title");
      const descEl = document.getElementById("rec-desc");
      const badgeEl = document.getElementById("badge-rec-status");

      if (comp < 70 || rpe >= 9) {
        if (badgeEl) { badgeEl.className = "badge badge-advanced"; badgeEl.textContent = "Deload -15%"; }
        if (titleEl) { titleEl.textContent = "🩹 Khuyến nghị Giảm tải (Deload Strategy -15%) 📉"; titleEl.style.color = "var(--accent-crimson)"; }
        if (descEl) { descEl.textContent = `AI ghi nhận mức hoàn thành ${comp}% với độ gắng sức ${rpe}/10 😮‍💨. Hành động: Tự động giảm 15% số reps hoặc tăng thời gian nghỉ giữa hiệp thêm 15 giây cho buổi kế tiếp để bảo vệ khớp!`; }
      } else if ((comp >= 70 && comp < 85) || (rpe === 8 && comp < 90)) {
        if (badgeEl) { badgeEl.className = "badge badge-intermediate"; badgeEl.textContent = "Minor Deload -5%"; }
        if (titleEl) { titleEl.textContent = "🛡️ Khuyến nghị Giảm nhẹ Củng cố Thể lực (-5%) 📉"; titleEl.style.color = "var(--accent-amber)"; }
        if (descEl) { descEl.textContent = `Khối lượng tập vừa qua hơi vượt ngưỡng nhẹ (${comp}%, RPE ${rpe}/10) 😐. Hành động: Tự động tinh chỉnh giảm nhẹ -5% số reps và chuẩn hóa form động tác!`; }
      } else if (comp >= 90 && rpe <= 6) {
        if (badgeEl) { badgeEl.className = "badge badge-emerald"; badgeEl.textContent = "Overload +10%"; }
        if (titleEl) { titleEl.textContent = "🚀 Khuyến nghị Tăng tiến Tải trọng (Progressive Overload +10%) 🔥"; titleEl.style.color = "var(--accent-emerald)"; }
        if (descEl) { descEl.textContent = `Xuất sắc! Bạn đạt ${comp}% giáo án mà vẫn giữ nhịp độ rất tốt (RPE ${rpe}/10) 💪. Hành động: Buổi sau sẽ tự động tăng 2 reps/set hoặc gợi ý biến thể nâng cao để bứt phá giới hạn!`; }
      } else {
        if (badgeEl) { badgeEl.className = "badge badge-intermediate"; badgeEl.textContent = "Optimal Maintenance"; }
        if (titleEl) { titleEl.textContent = "⚖️ Khuyến nghị Giữ nguyên Nhịp độ (Optimal Maintenance) 😊"; titleEl.style.color = "var(--accent-cyan)"; }
        if (descEl) { descEl.textContent = `Hiệu suất cân bằng tuyệt vời (${comp}% giáo án, RPE ${rpe}/10) ✨. Hành động: Duy trì khối lượng và nhịp tập hiện tại để xây dựng nền tảng bền vững cho chu kỳ tuần tới! 🦫`; }
      }
    };

    // Interactive RPE Stepper Pills
    const rpePills = container.querySelectorAll(".rpe-pill-btn");
    const updateRpePillActive = (val) => {
      rpePills.forEach((p) => {
        p.classList.toggle("active", parseInt(p.getAttribute("data-rpe"), 10) === val);
      });
    };

    rpePills.forEach((btn) => {
      btn.addEventListener("click", () => {
        const val = parseInt(btn.getAttribute("data-rpe"), 10);
        if (rpeSlider) rpeSlider.value = val;
        if (rpeDisplay) rpeDisplay.textContent = `${val}/10`;
        if (rpeDescBox) rpeDescBox.innerHTML = `<b>Mức RPE ${val}/10:</b> ${rpeDescriptions[val] || ""}`;
        updateRpePillActive(val);
        updateAdaptivePreview();
      });
    });

    rpeSlider?.addEventListener("input", (e) => {
      const val = parseInt(e.target.value, 10);
      if (rpeDisplay) rpeDisplay.textContent = `${val}/10`;
      if (rpeDescBox) rpeDescBox.innerHTML = `<b>Mức RPE ${val}/10:</b> ${rpeDescriptions[val] || ""}`;
      updateRpePillActive(val);
      updateAdaptivePreview();
    });

    // Soreness Cards Interactive Selection Logic
    const sorenessCards = container.querySelectorAll(".soreness-card");
    sorenessCards.forEach((card) => {
      card.addEventListener("click", (e) => {
        e.preventDefault();
        const checkbox = card.querySelector("input[type='checkbox']");
        const val = card.getAttribute("data-val");

        if (val === "Không đau mỏi gì đặc biệt") {
          // Deselect all specific muscle cards
          sorenessCards.forEach((c) => {
            if (c !== card) {
              c.classList.remove("active");
              const chk = c.querySelector("input[type='checkbox']");
              if (chk) chk.checked = false;
            }
          });
          card.classList.add("active");
          if (checkbox) checkbox.checked = true;
        } else {
          // Deselect "Không đau mỏi gì đặc biệt"
          const noneCard = container.querySelector(".soreness-card[data-val='Không đau mỏi gì đặc biệt']");
          if (noneCard) {
            noneCard.classList.remove("active");
            const noneChk = noneCard.querySelector("input[type='checkbox']");
            if (noneChk) noneChk.checked = false;
          }

          // Toggle current card
          const isNowActive = !card.classList.contains("active");
          card.classList.toggle("active", isNowActive);
          if (checkbox) checkbox.checked = isNowActive;

          // If no cards are selected, re-activate "Không đau mỏi gì đặc biệt"
          const anyActive = Array.from(sorenessCards).some(
            (c) => c.getAttribute("data-val") !== "Không đau mỏi gì đặc biệt" && c.classList.contains("active")
          );
          if (!anyActive && noneCard) {
            noneCard.classList.add("active");
            const noneChk = noneCard.querySelector("input[type='checkbox']");
            if (noneChk) noneChk.checked = true;
          }
        }
      });
    });

    const sessionSelect = document.getElementById("eval-session-select");
    const scopeSessionBtn = document.getElementById("eval-scope-session-btn");
    const scopeExerciseBtn = document.getElementById("eval-scope-exercise-btn");
    const exSelectWrapper = document.getElementById("eval-exercise-select-wrapper");
    const exSelect = document.getElementById("eval-exercise-select");

    const refreshExerciseSelectOptions = () => {
      const selectedId = sessionSelect?.value;
      const selectedSession = history.find((h) => h.id === selectedId);
      if (exSelect && selectedSession?.exercises && selectedSession.exercises.length > 0) {
        exSelect.innerHTML = selectedSession.exercises.map((ex, idx) => `
          <option value="${ex.id}" data-comp="${ex.completion_rate || 100}" data-reps="${ex.reps}" data-target="${ex.target_reps || ex.reps}" data-muscle="${ex.primary_muscle || ''}" data-substitute="${ex.substitute || ''}" ${this.selectedExerciseId === ex.id || idx === 0 ? 'selected' : ''}>
            Bài ${idx + 1}: ${ex.name.split('(')[0].trim()} (${ex.reps} reps · AI: ${ex.completion_rate || 100}%)
          </option>
        `).join("");
      }
    };

    const updateEvaluationViewForCurrentScope = () => {
      const selectedId = sessionSelect?.value;
      const selectedSession = history.find((h) => h.id === selectedId);
      const isExerciseScope = this.evalScope === "exercise";
      const currentExId = isExerciseScope ? exSelect?.value : null;

      // Update completion rate progress
      let compNum = 0;
      let labelText = "🤖 Tỉ lệ hoàn thành của buổi tập này:";
      if (isExerciseScope) {
        const opt = exSelect?.selectedOptions?.[0];
        const val = opt?.getAttribute("data-comp");
        compNum = val !== null && val !== undefined ? Math.round(parseFloat(val)) : 100;
        labelText = "🤖 Tỉ lệ hoàn thành của bài tập này:";
      } else {
        const opt = sessionSelect?.selectedOptions?.[0];
        const val = opt?.getAttribute("data-comp");
        compNum = val !== null && val !== undefined ? Math.round(parseFloat(val)) : 100;
        labelText = "🤖 Tỉ lệ hoàn thành của buổi tập này:";
      }

      const compLabel = document.getElementById("eval-comp-label");
      if (compLabel) compLabel.textContent = labelText;
      if (compSlider) compSlider.value = compNum;
      if (compDisplay) compDisplay.textContent = `${compNum}%`;
      const fillBar = document.getElementById("eval-comp-progress-fill");
      if (fillBar) fillBar.style.width = `${compNum}%`;

      // Determine target evaluation key
      const targetEvalKey = isExerciseScope && currentExId ? `${selectedId}_${currentExId}` : selectedId;
      const targetEval = this.evalsBySession ? this.evalsBySession[targetEvalKey] : null;
      const recContainer = document.getElementById("eval-recommendation-container");

      if (targetEval) {
        if (recContainer) recContainer.style.display = "block";
        const badgeEl = document.getElementById("badge-rec-status");
        const titleEl = document.getElementById("rec-title");
        const descEl = document.getElementById("rec-desc");
        const stretchesList = document.getElementById("rec-stretches-list");
        const hydrationText = document.getElementById("rec-hydration-text");
        const timeEl = document.getElementById("rec-timestamp");

        const strat = targetEval.recommendation?.strategy || targetEval.strategy || "maintenance";
        const badgeClass = targetEval.recommendation?.badge || (strat === "deload" ? "badge-advanced" : (strat === "overload" ? "badge-emerald" : (strat === "minor_deload" ? "badge-warning" : "badge-intermediate")));
        const stratLabel = strat === "deload" ? "Deload -15%" : (strat === "overload" ? "Overload +10%" : (strat === "minor_deload" ? "Minor Deload -5%" : "Optimal Maintenance"));

        if (badgeEl) {
          badgeEl.className = `badge ${badgeClass}`;
          badgeEl.textContent = stratLabel;
        }
        if (titleEl) {
          titleEl.textContent = targetEval.recommendation?.title || "Khuyến nghị Adaptive AI";
          titleEl.style.color = strat === "deload" ? "var(--accent-crimson)" : (strat === "overload" ? "var(--accent-emerald)" : (strat === "minor_deload" ? "var(--accent-amber)" : "var(--accent-cyan)"));
        }
        if (descEl) {
          descEl.textContent = targetEval.recommendation?.action || "Duy trì khối lượng và nhịp tập hiện tại!";
        }
        if (stretchesList) {
          const items = targetEval.recovery_items || [];
          stretchesList.innerHTML = items.length > 0
            ? items.map(it => `<div>• <b>${it.target || it.muscle || "Vùng cơ"}:</b> ${it.stretch_name} (${it.guide}) - Nghỉ khuyến nghị: ${it.rest_hours}h</div>`).join("")
            : "<div>• <b>Toàn thân:</b> Giãn cơ thả lỏng nhẹ nhàng và hít thở sâu 3–5 phút.</div>";
        }
        if (hydrationText) {
          hydrationText.textContent = `💧 ${targetEval.hydration_advice || "Uống từng ngụm nhỏ 350ml–500ml nước lọc hoặc bù điện giải trong 30 phút sau khi tập."}`;
        }
        if (timeEl) {
          timeEl.textContent = `🕒 ${targetEval.created_at || targetEval.timestamp || "Đã ghi nhận"}`;
        }

        if (rpeSlider && targetEval.rpe) {
          rpeSlider.value = targetEval.rpe;
          if (rpeDisplay) rpeDisplay.textContent = `${targetEval.rpe}/10`;
          if (rpeDescBox) rpeDescBox.innerHTML = `<b>Mức RPE ${targetEval.rpe}/10:</b> ${rpeDescriptions[targetEval.rpe] || ""}`;
          updateRpePillActive(targetEval.rpe);
        }
        if (targetEval.doms_severity) {
          const domsSelect = document.getElementById("eval-doms-severity");
          if (domsSelect) domsSelect.value = targetEval.doms_severity;
        }
        if (targetEval.satisfaction) {
          const satSelect = document.getElementById("eval-satisfaction");
          if (satSelect) satSelect.value = targetEval.satisfaction;
        }
        if (targetEval.note !== undefined) {
          const noteArea = document.getElementById("eval-user-note");
          if (noteArea) noteArea.value = targetEval.note || "";
        }
        const targetSoreness = targetEval.soreness || targetEval.muscle_soreness || [];
        sorenessCards.forEach(card => {
          const val = card.getAttribute("data-val");
          const shouldBeActive = targetSoreness.includes(val);
          card.classList.toggle("active", shouldBeActive);
          const chk = card.querySelector("input[type='checkbox']");
          if (chk) chk.checked = shouldBeActive;
        });
      } else {
        // Chưa đánh giá: ẩn khuyến nghị
        if (recContainer) recContainer.style.display = "none";

        let defaultRpe = 5;
        let defaultMuscle = "Không đau mỏi gì đặc biệt";
        if (isExerciseScope && selectedSession?.exercises) {
          const exObj = selectedSession.exercises.find((e) => e.id === currentExId);
          if (exObj) {
            defaultRpe = exObj.rpe || 5;
            defaultMuscle = exObj.primary_muscle || defaultMuscle;
          }
        }
        if (rpeSlider) {
          rpeSlider.value = defaultRpe;
          if (rpeDisplay) rpeDisplay.textContent = `${defaultRpe}/10`;
          if (rpeDescBox) rpeDescBox.innerHTML = `<b>Mức RPE ${defaultRpe}/10:</b> ${rpeDescriptions[defaultRpe] || ""}`;
          updateRpePillActive(defaultRpe);
        }
        const domsSelect = document.getElementById("eval-doms-severity");
        if (domsSelect) domsSelect.value = "moderate";
        const satSelect = document.getElementById("eval-satisfaction");
        if (satSelect) satSelect.value = "satisfied";
        const noteArea = document.getElementById("eval-user-note");
        if (noteArea) noteArea.value = "";

        sorenessCards.forEach(card => {
          const val = card.getAttribute("data-val");
          const isMatch = val === defaultMuscle || (defaultMuscle === "Không đau mỏi gì đặc biệt" && val === "Không đau mỏi gì đặc biệt");
          card.classList.toggle("active", isMatch);
          const chk = card.querySelector("input[type='checkbox']");
          if (chk) chk.checked = isMatch;
        });
      }
    };

    scopeSessionBtn?.addEventListener("click", () => {
      this.evalScope = "session";
      scopeSessionBtn.className = "btn btn-sm btn-primary";
      scopeExerciseBtn.className = "btn btn-sm btn-ghost";
      if (exSelectWrapper) exSelectWrapper.style.display = "none";
      updateEvaluationViewForCurrentScope();
    });

    scopeExerciseBtn?.addEventListener("click", () => {
      this.evalScope = "exercise";
      scopeExerciseBtn.className = "btn btn-sm btn-primary";
      scopeSessionBtn.className = "btn btn-sm btn-ghost";
      if (exSelectWrapper) exSelectWrapper.style.display = "flex";
      refreshExerciseSelectOptions();
      updateEvaluationViewForCurrentScope();
    });

    exSelect?.addEventListener("change", () => {
      this.selectedExerciseId = exSelect.value;
      updateEvaluationViewForCurrentScope();
    });

    sessionSelect?.addEventListener("change", () => {
      const selectedId = sessionSelect.value;
      this.selectedSessionId = selectedId;
      if (this.evalScope === "exercise") {
        refreshExerciseSelectOptions();
      }
      updateEvaluationViewForCurrentScope();
    });

    document.getElementById("btn-submit-evaluation")?.addEventListener("click", async () => {
      const sessionId = sessionSelect?.value;
      const sessionLabel = sessionSelect?.options[sessionSelect.selectedIndex]?.text || "Buổi tập vừa thực hiện";
      const isExerciseScope = this.evalScope === "exercise";
      const exerciseId = isExerciseScope ? exSelect?.value : null;
      const exerciseOpt = exSelect?.selectedOptions?.[0];
      const exerciseName = isExerciseScope ? (exerciseOpt?.text || "") : null;

      const comp = parseInt(compSlider?.value || 90, 10);
      const rpe = parseInt(rpeSlider?.value || 5, 10);
      const domsSeverity = document.getElementById("eval-doms-severity")?.value || "moderate";
      const satisfaction = document.getElementById("eval-satisfaction")?.value || "satisfied";
      const note = document.getElementById("eval-user-note")?.value || "";
      const autoApply = document.getElementById("eval-auto-apply")?.checked ?? true;

      const checkedSoreness = [];
      document.querySelectorAll("input[name='soreness_item']:checked").forEach((chk) => {
        checkedSoreness.push(chk.value);
      });

      try {
        const res = await API.progress.submitEvaluation({
          session_id: sessionId,
          session_label: sessionLabel,
          scope: isExerciseScope ? "exercise" : "session",
          exercise_id: exerciseId,
          exercise_name: exerciseName,
          completion_rate: comp,
          rpe,
          soreness: checkedSoreness,
          doms_severity: domsSeverity,
          satisfaction: satisfaction,
          note,
          auto_apply: autoApply,
        });

        this.latestEvaluation = res.evaluation;
        if (!this.evalsBySession) this.evalsBySession = {};
        const evalKey = isExerciseScope && exerciseId ? `${sessionId}_${exerciseId}` : sessionId;
        this.evalsBySession[evalKey] = res.evaluation;
        this.selectedSessionId = sessionId;
        if (isExerciseScope) this.selectedExerciseId = exerciseId;
        Toast.success(res.message || "🎉 Đã ghi nhận đánh giá thành công!");
        import("../components/capybara.js").then((m) => m.Capybara.refresh());
        await this.render();

        const recContainer = document.getElementById("eval-recommendation-container");
        if (recContainer) {
          recContainer.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
      } catch (err) {
        Toast.error("Lỗi gửi đánh giá: " + err.message);
      }
    });
  },
};

