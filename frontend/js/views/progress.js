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
      const [heatmapData, historyData, statsData, evalMetaData, evalsData] = await Promise.all([
        API.progress.heatmap(),
        API.progress.history(),
        API.progress.stats(),
        API.progress.evaluationMeta(),
        API.progress.evaluations(),
      ]);
      this.lastRenderTime = Date.now();

      this.evalMeta = evalMetaData;
      const muscles = heatmapData.muscles || [];
      const history = historyData.history || [];
      const latestHistoryComp = history.length > 0 && history[0].completion_rate !== undefined
        ? Math.round(history[0].completion_rate)
        : 100;
      const evals = evalsData?.evaluations || [];
      const latestEval = this.latestEvaluation || (evals.length > 0 ? evals[0] : null);
      const hasEvaluated = Boolean(latestEval);

      let recBadge = "badge-intermediate";
      let recStrategy = "Optimal Maintenance";
      let recTitle = "Khuyến nghị Giữ nguyên Nhịp độ (Optimal Maintenance) 😊";
      let recDesc = "Duy trì khối lượng và nhịp tập hiện tại để xây dựng nền tảng bền vững cho chu kỳ tuần tới!";
      let evalTime = "Vừa cập nhật";

      if (latestEval && latestEval.recommendation) {
        recBadge = latestEval.recommendation.badge || "badge-intermediate";
        recTitle = latestEval.recommendation.title || recTitle;
        recDesc = latestEval.recommendation.action || recDesc;
        recStrategy = latestEval.recommendation.strategy === "deload"
          ? "Deload -15%"
          : (latestEval.recommendation.strategy === "overload" ? "Overload +10%" : "Optimal Maintenance");
        evalTime = latestEval.created_at || "Vừa cập nhật";
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

        <!-- 5. Post-Workout Survey & Adaptive AI Recommendations Section -->
        <div class="fitsense-card" style="margin-bottom: 2rem;" id="section-evaluation-survey">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem; flex-wrap: wrap; gap: 0.5rem;">
            <div>
              <h3 style="font-size: 1.25rem; font-weight: 800;">📝 Khảo sát Đánh giá Sau Buổi tập & Tối ưu Thích ứng Thể lực</h3>
              <p style="font-size: 0.85rem; color: var(--text-secondary);">
                AI tự động đối chiếu tỉ lệ hoàn thành, kết hợp thang đo Borg RPE (1-10) để tự động điều chỉnh giáo án kế tiếp (Deload hoặc Tăng tiến).
              </p>
            </div>
            <span class="badge badge-intermediate">Adaptive AI Engine</span>
          </div>

          <form id="form-post-workout-evaluation" onsubmit="return false;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.25rem; margin-bottom: 1.25rem;">
              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label" style="font-weight: 700;">Chọn buổi tập cần đánh giá:</label>
                <select class="form-control" id="eval-session-select">
                  ${history.length > 0 ? history.map((h, i) => `
                    <option value="${h.id}" data-reps="${h.reps}" data-comp="${h.completion_rate !== undefined ? Math.round(h.completion_rate) : 100}">
                      ${h.exercise_name} · 🕒 ${h.timestamp || h.actual_date} (${h.reps} reps · AI: ${h.completion_rate !== undefined ? Math.round(h.completion_rate) : 100}%)
                    </option>
                  `).join("") : `<option value="current" data-comp="100">Buổi tập vừa thực hiện (Mặc định)</option>`}
                </select>
              </div>

              <!-- AI Estimated Completion Rate (Cố định khách quan theo dữ liệu AI) -->
              <div class="form-group" style="margin-bottom: 0;">
                <label class="form-label" style="display: flex; justify-content: space-between; align-items: center; font-weight: 700;">
                  <span>🤖 Tỉ lệ hoàn thành do AI đối chiếu:</span>
                  <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span class="badge badge-intermediate" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;">🔒 AI Verified</span>
                    <strong id="eval-comp-rate-val" style="color: var(--accent-cyan); font-size: 1.15rem;">${latestHistoryComp}%</strong>
                  </div>
                </label>
                <!-- Thanh tiến trình cố định - không cho phép kéo chỉnh sửa thủ công -->
                <div style="background: var(--bg-card); border-radius: 999px; height: 10px; overflow: hidden; margin-top: 0.6rem; border: 1px solid var(--border-color); position: relative;">
                  <div id="eval-comp-progress-fill" style="width: ${latestHistoryComp}%; height: 100%; background: linear-gradient(90deg, var(--accent-cyan), var(--accent-emerald)); border-radius: 999px; transition: width 0.35s ease;"></div>
                </div>
                <input type="hidden" id="eval-comp-rate" value="${latestHistoryComp}" />
                <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.4rem; display: flex; align-items: center; gap: 0.35rem;">
                  <span>🔒 Số liệu được AI đo đạc khách quan từ buổi tập và tự động cố định.</span>
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

              <div style="padding-top: 0.75rem; border-top: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; font-size: 0.82rem; color: var(--text-muted);">
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
                    <td><span style="color: var(--accent-cyan); font-weight: 700;">${item.exercise_name}</span></td>
                    <td><span class="badge badge-beginner">${item.day || "Tập tự do"}</span></td>
                    <td><strong>${item.reps}</strong> reps</td>
                    <td>${Math.floor((item.duration_sec || 0) / 60)}p ${(item.duration_sec || 0) % 60}s</td>
                    <td><span style="color: var(--accent-emerald); font-weight: 700;">${item.calories || 0} kcal</span></td>
                    <td>
                      <span class="badge ${item.rpe >= 8 ? 'badge-advanced' : item.rpe >= 6 ? 'badge-intermediate' : 'badge-beginner'}">
                        RPE ${item.rpe || 7}/10
                      </span>
                    </td>
                    <td style="color: var(--text-secondary); font-size: 0.82rem;">${item.notes || "—"}</td>
                  </tr>
                `).join("") : `
                  <tr>
                    <td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);">
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
    const rpeSlider = document.getElementById("eval-rpe-slider");
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
        if (descEl) { descEl.textContent = `AI ghi nhận mức hoàn thành ${comp}% với độ gắng sức ${rpe}/10 😮‍💨. Hành động: Tự động giảm 1–2 sets hoặc tăng thời gian nghỉ giữa hiệp thêm 15 giây cho buổi kế tiếp để bảo vệ khớp!`; }
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
    sessionSelect?.addEventListener("change", () => {
      const opt = sessionSelect.selectedOptions?.[0];
      const compVal = opt?.getAttribute("data-comp");
      if (compVal !== null && compVal !== undefined) {
        const compNum = Math.round(parseFloat(compVal));
        if (compSlider) compSlider.value = compNum;
        if (compDisplay) compDisplay.textContent = `${compNum}%`;
        const fillBar = document.getElementById("eval-comp-progress-fill");
        if (fillBar) fillBar.style.width = `${compNum}%`;
        updateAdaptivePreview();
      }
    });

    document.getElementById("btn-submit-evaluation")?.addEventListener("click", async () => {
      const sessionId = sessionSelect?.value;
      const sessionLabel = sessionSelect?.options[sessionSelect.selectedIndex]?.text || "Buổi tập vừa thực hiện";
      const comp = parseInt(compSlider?.value || 90, 10);
      const rpe = parseInt(rpeSlider?.value || 5, 10);
      const note = document.getElementById("eval-user-note")?.value || "";
      const autoApply = document.getElementById("eval-auto-apply")?.checked || true;

      const checkedSoreness = [];
      document.querySelectorAll("input[name='soreness_item']:checked").forEach((chk) => {
        checkedSoreness.push(chk.value);
      });

      try {
        const res = await API.progress.submitEvaluation({
          session_id: sessionId,
          session_label: sessionLabel,
          completion_rate: comp,
          rpe,
          soreness: checkedSoreness,
          note,
          auto_apply: autoApply,
        });

        this.latestEvaluation = res.evaluation;
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
