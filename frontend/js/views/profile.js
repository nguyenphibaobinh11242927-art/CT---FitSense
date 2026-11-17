/**
 * FitSense Profile & Biometrics View
 */

import { API } from "../api.js";
import { Toast } from "../components/toast.js";

export const ProfileView = {
  profileData: null,

  async render() {
    const container = document.getElementById("view-profile");
    if (!container) return;

    try {
      this.profileData = await API.profile.get();
      this.renderContent();
    } catch (err) {
      console.error("Profile load error:", err);
      container.innerHTML = `<div class="fitsense-card" style="color: var(--accent-crimson);">Lỗi tải hồ sơ: ${err.message}</div>`;
    }
  },

  renderContent() {
    const container = document.getElementById("view-profile");
    if (!container) return;

    if (!this.profileData) {
      container.innerHTML = `
        <div class="fitsense-card" style="text-align: center; padding: 3rem 1.5rem; max-width: 600px; margin: 2rem auto;">
          <div style="font-size: 3rem; margin-bottom: 0.75rem;">🔐</div>
          <h3 style="font-size: 1.4rem; font-weight: 800; margin-bottom: 0.5rem;">Cần Đăng Nhập Tài Khoản</h3>
          <p style="font-size: 0.92rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 1.5rem;">
            Bạn đang xem dưới <b>Chế độ Khách</b>. Hãy đăng nhập hoặc đăng ký bằng tài khoản Google để thiết lập hồ sơ thể chất, tính chỉ số BMI và lưu trữ dữ liệu vĩnh viễn!
          </p>
          <div style="display: flex; justify-content: center; gap: 0.75rem;">
            <button class="btn btn-primary" id="btn-profile-login-prompt">
              🔐 Đăng nhập / Đăng ký ngay
            </button>
          </div>
        </div>
      `;
      container.querySelector("#btn-profile-login-prompt")?.addEventListener("click", () => {
        document.getElementById("modal-auth")?.classList.add("active");
      });
      return;
    }

    const p = this.profileData;
    const heightM = (p.height_cm || 170) / 100;
    const initialBMI = ((p.weight_kg || 65) / (heightM * heightM)).toFixed(1);

    container.innerHTML = `
      <div class="view-header">
        <div class="view-title-group">
          <h2>👤 Hồ sơ Thể chất & Hạn chế Vận động</h2>
          <p>Tối ưu hóa phác đồ Calisthenics dựa trên thông số sinh học thực tế và thể trạng bảo vệ khớp.</p>
        </div>
        <button class="btn btn-emerald" id="btn-save-profile">
          💾 Lưu cập nhật hồ sơ
        </button>
      </div>

      <div class="profile-layout">
        <!-- Left Column: Biometrics & Goals -->
        <div class="fitsense-card">
          <h3 style="font-size: 1.15rem; font-weight: 800; margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem;">
            📊 1. Thông số Sinh trắc học & Thể lực
          </h3>

          <div class="form-group">
            <label class="form-label">Họ và tên của bạn:</label>
            <input type="text" class="form-input" id="prof-name" value="${p.name || 'FitSense Athlete'}" />
          </div>

          <div class="form-group">
            <label class="form-label">Email tài khoản:</label>
            <input type="email" class="form-input" id="prof-email" value="${p.email || 'user@fitsense.local'}" disabled style="opacity: 0.7; cursor: not-allowed;" />
          </div>

          <div class="form-row-3">
            <div class="form-group">
              <label class="form-label">Cân nặng (kg):</label>
              <input type="number" class="form-input" id="prof-weight" min="30" max="200" step="0.5" value="${p.weight_kg || 65}" />
            </div>

            <div class="form-group">
              <label class="form-label">Chiều cao (cm):</label>
              <input type="number" class="form-input" id="prof-height" min="100" max="230" step="0.5" value="${p.height_cm || 170}" />
            </div>

            <div class="form-group">
              <label class="form-label">Tuổi:</label>
              <input type="number" class="form-input" id="prof-age" min="12" max="90" value="${p.age || 22}" />
            </div>
          </div>

          <!-- Interactive BMI Gauge Widget -->
          <div class="bmi-widget" id="bmi-widget-box">
            <div class="bmi-top">
              <div>
                <span style="font-size: 0.75rem; text-transform: uppercase; font-weight: 700; color: var(--accent-cyan); letter-spacing: 0.5px;">
                  Chỉ số BMI Tính toán Tự động
                </span>
                <div style="font-size: 1.05rem; font-weight: 800; color: var(--text-primary); margin-top: 0.2rem;" id="bmi-category-text">
                  Cân đối lý tưởng
                </div>
              </div>
              <div class="bmi-value-large" id="bmi-val-text">${initialBMI}</div>
            </div>

            <div class="bmi-gauge-bar">
              <div class="bmi-needle" id="bmi-needle" style="left: 45%;"></div>
            </div>

            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted);">
              <span>Gầy (&lt;18.5)</span>
              <span>Lý tưởng (18.5 - 24.9)</span>
              <span>Thừa cân (25 - 29.9)</span>
              <span>Béo phì (&gt;30)</span>
            </div>

            <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.75rem; line-height: 1.4;" id="bmi-desc-text">
              Chỉ số BMI lý tưởng! Hãy duy trì phong độ với lịch rèn luyện Calisthenics toàn diện.
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Trình độ rèn luyện thể lực:</label>
            <select class="form-select" id="prof-level">
              <option value="Beginner (Người mới bắt đầu)" ${p.fitness_level?.includes('Beginner') ? 'selected' : ''}>Beginner (Mới bắt đầu / Cần xây dựng nền tảng)</option>
              <option value="Intermediate (Đã có nền tảng)" ${p.fitness_level?.includes('Intermediate') ? 'selected' : ''}>Intermediate (Trung cấp / Đã tập trên 6 tháng)</option>
              <option value="Advanced (Thuần thục)" ${p.fitness_level?.includes('Advanced') ? 'selected' : ''}>Advanced (Nâng cao / Calisthenics thuần thục)</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Mục tiêu rèn luyện chính:</label>
            <select class="form-select" id="prof-goal">
              <option value="Tăng cơ & Sức mạnh" ${p.goal?.includes('Tăng cơ') ? 'selected' : ''}>Tăng cơ & Sức mạnh Calisthenics</option>
              <option value="Đốt mỡ & Săn chắc toàn thân" ${p.goal?.includes('Đốt mỡ') ? 'selected' : ''}>Đốt mỡ & Săn chắc toàn thân (Fat Loss)</option>
              <option value="Sức bền & Tim mạch" ${p.goal?.includes('Sức bền') ? 'selected' : ''}>Sức bền & Thể lực tim mạch (Endurance)</option>
              <option value="Dẻo dai & Sức mạnh cốt lõi" ${p.goal?.includes('Dẻo dai') ? 'selected' : ''}>Dẻo dai & Sức mạnh cốt lõi (Core/Flexibility)</option>
            </select>
          </div>
        </div>

        <!-- Right Column: Restrictions & Equipment -->
        <div class="fitsense-card">
          <h3 style="font-size: 1.15rem; font-weight: 800; margin-bottom: 1.25rem; display: flex; align-items: center; gap: 0.5rem;">
            🛡️ 2. Hạn chế Chấn thương & Dụng cụ Tập
          </h3>

          <div class="form-group">
            <label class="form-label">Hạn chế vận động & Chấn thương (AI sẽ tự động lọc bài an toàn):</label>
            <div class="checkbox-grid" id="restrictions-list">
              <label class="checkbox-label">
                <input type="checkbox" value="Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)" ${p.restrictions?.includes('Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)') ? 'checked' : ''} class="cb-restr-all" />
                <span>Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" value="Khớp gối yếu (Tránh Squat quá sâu, Jumping)" ${p.restrictions?.some(r => r.includes('gối')) ? 'checked' : ''} class="cb-restr-item" />
                <span>Khớp gối yếu (Tránh Squat quá sâu, Jumping Jacks)</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" value="Cổ tay đau (Hạn chế Push-up sàn phẳng)" ${p.restrictions?.some(r => r.includes('tay')) ? 'checked' : ''} class="cb-restr-item" />
                <span>Cổ tay đau (Hạn chế Push-up sàn phẳng)</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" value="Đau lưng dưới / Thoát vị nhẹ (Tránh gập lưng nặng)" ${p.restrictions?.some(r => r.includes('lưng')) ? 'checked' : ''} class="cb-restr-item" />
                <span>Đau lưng dưới / Thoát vị nhẹ (Tránh gập lưng nặng)</span>
              </label>
            </div>
          </div>

          <div class="form-group" style="margin-top: 1.5rem;">
            <label class="form-label">Trang thiết bị & Dụng cụ sẵn có:</label>
            <div class="checkbox-grid" id="equipment-list">
              <label class="checkbox-label">
                <input type="checkbox" value="Không có dụng cụ (Chỉ tập Bodyweight)" ${p.equipment?.includes('Không có dụng cụ (Chỉ tập Bodyweight)') ? 'checked' : ''} class="cb-equip-none" />
                <span>Không có dụng cụ (Chỉ tập Bodyweight thuần túy)</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" value="Thảm yoga/thể dục" ${p.equipment?.some(e => e.includes('Thảm')) ? 'checked' : ''} class="cb-equip-item" />
                <span>Thảm yoga / thảm thể dục êm ái</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" value="Ghế tựa / Điểm tựa cao" ${p.equipment?.some(e => e.includes('Ghế')) ? 'checked' : ''} class="cb-equip-item" />
                <span>Ghế tựa / Ghế sofa / Điểm tựa cao</span>
              </label>
              <label class="checkbox-label">
                <input type="checkbox" value="Dây kháng lực (Resistance Band)" ${p.equipment?.some(e => e.includes('Dây')) ? 'checked' : ''} class="cb-equip-item" />
                <span>Dây kháng lực (Resistance Band)</span>
              </label>
            </div>
          </div>

          <div class="form-row-3" style="margin-top: 1.5rem;">
            <div class="form-group">
              <label class="form-label">Số ngày tập/tuần:</label>
              <select class="form-select" id="prof-days">
                <option value="3" ${p.days_per_week === 3 ? 'selected' : ''}>3 ngày</option>
                <option value="4" ${p.days_per_week === 4 || !p.days_per_week ? 'selected' : ''}>4 ngày (Khuyên dùng)</option>
                <option value="5" ${p.days_per_week === 5 ? 'selected' : ''}>5 ngày</option>
                <option value="6" ${p.days_per_week === 6 ? 'selected' : ''}>6 ngày</option>
              </select>
            </div>

            <div class="form-group" style="grid-column: span 2;">
              <label class="form-label">Thời lượng buổi tập (phút):</label>
              <select class="form-select" id="prof-duration">
                <option value="30" ${p.session_duration_minutes === 30 ? 'selected' : ''}>30 phút (Nhanh gọn)</option>
                <option value="45" ${p.session_duration_minutes === 45 || !p.session_duration_minutes ? 'selected' : ''}>45 phút (Chuẩn khoa học)</option>
                <option value="60" ${p.session_duration_minutes === 60 ? 'selected' : ''}>60 phút (Chuyên sâu)</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    `;

    // Dynamic BMI updates when weight or height change
    const weightInp = container.querySelector("#prof-weight");
    const heightInp = container.querySelector("#prof-height");
    const updateBMI = async () => {
      const w = parseFloat(weightInp.value) || 60;
      const h = parseFloat(heightInp.value) || 170;
      if (w >= 30 && h >= 100) {
        try {
          const res = await API.profile.calculateBMI(w, h);
          container.querySelector("#bmi-val-text").textContent = res.bmi;
          container.querySelector("#bmi-category-text").textContent = res.category;
          container.querySelector("#bmi-desc-text").textContent = res.description;

          // Needle pos: 15 BMI = 0%, 35 BMI = 100%
          const pct = Math.max(5, Math.min(95, ((res.bmi - 15) / (35 - 15)) * 100));
          const needle = container.querySelector("#bmi-needle");
          if (needle) needle.style.left = `${pct}%`;
        } catch (e) {}
      }
    };

    weightInp?.addEventListener("input", updateBMI);
    heightInp?.addEventListener("input", updateBMI);
    updateBMI();

    // Mutual exclusivity for checkboxes
    const cbRestrAll = container.querySelector(".cb-restr-all");
    const cbRestrItems = container.querySelectorAll(".cb-restr-item");
    cbRestrAll?.addEventListener("change", () => {
      if (cbRestrAll.checked) {
        cbRestrItems.forEach((cb) => (cb.checked = false));
      }
    });
    cbRestrItems.forEach((cb) => {
      cb.addEventListener("change", () => {
        if (cb.checked && cbRestrAll) cbRestrAll.checked = false;
      });
    });

    const cbEquipNone = container.querySelector(".cb-equip-none");
    const cbEquipItems = container.querySelectorAll(".cb-equip-item");
    cbEquipNone?.addEventListener("change", () => {
      if (cbEquipNone.checked) {
        cbEquipItems.forEach((cb) => (cb.checked = false));
      }
    });
    cbEquipItems.forEach((cb) => {
      cb.addEventListener("change", () => {
        if (cb.checked && cbEquipNone) cbEquipNone.checked = false;
      });
    });

    // Save profile handler
    container.querySelector("#btn-save-profile")?.addEventListener("click", async () => {
      const name = container.querySelector("#prof-name").value.trim();
      const email = container.querySelector("#prof-email").value.trim();
      const weight_kg = parseFloat(weightInp.value);
      const height_cm = parseFloat(heightInp.value);
      const age = parseInt(container.querySelector("#prof-age").value, 10);
      const fitness_level = container.querySelector("#prof-level").value;
      const goal = container.querySelector("#prof-goal").value;
      const days_per_week = parseInt(container.querySelector("#prof-days").value, 10);
      const session_duration_minutes = parseInt(container.querySelector("#prof-duration").value, 10);

      // Gather restrictions
      const restrictions = [];
      if (cbRestrAll && cbRestrAll.checked) {
        restrictions.push(cbRestrAll.value);
      } else {
        cbRestrItems.forEach((cb) => {
          if (cb.checked) restrictions.push(cb.value);
        });
      }
      if (restrictions.length === 0) {
        restrictions.push("Không có hạn chế nào (Thể trạng hoàn toàn khỏe mạnh)");
      }

      // Gather equipment
      const equipment = [];
      if (cbEquipNone && cbEquipNone.checked) {
        equipment.push(cbEquipNone.value);
      } else {
        cbEquipItems.forEach((cb) => {
          if (cb.checked) equipment.push(cb.value);
        });
      }
      if (equipment.length === 0) {
        equipment.push("Không có dụng cụ (Chỉ tập Bodyweight)");
      }

      const updatedPayload = {
        name,
        email,
        weight_kg,
        height_cm,
        age,
        fitness_level,
        goal,
        environment: "Tại nhà (Home Workout)",
        restrictions,
        equipment,
        days_per_week,
        session_duration_minutes,
      };

      try {
        const res = await API.profile.update(updatedPayload);
        Toast.success(res.message || "Cập nhật hồ sơ thành công!");
        if (res.schedule_updated && res.schedule_changes && res.schedule_changes.length > 0) {
          setTimeout(() => {
            Toast.success(`🛡️ AI đã tự động thay thế ${res.schedule_changes.length} bài tập trong Kế hoạch tuần để bảo vệ bạn khỏi chấn thương!`);
          }, 800);
        }
        this.profileData = updatedPayload;
        
        // Update user badge in navbar
        const navName = document.querySelector(".user-name");
        if (navName) navName.textContent = name;
      } catch (e) {
        Toast.error("Không thể lưu hồ sơ: " + e.message);
      }
    });
  },
};
