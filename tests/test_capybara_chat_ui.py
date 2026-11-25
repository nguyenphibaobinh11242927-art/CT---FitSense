"""Unit and integration tests for Capybara AI Assistant Chat Dialog (SCRUM-31)."""

import os
import unittest


class TestCapybaraChatUI(unittest.TestCase):
    """Kiểm tra tính toàn vẹn cấu trúc giao diện và logic của Capybara Chat."""

    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.html_path = os.path.join(cls.base_dir, "frontend", "index.html")
        cls.css_path = os.path.join(cls.base_dir, "frontend", "css", "style.css")
        cls.chat_js_path = os.path.join(cls.base_dir, "frontend", "js", "components", "capybara_chat.js")
        cls.companion_js_path = os.path.join(cls.base_dir, "frontend", "js", "components", "capybara.js")
        cls.api_js_path = os.path.join(cls.base_dir, "frontend", "js", "api.js")
        cls.app_js_path = os.path.join(cls.base_dir, "frontend", "js", "app.js")
        cls.expressions_js_path = os.path.join(cls.base_dir, "frontend", "js", "components", "capybara_expressions.js")
        cls.action_card_js_path = os.path.join(cls.base_dir, "frontend", "js", "components", "capybara_action_card.js")

    def test_html_modal_structure(self):
        """Đảm bảo frontend/index.html chứa đầy đủ cấu trúc modal Capybara Chat."""
        with open(self.html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('id="modal-capybara-chat"', html)
        self.assertIn('class="modal-backdrop capy-chat-backdrop"', html)
        self.assertIn('id="capy-chat-dialog-box"', html)
        self.assertIn('class="capy-chat-header"', html)
        self.assertIn('id="btn-capy-clear-chat"', html)
        self.assertIn('id="btn-capy-chat-close"', html)
        self.assertIn('id="capy-chips-wrapper"', html)
        self.assertIn('id="capy-chips-list"', html)
        self.assertIn('id="capy-messages-container"', html)
        self.assertIn('id="capy-chat-form"', html)
        self.assertIn('id="capy-chat-input"', html)
        self.assertIn('id="capy-chat-send-btn"', html)

    def test_css_styles_and_animation(self):
        """Đảm bảo frontend/css/style.css chứa đầy đủ định kiểu và animation mở popup."""
        with open(self.css_path, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn(".capy-chat-backdrop", css)
        self.assertIn(".capy-chat-dialog", css)
        self.assertIn("@keyframes popFromCapy", css)
        self.assertIn(".capy-chip", css)
        self.assertIn(".capy-chip.is-editing", css)
        self.assertIn(".capy-chip-inline-editor", css)
        self.assertIn(".capy-chip-confirm-btn", css)
        self.assertIn(".capy-chip-cancel-btn", css)
        self.assertIn(".capy-action-card", css)
        self.assertIn(".action-card-btn", css)
        self.assertIn(".capy-typing-indicator", css)
        self.assertIn("@media (max-width: 768px)", css)

    def test_capybara_chat_component_js(self):
        """Đảm bảo module capybara_chat.js tồn tại và cung cấp đầy đủ các hàm xử lý."""
        self.assertTrue(os.path.exists(self.chat_js_path))
        with open(self.chat_js_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("export const CapybaraChat", js)
        self.assertIn("init()", js)
        self.assertIn("open()", js)
        self.assertIn("close()", js)
        self.assertIn("renderChips()", js)
        self.assertIn("enableInlineChipEdit", js)
        self.assertIn("sendMessage", js)
        self.assertIn("loadMessages", js)
        self.assertIn("saveMessages", js)
        self.assertIn("clearHistory", js)
        self.assertIn("createActionCardElement", js)
        self.assertIn("createCapyAvatarElement", js)
        self.assertIn("resolveCapyMood", js)
        self.assertIn("playSuccessChime", js)
        self.assertIn("fitsense_capy_chat_history", js)

    def test_capybara_companion_triggers_chat(self):
        """Đảm bảo khi click vào Capybara avatar, module sẽ kích hoạt mở chat popup."""
        with open(self.companion_js_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("CapybaraChat?.open()", js)
        self.assertIn("this.hideBubble(true)", js)

    def test_api_js_has_chat_endpoint(self):
        """Đảm bảo frontend/js/api.js hỗ trợ gọi endpoint /api/capybara/chat."""
        with open(self.api_js_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("/api/capybara/chat", js)

    def test_app_js_initializes_chat(self):
        """Đảm bảo frontend/js/app.js import và khởi tạo CapybaraChat."""
        with open(self.app_js_path, "r", encoding="utf-8") as f:
            js = f.read()

        self.assertIn("CapybaraChat", js)
        self.assertIn("CapybaraChat.init()", js)

    def test_self_initialization_and_import_query(self):
        """Kiểm tra cơ chế self-initialization trong open() và khớp query param ?v=3.0.0."""
        with open(self.chat_js_path, "r", encoding="utf-8") as f:
            chat_js = f.read()
        with open(self.companion_js_path, "r", encoding="utf-8") as f:
            comp_js = f.read()

        # Self-initialization
        self.assertIn("if (!this.modal) this.init();", chat_js)
        # Consistent ?v=3.0.0 import
        self.assertIn('import("./capybara_chat.js?v=3.0.0")', comp_js)

    def test_inline_edit_escape_stop_propagation(self):
        """Kiểm tra sự kiện keydown của input inline chip editor có e.stopPropagation()."""
        with open(self.chat_js_path, "r", encoding="utf-8") as f:
            chat_js = f.read()

        self.assertIn('input.addEventListener("keydown", (e) => {', chat_js)
        self.assertIn("e.stopPropagation();", chat_js)

    def test_action_card_conditional_and_joint_mapping(self):
        """Kiểm tra Action Card chỉ tạo khi có res.action và mapping đúng bài theo khớp (SCRUM-31 + SCRUM-32)."""
        self.assertTrue(os.path.exists(self.expressions_js_path))
        self.assertTrue(os.path.exists(self.action_card_js_path))

        with open(self.chat_js_path, "r", encoding="utf-8") as f:
            chat_js = f.read()
        with open(self.expressions_js_path, "r", encoding="utf-8") as f:
            expr_js = f.read()
        with open(self.action_card_js_path, "r", encoding="utf-8") as f:
            card_js = f.read()

        # Chat delegate sang module SCRUM-32 (resolveCapyMood & normalizeActionCard)
        self.assertIn("normalizeActionCard(res)", chat_js)
        self.assertIn("resolveCapyMood(", chat_js)

        # res.intent chỉ set mood worried, không tạo Action Card ảo khi thiếu action
        self.assertIn('intent === "INJURY_REPORT"', expr_js)
        self.assertIn('return "worried";', expr_js)
        self.assertIn("if (!action) return null;", card_js)
        self.assertIn('if (action === "swap_exercise_for_injury")', card_js)

        # Mapping chi tiết theo từng khớp
        self.assertIn("wrist:", card_js)
        self.assertIn("Standard Push-up (Chống đẩy)", card_js)
        self.assertIn("Forearm Plank (Plank cẳng tay)", card_js)
        self.assertIn("shoulder:", card_js)
        self.assertIn("Pike Push-up (Đẩy vai dốc)", card_js)
        self.assertIn("Incline Push-up (Chống đẩy dốc)", card_js)
        self.assertIn("lower_back:", card_js)
        self.assertIn("Leg Raise (Nâng chân)", card_js)
        self.assertIn("Dead Bug (Bọ chết siết bụng)", card_js)
        self.assertIn("knee:", card_js)
        self.assertIn("Squat (Gánh đùi)", card_js)
        self.assertIn("Glute Bridge (Cầu mông)", card_js)


if __name__ == "__main__":
    unittest.main()