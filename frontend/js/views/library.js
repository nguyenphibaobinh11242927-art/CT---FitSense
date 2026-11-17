/**
 * FitSense Exercise Library View (28 Calisthenics Exercises)
 */

import { API } from "../api.js";
import { Toast } from "../components/toast.js";

export const LibraryView = {
  catalog: [],
  meta: null,
  activeFilters: {
    query: "",
    muscles: [],
    role: "all",
    difficulty: "",
    equipment: "",
    category: "",
  },
  debounceTimer: null,

  async render() {
    const container = document.getElementById("view-library");
    if (!container) return;

    try {
      const [metaData, listData] = await Promise.all([
        API.exercises.meta(),
        API.exercises.list(),
      ]);
      this.meta = metaData;
      this.catalog = listData.exercises || [];
      this.renderContent();
    } catch (err) {
      console.error("Library render error:", err);
      container.innerHTML = `<div class="fitsense-card" style="color: var(--accent-crimson);">Lỗi tải thư viện bài tập: ${err.message}</div>`;
    }
  },

  renderContent() {
    const container = document.getElementById("view-library");
    if (!container) return;

    const muscles = this.meta?.muscles || {};

    container.innerHTML = `
      <div class="view-header">
        <div class="view-title-group">
          <h2>📚 Thư viện</h2>
          <p>Kho bài tập thể hình không tạ chuẩn hóa khoa học, kiểm duyệt chuyển động và bảo vệ khớp.</p>
        </div>
      </div>

      <!-- Filters & Search Toolbar -->
      <div class="library-filters">
        <div class="search-box-wrapper">
          <span class="search-icon">🔍</span>
          <input 
            type="text" 
            class="search-input" 
            id="lib-search-input" 
            placeholder="Tìm kiếm bài tập theo tên tiếng Việt, tiếng Anh hoặc nhóm cơ (VD: Squat, Hít đất, Ngực, Bụng...)" 
            value="${this.activeFilters.query}"
          />
        </div>

        <!-- Muscle Group Pills -->
        <div class="filter-pills-row" id="muscle-filters-row">
          <button class="filter-btn ${this.activeFilters.muscles.length === 0 ? 'active' : ''}" data-muscle="">
            Tất cả nhóm cơ
          </button>
          ${Object.entries(muscles).map(([key, label]) => `
            <button class="filter-btn ${this.activeFilters.muscles.includes(key) ? 'active' : ''}" data-muscle="${key}">
              ${label}
            </button>
          `).join("")}
        </div>

        <!-- Difficulty, Role, Equipment, Category Filter Rows -->
        <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.5rem; align-items: center;">
          <div class="filter-pills-row" id="difficulty-filters-row">
            <span style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted); align-self: center;">Độ khó:</span>
            <button class="filter-btn ${!this.activeFilters.difficulty ? 'active' : ''}" data-diff="">Tất cả</button>
            <button class="filter-btn ${this.activeFilters.difficulty === 'Beginner' ? 'active' : ''}" data-diff="Beginner">Beginner</button>
            <button class="filter-btn ${this.activeFilters.difficulty === 'Intermediate' ? 'active' : ''}" data-diff="Intermediate">Intermediate</button>
            <button class="filter-btn ${this.activeFilters.difficulty === 'Advanced' ? 'active' : ''}" data-diff="Advanced">Advanced</button>
          </div>

          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <label style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted);">Vai trò cơ:</label>
            <select class="form-select" id="lib-role-select" style="padding: 0.35rem 0.65rem; font-size: 0.85rem; width: auto; background-color: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color);">
              <option value="all" ${this.activeFilters.role === 'all' ? 'selected' : ''}>Chính hoặc phụ</option>
              <option value="primary" ${this.activeFilters.role === 'primary' ? 'selected' : ''}>Chỉ cơ chính</option>
              <option value="secondary" ${this.activeFilters.role === 'secondary' ? 'selected' : ''}>Chỉ cơ phụ</option>
            </select>
          </div>

          <div style="display: flex; gap: 0.5rem; align-items: center;">
            <label style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted);">Dụng cụ:</label>
            <select class="form-select" id="lib-equip-select" style="padding: 0.35rem 0.65rem; font-size: 0.85rem; width: auto; background-color: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color);">
              <option value="" ${!this.activeFilters.equipment ? 'selected' : ''}>Mọi dụng cụ</option>
              <option value="__none__" ${this.activeFilters.equipment === '__none__' ? 'selected' : ''}>Không cần dụng cụ</option>
              <option value="mat" ${this.activeFilters.equipment === 'mat' ? 'selected' : ''}>Thảm tập</option>
              <option value="bar" ${this.activeFilters.equipment === 'bar' ? 'selected' : ''}>Xà đơn</option>
              <option value="band" ${this.activeFilters.equipment === 'band' ? 'selected' : ''}>Dây kháng lực</option>
              <option value="chair" ${this.activeFilters.equipment === 'chair' ? 'selected' : ''}>Ghế / Điểm tựa</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Interactive Anatomical Body Info Bar -->
      <div class="anatomy-box">
        <div class="anatomy-info">
          <h4>🧬 Bản đồ Giải phẫu Cơ bắp Tương tác</h4>
          <p>Chọn nhanh một hoặc nhiều nhóm cơ để lọc ngay các bài tập tác động trực tiếp và gián tiếp</p>
        </div>
        <div class="muscle-tags-cloud">
          <span class="muscle-tag-clickable ${this.activeFilters.muscles.includes('chest') ? 'active' : ''}" data-muscle="chest">🛡️ Ngực</span>
          <span class="muscle-tag-clickable ${this.activeFilters.muscles.includes('back') ? 'active' : ''}" data-muscle="back">🦅 Lưng/Xô</span>
          <span class="muscle-tag-clickable ${this.activeFilters.muscles.includes('quads') ? 'active' : ''}" data-muscle="quads">🦵 Đùi trước</span>
          <span class="muscle-tag-clickable ${this.activeFilters.muscles.includes('core') ? 'active' : ''}" data-muscle="core">🧱 Cơ Bụng</span>
          <span class="muscle-tag-clickable ${this.activeFilters.muscles.includes('shoulders') ? 'active' : ''}" data-muscle="shoulders">⛰️ Khớp Vai</span>
          <span class="muscle-tag-clickable ${this.activeFilters.muscles.includes('triceps') ? 'active' : ''}" data-muscle="triceps">💪 Tay sau</span>
        </div>
      </div>

      <!-- Exercises Grid -->
      <div class="library-grid" id="library-cards-container">
        ${this.renderCardsHtml()}
      </div>
    `;

    // Bind Search Input with debounce
    const searchInput = container.querySelector("#lib-search-input");
    searchInput?.addEventListener("input", (e) => {
      clearTimeout(this.debounceTimer);
      this.activeFilters.query = e.target.value.trim();
      this.debounceTimer = setTimeout(() => this.filterAndReRenderCards(), 200);
    });

    // Muscle Filter UI sync helper
    const syncMuscleFilterUI = () => {
      const isAll = this.activeFilters.muscles.length === 0;
      container.querySelectorAll("#muscle-filters-row .filter-btn, .muscle-tag-clickable").forEach((btn) => {
        const m = btn.getAttribute("data-muscle") || "";
        if (!m) {
          btn.classList.toggle("active", isAll);
        } else {
          btn.classList.toggle("active", this.activeFilters.muscles.includes(m));
        }
      });
    };

    // Muscle Filter buttons & anatomy tags (Multi-select toggle)
    container.querySelectorAll("#muscle-filters-row .filter-btn, .muscle-tag-clickable").forEach((btn) => {
      btn.addEventListener("click", () => {
        const m = btn.getAttribute("data-muscle") || "";
        if (!m) {
          this.activeFilters.muscles = [];
        } else {
          const idx = this.activeFilters.muscles.indexOf(m);
          if (idx > -1) {
            this.activeFilters.muscles.splice(idx, 1);
          } else {
            this.activeFilters.muscles.push(m);
          }
        }
        syncMuscleFilterUI();
        this.filterAndReRenderCards();
      });
    });

    // Difficulty buttons
    container.querySelectorAll("#difficulty-filters-row .filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const d = btn.getAttribute("data-diff") || "";
        this.activeFilters.difficulty = d;
        container.querySelectorAll("#difficulty-filters-row .filter-btn").forEach((b) => {
          b.classList.toggle("active", (b.getAttribute("data-diff") || "") === d);
        });
        this.filterAndReRenderCards();
      });
    });

    // Role Select
    container.querySelector("#lib-role-select")?.addEventListener("change", (e) => {
      this.activeFilters.role = e.target.value;
      this.filterAndReRenderCards();
    });

    // Equipment Select
    container.querySelector("#lib-equip-select")?.addEventListener("change", (e) => {
      this.activeFilters.equipment = e.target.value;
      this.filterAndReRenderCards();
    });

    this.bindCardEvents();
  },

  renderCardsHtml() {
    if (!this.catalog || this.catalog.length === 0) {
      return `
        <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--text-muted);">
          <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">🔍</div>
          <p>Không tìm thấy bài tập nào khớp với bộ lọc hiện tại.</p>
        </div>
      `;
    }

    return this.catalog.map((ex) => {
      const gifSrc = ex.media_gif ? `/${ex.media_gif}` : null;
      return `
        <div class="lib-card">
          <div class="lib-card-media">
            ${gifSrc 
              ? `<img src="${gifSrc}" alt="${ex.name}" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'lib-media-placeholder\\'><span>🏋️</span><span>${ex.name}</span></div>'" />`
              : `<div class="lib-media-placeholder"><span>🤸</span><span style="font-size: 0.8rem; font-weight: 600;">Calisthenics</span></div>`
            }
          </div>

          <div class="lib-card-body">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.3rem;">
              <h4 class="lib-card-title">${ex.name}</h4>
              <div style="display: flex; gap: 0.35rem; align-items: center;">
                ${ex.has_personal_warning ? `<span class="badge badge-advanced" style="font-size: 0.72rem; padding: 0.2rem 0.5rem;">⚠️ Hạn chế</span>` : ""}
                <span class="badge ${ex.difficulty === 'Advanced' ? 'badge-advanced' : ex.difficulty === 'Intermediate' ? 'badge-intermediate' : 'badge-beginner'}">
                  ${ex.difficulty}
                </span>
              </div>
            </div>
            <div class="lib-card-sub">${ex.name_en} • ${ex.category}</div>
            
            <p class="lib-card-desc">${ex.description}</p>

            <div class="ex-card-muscles" style="margin-bottom: 1.25rem;">
              ${(ex.primary_muscles || []).map((m) => `<span class="muscle-pill" style="border-color: var(--border-glow);">${m}</span>`).join("")}
              ${(ex.equipment || []).map((eq) => `<span class="muscle-pill">${eq}</span>`).join("")}
            </div>

            <div style="display: flex; gap: 0.6rem; margin-top: auto;">
              <button class="btn btn-outline btn-sm btn-view-exercise-detail" style="flex: 1;" data-id="${ex.id}">
                📖 Xem kỹ thuật
              </button>
              <button class="btn btn-primary btn-sm btn-lib-start-hud" data-id="${ex.id}" data-name="${ex.name}">
                ▶️ Tập
              </button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  },

  async filterAndReRenderCards() {
    try {
      const params = {
        query: this.activeFilters.query || "",
        muscle: (this.activeFilters.muscles || []).join(","),
        role: this.activeFilters.role || "all",
        difficulty: this.activeFilters.difficulty || "",
        equipment: this.activeFilters.equipment || "",
        category: this.activeFilters.category || "",
      };
      const data = await API.exercises.list(params);
      this.catalog = data.exercises || [];
      const cardsContainer = document.getElementById("library-cards-container");
      if (cardsContainer) {
        cardsContainer.innerHTML = this.renderCardsHtml();
        this.bindCardEvents();
      }
    } catch (e) {
      console.error("Filter exercises error:", e);
    }
  },

  bindCardEvents() {
    const container = document.getElementById("view-library");
    if (!container) return;

    container.querySelectorAll(".btn-view-exercise-detail").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        await this.openDetailModal(id);
      });
    });

    container.querySelectorAll(".btn-lib-start-hud").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-id");
        const name = btn.getAttribute("data-name");
        window.startWorkoutSession(id, name, 12);
      });
    });
  },

  async openDetailModal(exerciseId) {
    const modalBackdrop = document.getElementById("modal-exercise-detail");
    const modalBody = document.getElementById("exercise-detail-body");
    if (!modalBackdrop || !modalBody) return;

    modalBody.innerHTML = `<div style="text-align: center; padding: 2rem;">⏳ Đang tải hướng dẫn...</div>`;
    modalBackdrop.classList.add("active");

    try {
      const ex = await API.exercises.detail(exerciseId);
      const gifSrc = ex.media_gif ? `/${ex.media_gif}` : null;

      modalBody.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
          <div>
            <h3 style="font-size: 1.4rem; font-weight: 800; color: var(--text-primary);">${ex.name}</h3>
            <div style="font-size: 0.9rem; color: var(--accent-cyan);">${ex.name_en} • ${ex.category}</div>
          </div>
          <span class="badge ${ex.difficulty === 'Advanced' ? 'badge-advanced' : ex.difficulty === 'Intermediate' ? 'badge-intermediate' : 'badge-beginner'}" style="font-size: 0.85rem; padding: 0.3rem 0.75rem;">
            ${ex.difficulty}
          </span>
        </div>

        ${ex.has_personal_warning ? `
          <div class="ai-reason-box" style="margin-bottom: 1.25rem; border-color: var(--accent-crimson); background: rgba(239, 68, 68, 0.1); color: var(--accent-crimson); font-weight: 600;">
            ${ex.personal_warning_message}
          </div>
        ` : ""}

        ${ex.muscle_svg ? `
          <div style="background: #edf1f6; border-radius: var(--radius-md); padding: 0.75rem; margin-bottom: 1.25rem; text-align: center;">
            <div style="font-size: 0.82rem; font-weight: 700; color: #1e293b; margin-bottom: 0.4rem;">
              🧍 Sơ đồ Giải phẫu Cơ bắp (Xanh = Cơ chính, Cam = Cơ phụ)
            </div>
            <div style="max-width: 300px; margin: 0 auto; line-height: 0;">
              ${ex.muscle_svg}
            </div>
          </div>
        ` : ""}

        ${gifSrc ? `
          <div style="width: 100%; height: 220px; background: #000; border-radius: var(--radius-md); overflow: hidden; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: center;">
            <img src="${gifSrc}" alt="${ex.name}" style="max-height: 100%; object-fit: contain;" />
          </div>
        ` : ""}

        <div style="margin-bottom: 1.25rem;">
          <h5 style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.3rem; color: var(--text-primary);">Mô tả chuyển động:</h5>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5;">${ex.description}</p>
        </div>

        <div style="margin-bottom: 1.25rem;">
          <h5 style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--text-primary);">Các bước thực hiện chuẩn:</h5>
          <ol style="padding-left: 1.2rem; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
            ${(ex.steps || []).map((step) => `<li style="margin-bottom: 0.3rem;">${step}</li>`).join("")}
          </ol>
        </div>

        <div style="margin-bottom: 1.25rem;">
          <h5 style="font-weight: 700; font-size: 0.95rem; margin-bottom: 0.5rem; color: var(--accent-amber);">⚠️ Lỗi sai thường gặp:</h5>
          <ul style="padding-left: 1.2rem; font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6;">
            ${(ex.common_mistakes || []).map((m) => `<li style="margin-bottom: 0.3rem;">${m}</li>`).join("")}
          </ul>
        </div>

        <div class="ai-reason-box" style="margin-bottom: 1.5rem;">
          🛡️ <b>Lưu ý an toàn khớp:</b> ${ex.safety_notes || "Luôn khởi động kỹ và kiểm soát nhịp thở."}
        </div>

        ${ex.suggested_alternatives && ex.suggested_alternatives.length > 0 ? `
          <div style="margin-bottom: 1.5rem; padding: 0.85rem; background: var(--surface-card); border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            <h5 style="font-weight: 700; font-size: 0.88rem; margin-bottom: 0.4rem; color: var(--accent-cyan);">🔄 Gợi ý bài tập thay thế an toàn:</h5>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
              ${ex.suggested_alternatives.map((a) => `<span class="muscle-pill btn-alt-click" style="cursor: pointer; border-color: var(--accent-cyan);" data-alt-id="${a.id}">👉 ${a.name} (${a.difficulty})</span>`).join("")}
            </div>
          </div>
        ` : ""}

        <div style="display: flex; justify-content: flex-end; gap: 0.75rem;">
          <button class="btn btn-outline" onclick="document.getElementById('modal-exercise-detail').classList.remove('active')">
            Đóng
          </button>
          <button class="btn btn-emerald" id="btn-modal-start-workout">
            🚀 Bắt đầu tập với AI HUD
          </button>
        </div>
      `;

      modalBody.querySelectorAll(".btn-alt-click").forEach((pill) => {
        pill.addEventListener("click", () => {
          const altId = pill.getAttribute("data-alt-id");
          if (altId) this.openDetailModal(altId);
        });
      });

      modalBody.querySelector("#btn-modal-start-workout")?.addEventListener("click", () => {
        modalBackdrop.classList.remove("active");
        window.startWorkoutSession(ex.id, ex.name, 12);
      });
    } catch (e) {
      modalBody.innerHTML = `<div style="color: var(--accent-crimson); padding: 1.5rem;">Lỗi tải bài tập: ${e.message}</div>`;
    }
  },
};
