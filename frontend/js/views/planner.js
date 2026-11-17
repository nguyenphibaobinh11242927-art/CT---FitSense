/**
 * FitSense Weekly Planner View
 */

import { API } from "../api.js";
import { Toast } from "../components/toast.js";
import { showConfirmModal } from "../components/modal.js";

export const PlannerView = {
  scheduleData: null,
  activeDayIndex: 0,

  async render() {
    const container = document.getElementById("view-planner");
    if (!container) return;

    try {
      this.scheduleData = await API.planner.getWeek();
      this.activeDayIndex = this.scheduleData.today_weekday_index ?? 0;
      this.renderContent();
    } catch (err) {
      console.error("Planner load error:", err);
      container.innerHTML = `<div class="fitsense-card" style="color: var(--accent-crimson);">Lỗi tải lịch tập: ${err.message}</div>`;
    }
  },

  renderContent() {
    const container = document.getElementById("view-planner");
    if (!container || !this.scheduleData) return;

    const schedule = this.scheduleData.schedule || [];
    const todayName = this.scheduleData.today_name || "Thứ 2";
    const warnings = this.scheduleData.warnings || {};
    const activeDay = schedule[this.activeDayIndex] || schedule[0];
    const dayWarnings = warnings[activeDay.day] || [];
    const isTodayActive = activeDay.day.toLowerCase() === todayName.toLowerCase();

    container.innerHTML = `
      <div class="view-header">
        <div class="view-title-group">
          <h2>📅 Kế hoạch Tuần & Trợ lý AI</h2>
          <p>Lịch phân bổ nhóm cơ tối ưu phục hồi sinh học và rèn luyện Calisthenics chuẩn khoa học.</p>
        </div>
        <div class="planner-toolbar">
          <button class="btn btn-outline" id="btn-toggle-upload-plan" title="Nhập giáo án cá nhân từ file JSON hoặc CSV">
            📤 Tải lên file giáo án
          </button>
          <button class="btn btn-outline" id="btn-download-sample-plan" title="Tải về file JSON mẫu để tham khảo cấu trúc giáo án">
            ⬇️ Tải JSON mẫu
          </button>
          <button class="btn btn-primary" id="btn-generate-ai" title="AI tự động phân tích và tạo lịch tập tối ưu">
            🤖 Tạo lịch bằng AI
          </button>
          <button class="btn btn-outline" id="btn-reset-planner" title="Khôi phục về giáo án chuẩn ban đầu">
            🔄 Đặt lại mẫu
          </button>
        </div>
      </div>

      <!-- Upload Custom Plan Collapsible Box -->
      <div class="fitsense-card" id="box-upload-plan" style="display: none; margin-bottom: 1.5rem; border-color: var(--accent-cyan); background: rgba(56, 189, 248, 0.04);">
        <h4 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
          📤 Nạp Kế hoạch Cá nhân từ File (.JSON hoặc .CSV)
        </h4>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">
          Hệ thống hỗ trợ nạp giáo án tự thiết kế từ file JSON hoặc CSV. Bạn cũng có thể tải file JSON mẫu về để chỉnh sửa rồi nạp lại.
        </p>
        <div style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap;">
          <input type="file" id="file-plan-upload-input" accept=".json,.csv" class="form-control" style="width: auto; max-width: 320px;" />
          <button class="btn btn-primary btn-sm" id="btn-apply-uploaded-plan">
            ✅ Nạp kế hoạch từ file này
          </button>
        </div>
      </div>

      <!-- 7-Day Interactive Tabs -->
      <div class="day-tabs">
        ${schedule.map((d, idx) => {
          const isToday = d.day.toLowerCase() === todayName.toLowerCase();
          const isActive = idx === this.activeDayIndex;
          return `
            <div class="day-tab ${isActive ? 'active' : ''} ${isToday ? 'today' : ''} ${d.is_rest ? 'is-rest' : ''}" data-idx="${idx}">
              <span class="day-name">${d.day}</span>
              <span class="day-status">${d.is_rest ? 'Nghỉ ngơi' : `${d.exercises?.length || 0} bài tập`}</span>
            </div>
          `;
        }).join("")}
      </div>

      <!-- Active Day Detail Card -->
      <div class="fitsense-card day-content-card">
        <div class="day-content-header">
          <div>
            <span style="font-size: 0.8rem; font-weight: 700; color: var(--accent-cyan); text-transform: uppercase;">
              Buổi tập ${activeDay.day} ${isTodayActive ? '(Hôm nay)' : ''}
            </span>
            <div class="day-focus-badge">
              ${activeDay.focus}
            </div>
          </div>
          ${activeDay.is_rest 
            ? `<span class="badge badge-beginner" style="font-size: 0.9rem; padding: 0.4rem 0.9rem;">🛌 Nghỉ ngơi hồi phục (Rest Day)</span>`
            : (isTodayActive 
                ? `<button class="btn btn-emerald btn-sm" id="btn-start-day-workout">🚀 Bắt đầu tập buổi hôm nay (${activeDay.day})</button>`
                : `<button class="btn btn-primary btn-sm" id="btn-start-day-workout" style="background: linear-gradient(135deg, #0284c7, #0ea5e9); border: none;" title="Tập giáo án ${activeDay.day} thay cho hôm nay, AI sẽ tự động phân bổ lại các ngày còn lại">🔀 Tập buổi ${activeDay.day} thay cho hôm nay</button>`
              )
          }
        </div>

        <div class="ai-reason-box">
          💡 <b>Cơ sở khoa học / Gợi ý AI:</b> ${activeDay.ai_reason}
        </div>

        ${dayWarnings.length > 0 ? `
          <div class="recovery-warning-box">
            <span>⚠️</span>
            <div>
              <strong>Cảnh báo phục hồi cơ bắp:</strong>
              <div>${dayWarnings.join(" • ")}</div>
            </div>
          </div>
        ` : ""}

        ${activeDay.exercises && activeDay.exercises.length > 0 ? `
          <div class="planner-exercise-grid">
            ${activeDay.exercises.map((ex, exIdx) => `
              <div class="planner-ex-card">
                <div class="ex-card-top">
                  <div>
                    <div class="ex-card-title">${ex.name}</div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">
                      Thiết bị: ${ex.equipment || "Bodyweight"}
                    </div>
                  </div>
                  <span class="badge ${ex.difficulty === 'Advanced' ? 'badge-advanced' : ex.difficulty === 'Intermediate' ? 'badge-intermediate' : 'badge-beginner'}">
                    ${ex.difficulty || 'Beginner'}
                  </span>
                </div>

                <div class="ex-card-metrics">
                  <span class="ex-metric">🔢 <strong>${ex.sets}</strong> hiệp</span>
                  <span class="ex-metric">🎯 <strong>${ex.reps}</strong> reps</span>
                  <span class="ex-metric">⏱️ Nghỉ <strong>${ex.rest_sec || 60}s</strong></span>
                </div>

                <div class="ex-card-muscles">
                  <span class="muscle-pill">${ex.primary_muscle || "Toàn thân"}</span>
                  ${ex.secondary_muscle ? `<span class="muscle-pill">${ex.secondary_muscle}</span>` : ""}
                </div>

                <div class="ex-card-actions">
                  <button class="btn btn-outline btn-sm btn-swap-exercise" data-day="${activeDay.day}" data-ex-id="${ex.id || 'squat'}" data-ex-name="${ex.name}">
                    🔄 Đổi bài tập
                  </button>
                  <button class="btn btn-primary btn-sm btn-start-planner-ex" data-id="${ex.id || 'squat'}" data-name="${ex.name}" data-reps="${ex.reps}">
                    ▶️ Tập bài này
                  </button>
                </div>
              </div>
            `).join("")}
          </div>
        ` : `
          <div style="text-align: center; padding: 3rem 1rem; color: var(--text-muted);">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">🛌</div>
            <h3 style="font-size: 1.25rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.3rem;">Ngày Nghỉ Phục Hồi Toàn Diện</h3>
            <p style="font-size: 0.9rem; max-width: 480px; margin: 0 auto;">
              Nghỉ ngơi 48-72h giữa các nhóm cơ giúp sợi cơ tổng hợp protein, phục hồi lượng glycogen dự trữ và ngăn ngừa chấn thương.
            </p>
          </div>
        `}

        <!-- Day Plan Editor Collapsible Box -->
        <div style="margin-top: 1.5rem; border-top: 1px solid var(--border-subtle); padding-top: 1.25rem;">
          <details id="details-edit-day" style="cursor: pointer;">
            <summary style="font-size: 0.95rem; font-weight: 700; color: var(--accent-cyan); display: flex; align-items: center; gap: 0.5rem;">
              ✏️ Tự chỉnh sửa giáo án ${activeDay.day}
            </summary>
            <div style="margin-top: 1rem; cursor: default;">
              <div class="form-group">
                <label class="form-label">Trọng tâm buổi tập:</label>
                <input type="text" class="form-control" id="edit-day-focus" value="${activeDay.focus}" />
              </div>

              <div class="form-group" style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem;">
                <input type="checkbox" id="edit-day-is-rest" ${activeDay.is_rest ? "checked" : ""} style="width: 18px; height: 18px;" />
                <label for="edit-day-is-rest" style="font-size: 0.88rem; font-weight: 600;">Đặt ngày này thành Ngày nghỉ phục hồi (Rest Day)</label>
              </div>

              <div id="edit-day-exercises-container" style="${activeDay.is_rest ? "display: none;" : ""}">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                  <h5 style="font-size: 0.88rem; font-weight: 700;">Danh sách bài tập trong ngày:</h5>
                  <button class="btn btn-outline btn-sm" id="btn-add-exercise-row" type="button">➕ Thêm bài tập</button>
                </div>
                <div class="table-wrapper">
                  <table class="fitsense-table" id="table-edit-day-exercises">
                    <thead>
                      <tr>
                        <th>Tên bài tập</th>
                        <th style="width: 80px;">Sets</th>
                        <th style="width: 90px;">Reps</th>
                        <th style="width: 80px;">Nghỉ (s)</th>
                        <th>Nhóm cơ</th>
                        <th style="width: 60px;">Xóa</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${(activeDay.exercises || []).map((ex, i) => `
                        <tr data-row-idx="${i}">
                          <td><input type="text" class="form-control ex-row-name" value="${ex.name}" /></td>
                          <td><input type="number" class="form-control ex-row-sets" value="${ex.sets || 3}" min="1" max="10" /></td>
                          <td><input type="text" class="form-control ex-row-reps" value="${ex.reps || '12'}" /></td>
                          <td><input type="number" class="form-control ex-row-rest" value="${ex.rest_sec || 60}" min="10" max="300" /></td>
                          <td><input type="text" class="form-control ex-row-muscle" value="${ex.primary_muscle || 'Toàn thân'}" /></td>
                          <td style="text-align: center;"><button type="button" class="btn btn-icon btn-sm btn-del-ex-row" style="color: var(--accent-crimson);">🗑️</button></td>
                        </tr>
                      `).join("")}
                    </tbody>
                  </table>
                </div>
              </div>

              <div style="margin-top: 1rem; display: flex; justify-content: flex-end;">
                <button class="btn btn-primary btn-sm" id="btn-save-day-edit">
                  💾 Lưu chỉnh sửa ${activeDay.day}
                </button>
              </div>
            </div>
          </details>
        </div>
      </div>
    `;

    // Tab switcher events
    container.querySelectorAll(".day-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        const idx = parseInt(tab.getAttribute("data-idx"), 10);
        this.activeDayIndex = idx;
        this.renderContent();
      });
    });

    // Generate AI button
    container.querySelector("#btn-generate-ai")?.addEventListener("click", async () => {
      const btn = container.querySelector("#btn-generate-ai");
      btn.disabled = true;
      btn.innerHTML = `⏳ AI đang phân tích thể trạng...`;
      try {
        const result = await API.planner.generate();
        Toast.success(result.message || "Tạo lịch tập thành công!");
        this.scheduleData = await API.planner.getWeek();
        this.renderContent();
      } catch (e) {
        Toast.error("Không thể tạo lịch: " + e.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `🤖 Tạo lịch bằng AI`;
      }
    });

    // Reset button
    container.querySelector("#btn-reset-planner")?.addEventListener("click", async () => {
      const confirmed = await showConfirmModal({
        title: "Đặt Lại Kế Hoạch Tuần",
        subtitle: "Khôi phục giáo án mặc định",
        icon: "🔄",
        message: "Bạn có chắc chắn muốn đặt lại kế hoạch tuần về cấu trúc mặc định chuẩn khoa học ban đầu không?",
        confirmText: "Đặt lại ngay",
        cancelText: "Hủy bỏ",
        confirmClass: "btn btn-primary",
      });
      if (confirmed) {
        try {
          await API.planner.reset();
          Toast.info("Đã đặt lại lịch tập tuần.");
          this.scheduleData = await API.planner.getWeek();
          this.renderContent();
        } catch (e) {
          Toast.error(e.message);
        }
      }
    });

    // Toggle upload custom plan box
    container.querySelector("#btn-toggle-upload-plan")?.addEventListener("click", () => {
      const box = container.querySelector("#box-upload-plan");
      if (box) box.style.display = box.style.display === "none" ? "block" : "none";
    });

    // Download sample template plan JSON
    container.querySelector("#btn-download-sample-plan")?.addEventListener("click", async () => {
      try {
        const data = await API.planner.template();
        const jsonStr = JSON.stringify(data.template, null, 2);
        const blob = new Blob([jsonStr], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = data.filename || "fitsense_plan_template.json";
        a.click();
        URL.revokeObjectURL(url);
        Toast.success("Đã tải file JSON mẫu thành công!");
      } catch (e) {
        Toast.error("Không thể tải file mẫu: " + e.message);
      }
    });

    // Apply uploaded plan
    container.querySelector("#btn-apply-uploaded-plan")?.addEventListener("click", async () => {
      const fileInput = container.querySelector("#file-plan-upload-input");
      const file = fileInput?.files?.[0];
      if (!file) {
        Toast.warning("Vui lòng chọn 1 file .json hoặc .csv trước!");
        return;
      }
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const content = e.target.result;
          const res = await API.planner.upload(content, file.name);
          Toast.success(res.message);
          this.scheduleData = await API.planner.getWeek();
          this.renderContent();
        } catch (err) {
          Toast.error(err.message);
        }
      };
      reader.readAsText(file);
    });

    // Toggle rest day in editor
    const isRestCheckbox = container.querySelector("#edit-day-is-rest");
    isRestCheckbox?.addEventListener("change", (e) => {
      const exContainer = container.querySelector("#edit-day-exercises-container");
      if (exContainer) exContainer.style.display = e.target.checked ? "none" : "block";
    });

    // Add new exercise row
    container.querySelector("#btn-add-exercise-row")?.addEventListener("click", () => {
      const tbody = container.querySelector("#table-edit-day-exercises tbody");
      if (!tbody) return;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><input type="text" class="form-control ex-row-name" placeholder="Tên bài tập" value="Bài tập mới" /></td>
        <td><input type="number" class="form-control ex-row-sets" value="3" min="1" max="10" /></td>
        <td><input type="text" class="form-control ex-row-reps" value="12" /></td>
        <td><input type="number" class="form-control ex-row-rest" value="60" min="10" max="300" /></td>
        <td><input type="text" class="form-control ex-row-muscle" value="Toàn thân" /></td>
        <td style="text-align: center;"><button type="button" class="btn btn-icon btn-sm btn-del-ex-row" style="color: var(--accent-crimson);">🗑️</button></td>
      `;
      tr.querySelector(".btn-del-ex-row")?.addEventListener("click", () => tr.remove());
      tbody.appendChild(tr);
    });

    // Bind delete row buttons
    container.querySelectorAll(".btn-del-ex-row").forEach((btn) => {
      btn.addEventListener("click", () => {
        btn.closest("tr")?.remove();
      });
    });

    // Save day edit
    container.querySelector("#btn-save-day-edit")?.addEventListener("click", async () => {
      const focus = container.querySelector("#edit-day-focus")?.value.trim() || "";
      const isRest = container.querySelector("#edit-day-is-rest")?.checked || false;
      const exercises = [];

      if (!isRest) {
        container.querySelectorAll("#table-edit-day-exercises tbody tr").forEach((tr) => {
          const name = tr.querySelector(".ex-row-name")?.value.trim();
          if (!name) return;
          const sets = parseInt(tr.querySelector(".ex-row-sets")?.value, 10) || 3;
          const reps = tr.querySelector(".ex-row-reps")?.value.trim() || "12";
          const rest = parseInt(tr.querySelector(".ex-row-rest")?.value, 10) || 60;
          const muscle = tr.querySelector(".ex-row-muscle")?.value.trim() || "Toàn thân";
          exercises.push({
            name,
            sets,
            reps,
            rest_sec: rest,
            primary_muscle: muscle,
            secondary_muscle: "Core",
            equipment: "Bodyweight",
            difficulty: "Beginner",
          });
        });
      }

      try {
        const res = await API.planner.updateDay(activeDay.day, focus, isRest, exercises);
        Toast.success(res.message);
        this.scheduleData = await API.planner.getWeek();
        this.renderContent();
      } catch (err) {
        Toast.error("Lỗi lưu giáo án: " + err.message);
      }
    });

    // Helper for safe workout start with recovery warning check
    const startWorkoutWithSafetyCheck = async (exerciseId, exerciseName, targetReps) => {
      if (dayWarnings.length > 0) {
        const confirmed = await showConfirmModal({
          title: `Cảnh Báo Phục Hồi Cơ Bắp (${activeDay.day})`,
          subtitle: "Bảo vệ nhóm cơ khỏi quá tải",
          icon: "⚠️",
          message: `
            <div style="background: rgba(245, 158, 11, 0.1); border-left: 3px solid var(--accent-amber); padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 0.85rem;">
              <ul style="margin: 0; padding-left: 1.2rem; color: var(--accent-amber); font-size: 0.9rem;">
                ${dayWarnings.map(w => `<li style="margin-bottom: 0.25rem;">${w}</li>`).join("")}
              </ul>
            </div>
            <p style="font-size: 0.9rem; margin-bottom: 0;">Nhóm cơ này có thể chưa phục hồi đủ 48 giờ. Bạn có muốn tiếp tục tập không?</p>
          `,
          confirmText: "Vẫn tiếp tục",
          cancelText: "Hủy bỏ",
          confirmClass: "btn btn-primary",
        });
        if (!confirmed) return;
      }
      window.startWorkoutSession(exerciseId, exerciseName, targetReps, activeDay.day);
    };

    // Start entire day workout
    container.querySelector("#btn-start-day-workout")?.addEventListener("click", async () => {
      const isToday = activeDay.day.toLowerCase() === todayName.toLowerCase();
      if (!isToday) {
        const confirmed = await showConfirmModal({
          title: "Xác Nhận Đổi Buổi Tập",
          subtitle: "FitSense Adaptive Assistant",
          icon: "🔀",
          message: `
            <div style="background: rgba(56, 189, 248, 0.08); border-left: 3px solid var(--accent-cyan); padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 0.85rem;">
              Bạn đang chọn tập giáo án của <b>${activeDay.day}</b> thay cho buổi hôm nay (<b>${todayName}</b>).
            </div>
            <p style="margin-bottom: 0.5rem;">FitSense AI sẽ tự động chuyển buổi tập này về hôm nay và sắp xếp lại các ngày còn lại trong tuần để cân bằng nhóm cơ & ngày nghỉ.</p>
            <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 0;">Bạn có muốn tiếp tục không?</p>
          `,
          confirmText: "Đồng ý",
          cancelText: "Hủy bỏ",
          confirmClass: "btn btn-cyan",
        });
        if (!confirmed) return;
      }

      try {
        const res = await API.planner.startDayWorkout(activeDay.day, true);
        if (res.rearranged) {
          Toast.success(`✨ ${res.message}`);
          this.scheduleData = await API.planner.getWeek();
          const newTodayIdx = this.scheduleData.schedule.findIndex(d => d.day.toLowerCase() === todayName.toLowerCase());
          if (newTodayIdx !== -1) this.activeDayIndex = newTodayIdx;
          this.renderContent();
        } else {
          Toast.success(`🚀 Bắt đầu buổi tập ${activeDay.day}!`);
        }

        const currentActive = this.scheduleData?.schedule?.[this.activeDayIndex] || activeDay;
        const firstEx = currentActive.exercises?.[0];
        if (firstEx) {
          await startWorkoutWithSafetyCheck(firstEx.id || "squat", firstEx.name, parseInt(firstEx.reps) || 12);
        }
      } catch (err) {
        Toast.error("Lỗi khởi động buổi tập: " + err.message);
      }
    });

    // Start single exercise
    container.querySelectorAll(".btn-start-planner-ex").forEach((b) => {
      b.addEventListener("click", async () => {
        const id = b.getAttribute("data-id");
        const name = b.getAttribute("data-name");
        const reps = parseInt(b.getAttribute("data-reps")) || 12;
        const isToday = activeDay.day.toLowerCase() === todayName.toLowerCase();
        if (!isToday) {
          const confirmed = await showConfirmModal({
            title: "Xác Nhận Đổi Buổi Tập",
            subtitle: "FitSense Adaptive Assistant",
            icon: "🔀",
            message: `
              <div style="background: rgba(56, 189, 248, 0.08); border-left: 3px solid var(--accent-cyan); padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 0.85rem;">
                Bạn đang chọn bài tập thuộc <b>${activeDay.day}</b> thay cho hôm nay (<b>${todayName}</b>).
              </div>
              <p style="margin-bottom: 0.5rem;">FitSense AI sẽ tự động sắp xếp lại giáo án tuần này để tối ưu chu kỳ hồi phục cơ bắp.</p>
              <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 0;">Bạn có muốn tiếp tục không?</p>
            `,
            confirmText: "Đồng ý",
            cancelText: "Hủy bỏ",
            confirmClass: "btn btn-cyan",
          });
          if (!confirmed) return;
          try {
            const res = await API.planner.startDayWorkout(activeDay.day, true);
            if (res.rearranged) {
              Toast.success(`✨ ${res.message}`);
              this.scheduleData = await API.planner.getWeek();
              const newTodayIdx = this.scheduleData.schedule.findIndex(d => d.day.toLowerCase() === todayName.toLowerCase());
              if (newTodayIdx !== -1) this.activeDayIndex = newTodayIdx;
              this.renderContent();
            }
          } catch (e) {
            console.warn("Could not reschedule:", e);
          }
        }
        await startWorkoutWithSafetyCheck(id, name, reps);
      });
    });

    // Swap exercise modal opener
    container.querySelectorAll(".btn-swap-exercise").forEach((b) => {
      b.addEventListener("click", async () => {
        const day = b.getAttribute("data-day");
        const exId = b.getAttribute("data-ex-id");
        const exName = b.getAttribute("data-ex-name");
        await this.openSwapModal(day, exId, exName);
      });
    });
  },

  async openSwapModal(day, exId, exName) {
    const modalBackdrop = document.getElementById("modal-swap");
    const modalBody = document.getElementById("swap-modal-body");
    if (!modalBackdrop || !modalBody) return;

    modalBody.innerHTML = `<div style="text-align: center; padding: 2rem;">⏳ Đang tìm bài tập thay thế tương đương từ AI...</div>`;
    modalBackdrop.classList.add("active");

    try {
      const data = await API.exercises.alternatives(exId);
      const alternatives = data.alternatives || [];

      if (alternatives.length === 0) {
        modalBody.innerHTML = `
          <div style="text-align: center; padding: 2rem; color: var(--text-secondary);">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">ℹ️</div>
            <p>Không có bài tập thay thế trực tiếp nào phù hợp với hạn chế thể chất hiện tại trong hồ sơ của bạn.</p>
          </div>
        `;
        return;
      }

      modalBody.innerHTML = `
        <div style="margin-bottom: 1.25rem;">
          <p style="font-size: 0.88rem; color: var(--text-secondary);">
            Đổi bài <b>"${exName}"</b> trong <b>${day}</b> sang bài tập có cùng cơ chế vận động và tác động nhóm cơ tương ứng:
          </p>
        </div>

        <div style="display: flex; flex-direction: column; gap: 0.75rem; max-height: 400px; overflow-y: auto;">
          ${alternatives.map((alt) => `
            <div class="stat-card" style="justify-content: space-between; cursor: pointer; padding: 1rem;" data-alt-id="${alt.id}">
              <div>
                <div style="font-weight: 700; font-size: 1rem; color: var(--text-primary);">${alt.name}</div>
                <div style="font-size: 0.8rem; color: var(--text-muted);">${alt.name_en} • ${alt.category}</div>
                <div style="display: flex; gap: 0.4rem; margin-top: 0.4rem;">
                  <span class="badge badge-beginner">${alt.difficulty}</span>
                  <span class="muscle-pill">${(alt.primary_muscles || []).join(", ")}</span>
                </div>
              </div>
              <button class="btn btn-primary btn-sm btn-select-swap" data-day="${day}" data-curr="${exId}" data-new="${alt.id}">
                Chọn bài này
              </button>
            </div>
          `).join("")}
        </div>
      `;

      modalBody.querySelectorAll(".btn-select-swap").forEach((btn) => {
        btn.addEventListener("click", async () => {
          const d = btn.getAttribute("data-day");
          const c = btn.getAttribute("data-curr");
          const n = btn.getAttribute("data-new");

          try {
            const res = await API.planner.swap(d, c, n);
            Toast.success(res.message);
            modalBackdrop.classList.remove("active");
            this.scheduleData = await API.planner.getWeek();
            this.renderContent();
          } catch (e) {
            Toast.error(e.message);
          }
        });
      });
    } catch (err) {
      modalBody.innerHTML = `<div style="color: var(--accent-crimson); padding: 1.5rem;">Lỗi tìm bài thay thế: ${err.message}</div>`;
    }
  },
};
