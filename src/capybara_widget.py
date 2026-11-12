"""Module Trợ lý Thú cưng Capybara Đồng hành (Capybara Workout Companion).

Hiển thị chú chuột túi Capybara nổi ở góc màn hình dưới dạng pop-up tự động:
- Vị trí: Cố định ở góc dưới cùng bên phải màn hình (Bottom-Right Floating Pop-up).
- Bố cục: [ Bong bóng lời thoại tự chạy 💬 ]  [ Chú Capybara 🦫 ]
- Tự động nhận biết trạng thái tập luyện hôm nay:
    + Chưa tập: Mặt buồn 🥺, nhắc nhở dễ thương, giục giã giữ chuỗi rèn luyện, chấm trạng thái đỏ.
    + Đã tập xong: Mặt vui hớn hở 🥰, đội trái cam Onsen 🍊, khen ngợi và chúc mừng, chấm trạng thái xanh.
- Tự động xoay vòng câu thoại mượt mà bằng CSS Keyframe Animation (cứ mỗi 8 giây chuyển sang câu mới).
- Tối giản tối đa: Đã loại bỏ hoàn toàn các thanh tiêu đề và nút bấm thủ công.
"""

import html
import random
import textwrap
import streamlit as st

# Vector SVG Capybara Buồn / Nhắc nhở (Chưa tập hôm nay 🥺 💧)
CAPY_SVG_SAD = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="86" height="86">
  <!-- Thân & Đầu Capybara -->
  <ellipse cx="60" cy="72" rx="42" ry="34" fill="#A47148"/>
  <!-- Tai trái & phải hơi cụp -->
  <ellipse cx="30" cy="48" rx="9" ry="12" fill="#7D4B27" transform="rotate(-30 30 48)"/>
  <ellipse cx="30" cy="48" rx="5" ry="7" fill="#C99468" transform="rotate(-30 30 48)"/>
  <ellipse cx="90" cy="48" rx="9" ry="12" fill="#7D4B27" transform="rotate(30 90 48)"/>
  <ellipse cx="90" cy="48" rx="5" ry="7" fill="#C99468" transform="rotate(30 90 48)"/>
  <!-- Băng đô mồ hôi tập luyện trễ xuống -->
  <rect x="34" y="38" width="52" height="7" rx="3.5" fill="#64748B" opacity="0.85"/>
  <line x1="34" y1="41.5" x2="86" y2="41.5" stroke="#94A3B8" stroke-width="1.5"/>
  <!-- Mõm Capybara vuông đặc trưng -->
  <path d="M 40 68 C 40 56, 80 56, 80 68 C 80 82, 40 82, 40 68 Z" fill="#885532"/>
  <!-- Mũi & Lỗ mũi -->
  <ellipse cx="54" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <ellipse cx="66" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <!-- Mắt to tròn ủ rũ / buồn thiu -->
  <ellipse cx="44" cy="54" rx="5.5" ry="7" fill="#2B1A0E"/>
  <circle cx="43" cy="52" r="2.2" fill="#FFFFFF"/>
  <circle cx="46.5" cy="56" r="1.1" fill="#FFFFFF"/>
  <ellipse cx="76" cy="54" rx="5.5" ry="7" fill="#2B1A0E"/>
  <circle cx="75" cy="52" r="2.2" fill="#FFFFFF"/>
  <circle cx="78.5" cy="56" r="1.1" fill="#FFFFFF"/>
  <!-- Lông mày cụp buồn -->
  <path d="M 37 45 Q 43 42 49 46" stroke="#4A2810" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <path d="M 83 45 Q 77 42 71 46" stroke="#4A2810" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <!-- Miệng mếu nhẹ -->
  <path d="M 55 76 Q 60 72 65 76" stroke="#4A2810" stroke-width="2.2" fill="none" stroke-linecap="round"/>
  <!-- Giọt nước mắt buồn long lanh -->
  <path d="M 84 62 C 81 66, 81 70, 84 72 C 87 70, 87 66, 84 62 Z" fill="#38BDF8"/>
  <circle cx="83.5" cy="68" r="0.8" fill="#FFFFFF"/>
  <!-- Hai bàn chân bấu nhẹ -->
  <ellipse cx="44" cy="98" rx="9" ry="6" fill="#7D4B27"/>
  <ellipse cx="76" cy="98" rx="9" ry="6" fill="#7D4B27"/>
</svg>"""

# Vector SVG Capybara Vui vẻ / Ăn mừng (Đã tập xong 🥰 🍊 ✨)
CAPY_SVG_HAPPY = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="86" height="86">
  <!-- Thân & Đầu Capybara ấm áp -->
  <ellipse cx="60" cy="72" rx="42" ry="34" fill="#B58A63"/>
  <!-- Tai vểnh hào hứng -->
  <ellipse cx="30" cy="46" rx="9" ry="12" fill="#885532" transform="rotate(-15 30 46)"/>
  <ellipse cx="30" cy="46" rx="5" ry="7" fill="#DDA15E" transform="rotate(-15 30 46)"/>
  <ellipse cx="90" cy="46" rx="9" ry="12" fill="#885532" transform="rotate(15 90 46)"/>
  <ellipse cx="90" cy="46" rx="5" ry="7" fill="#DDA15E" transform="rotate(15 90 46)"/>
  <!-- Mõm Capybara -->
  <path d="M 40 68 C 40 56, 80 56, 80 68 C 80 82, 40 82, 40 68 Z" fill="#885532"/>
  <!-- Mũi hếch kiêu hãnh -->
  <ellipse cx="54" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <ellipse cx="66" cy="65" rx="3.2" ry="2.2" fill="#3D1E0B"/>
  <!-- Mắt cười tít hình trăng khuyết (^ ^) -->
  <path d="M 38 54 Q 44 46 50 54" stroke="#2B1A0E" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <path d="M 70 54 Q 76 46 82 54" stroke="#2B1A0E" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <!-- Má hồng hào phúng phính -->
  <ellipse cx="36" cy="61" rx="7.5" ry="4.5" fill="#FB7185" opacity="0.75"/>
  <ellipse cx="84" cy="61" rx="7.5" ry="4.5" fill="#FB7185" opacity="0.75"/>
  <!-- Nụ cười tươi hạnh phúc -->
  <path d="M 54 73 Q 60 79 66 73" stroke="#4A2810" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  <!-- Trái cam Onsen trứ danh trên đỉnh đầu -->
  <circle cx="60" cy="28" r="11" fill="#EA580C"/>
  <circle cx="59" cy="26" r="9.5" fill="#F97316"/>
  <circle cx="56" cy="23" r="3" fill="#FDBA74" opacity="0.6"/>
  <path d="M 60 17 Q 67 13 69 16 Q 66 20 60 17 Z" fill="#22C55E"/>
  <ellipse cx="60" cy="17" rx="1.5" ry="1" fill="#15803D"/>
  <!-- Ngôi sao lấp lánh xung quanh -->
  <path d="M 20 25 L 22 30 L 27 32 L 22 34 L 20 39 L 18 34 L 13 32 L 18 30 Z" fill="#FACC15"/>
  <path d="M 100 22 L 102 26 L 106 27 L 102 28 L 100 32 L 98 28 L 94 27 L 98 26 Z" fill="#38BDF8"/>
  <circle cx="106" cy="40" r="1.5" fill="#FACC15"/>
  <!-- Hai bàn chân trước tươi vui -->
  <ellipse cx="44" cy="98" rx="9" ry="6" fill="#885532"/>
  <ellipse cx="76" cy="98" rx="9" ry="6" fill="#885532"/>
</svg>"""

# Danh sách lời thoại nhắc nhở khi chưa tập (Buồn 🥺 / Ngắn gọn <= 2 dòng)
SAD_QUOTES = [
    "Hôm nay bạn chưa tập nè, cùng khởi động nhé! 🥺",
    "Chưa tập bài nào đó, làm vài set nhẹ thôi! 🦫",
    "Squat 10 phút với Cappy cho tỉnh táo nha! 🔥",
    "Đừng bỏ chuỗi Streak, bắt đầu ngay bạn ơi! 💪",
    "Thảm tập sẵn sàng rồi, chỉ chờ bạn thôi đó! 🏃",
    "Ngồi lâu mỏi lưng lắm, giãn cơ một chút nào! 🤸",
]

# Danh sách lời thoại khen ngợi khi đã tập xong (Vui tươi 🥰 / Ngắn gọn <= 2 dòng)
HAPPY_QUOTES = [
    "Giỏi quá bạn ơi! Đã hoàn thành mục tiêu rồi! 🎉",
    "Đỉnh chóp! Cơ bắp đang hồi phục rất tốt đó! 💪",
    "Tập xong nhớ uống đủ nước và nạp protein nhé! 🥛",
    "Tự hào về bạn quá! Nghỉ ngơi thật tốt nha! 🌿",
    "Chuỗi Streak đang cháy rực rỡ luôn đó bạn! 🔥",
    "Hôm nay bạn đã chiến thắng sự lười biếng rồi! 🌟",
]

# Danh sách lời thoại chào mừng ở giao diện đăng nhập (<= 2 dòng)
WELCOME_QUOTES = [
    "Xin chào! Chào mừng bạn đến với FitSense! 🦫✨",
    "Chào bạn! Tớ là CappyHeo, trợ lý FitSense! 🍊",
    "Đăng nhập để AI lên lịch tập riêng cho bạn! ⚡",
    "Cùng bạn chinh phục vóc dáng mới tại FitSense! 💪",
    "Sẵn sàng cho buổi tập thông minh chưa bạn? 🚀",
    "Chúc bạn ngày mới tập luyện tràn năng lượng! 🌟",
]

# Ngân hàng câu thoại riêng theo từng mục (các mục chung đặc điểm dùng chung ngân hàng)
SECTION_QUOTES = {
    "hud": [
        "Đứng đủ khung hình để AI bắt khớp chuẩn nhé! 📸",
        "Giữ lưng thẳng, hít sâu trước khi xuống Squat! 🏋️",
        "Chậm rãi kiểm soát nhịp thở theo từng rep nha! 💨",
        "Mệt thì bấm Tạm ngưng, không cần vội đâu bạn! ⏸️",
        "Giơ tay chữ X nếu muốn kết thúc hiệp sớm nhé! 🙅",
        "Mỗi rep đúng kỹ thuật giá trị hơn rep vội đó! ✨",
    ],
    "planner_library": [
        "Bấm 'Tập ngay' để AI đưa bài vào phòng tập! 🚀",
        "Bạn có thể tải lên hoặc tự sửa lịch theo ý! 📝",
        "Chưa ưng bài nào thì chọn bài thay thế nhé! 🔄",
        "Điều chỉnh số set và thời gian nghỉ phù hợp! 💡",
        "Đọc kỹ lỗi sai thường gặp trước khi tập nha! 📖",
        "Ưu tiên kỹ thuật chuẩn trước khi tăng số rep! 💡",
    ],
    "analytics_heatmap": [
        "Nhóm cơ cam/đỏ cần nghỉ thêm trước khi tập! 🟠",
        "Cơ xanh lá đã hồi phục, sẵn sàng tập mạnh! 🟢",
        "Tập đều đặn để chuỗi Streak ngày càng dài! 🔥",
        "Xem biểu đồ tiến độ để cân bằng các nhóm cơ! 📊",
        "Ngủ đủ giấc giúp cơ bắp phục hồi nhanh hơn! 😴",
        "Kỷ lục mới sẽ đến khi bạn kiên trì mỗi tuần! 🏆",
    ],
    "profile_eval": [
        "Hãy chấm điểm RPE thật lòng để AI chỉnh tải! ⭐",
        "Nhớ cập nhật thể trạng để AI chỉnh giáo án! 📋",
        "Cơ thể mệt hay khỏe? Kể cho Cappy nghe nhé! 🦫",
        "Hoàn tất đánh giá xong nhớ uống bù nước nha! 💧",
        "Đánh giá giúp AI tối ưu lịch tuần tới cho bạn! ✨",
        "Lắng nghe cơ thể và bảo vệ khớp là số một! 💚",
    ],
}


def resolve_capy_section(current_screen: str | None, is_logged_in: bool) -> str:
    """Ánh xạ màn hình hiện tại sang nhóm ngân hàng câu thoại CappyHeo phù hợp."""
    if not is_logged_in:
        return "welcome"
    if not current_screen:
        return "default"
    screen_l = current_screen.lower()
    if "hud" in screen_l or "phòng tập" in screen_l:
        return "hud"
    if "kế hoạch" in screen_l or "lịch" in screen_l or "thư viện" in screen_l or "bài tập" in screen_l:
        return "planner_library"
    if "heatmap" in screen_l or "cơ bắp" in screen_l or "tiến độ" in screen_l or "lịch sử" in screen_l:
        return "analytics_heatmap"
    if "đánh giá" in screen_l or "hồ sơ" in screen_l:
        return "profile_eval"
    return "default"


def _select_section_quotes(
    quotes_pool: list[str],
    cache_key: tuple,
    count: int = 3,
) -> list[str]:
    """Random 3 câu trong ngân hàng mục và giữ ổn định giữa các thao tác trên cùng màn hình."""
    try:
        cache = st.session_state.get("capy_quote_cache", {})
        if isinstance(cache, dict) and cache_key in cache:
            cached = cache[cache_key]
            if isinstance(cached, list) and len(cached) == min(count, len(quotes_pool)):
                return cached
    except Exception:
        cache = None

    shuffled = list(quotes_pool)
    random.shuffle(shuffled)
    selected = shuffled[:count]

    try:
        if isinstance(cache, dict):
            cache[cache_key] = selected
            st.session_state["capy_quote_cache"] = cache
    except Exception:
        pass

    return selected


def render_capybara_companion(
    theme: str = "dark",
    has_worked_out_today: bool = False,
    user_name: str = "bạn",
    is_logged_in: bool = None,
    current_screen: str | None = None,
):
    """Render widget chú chuột túi Capybara nổi ở góc màn hình (Bottom-Right Corner Pop-up)."""
    if not st.session_state.get("show_capybara", True):
        return

    # Xác định trạng thái đăng nhập
    if is_logged_in is None:
        is_logged_in = st.session_state.get("is_logged_in", False)

    section_key = resolve_capy_section(current_screen, bool(is_logged_in))

    # 1. TRƯỜNG HỢP CHƯA ĐĂNG NHẬP (Giao diện Đăng nhập / Chào đón):
    if not is_logged_in:
        quotes_pool = WELCOME_QUOTES
        svg_content = CAPY_SVG_HAPPY
        dot_color = "#38BDF8" if theme == "dark" else "#EAB308"
        dot_rgb = "56, 189, 248" if theme == "dark" else "234, 179, 8"
        status_title = "Trạng thái: Chào mừng bạn đến với FitSense! 🍊✨"
    else:
        # 2. TRƯỜNG HỢP ĐÃ ĐĂNG NHẬP (Theo dõi luyện tập của người dùng):
        if not has_worked_out_today:
            session_history = st.session_state.get("session_history", [])
            if session_history and len(session_history) > 0:
                has_worked_out_today = True

        # Biểu cảm SVG phản ánh trạng thái tập trong ngày; câu thoại lấy theo ngân hàng mục
        if has_worked_out_today:
            svg_content = CAPY_SVG_HAPPY
            dot_color = "#22C55E"
            dot_rgb = "34, 197, 94"
            status_title = "Trạng thái: Đã hoàn thành bài tập hôm nay! 🥰"
            default_pool = HAPPY_QUOTES
        else:
            svg_content = CAPY_SVG_SAD
            dot_color = "#EF4444"
            dot_rgb = "239, 68, 68"
            status_title = "Trạng thái: Hôm nay bạn chưa tập bài nào! 🥺"
            default_pool = SAD_QUOTES

        quotes_pool = SECTION_QUOTES.get(section_key, default_pool)

    # Chọn ngẫu nhiên 3 câu thoại riêng của mục hiện tại (cache theo mục để không nhảy loạn khi bấm nút khác)
    cache_key = (section_key, bool(is_logged_in), bool(has_worked_out_today))
    selected_quotes = _select_section_quotes(quotes_pool, cache_key=cache_key, count=3)

    quote_slides_html = []
    for idx, raw_q in enumerate(selected_quotes):
        if user_name and user_name != "bạn":
            q_text = raw_q.replace("bạn ơi", f"{user_name} ơi").replace("bạn", user_name)
        else:
            q_text = raw_q
        # Sanitize HTML / Khử nhiễm XSS cho lời thoại Capybara
        safe_q_text = html.escape(q_text)
        quote_slides_html.append(f'<div class="capy-slide slide-{idx+1}">{safe_q_text}</div>')

    quotes_markup = "\n".join(quote_slides_html)

    # Màu sắc giao diện theo theme
    if theme == "light":
        bg_bubble = "#FFFFFF"
        border_bubble = "#EAB308"
        text_bubble = "#0F172A"
        shadow_bubble = "0 10px 28px rgba(234, 179, 8, 0.22), 0 4px 12px rgba(0, 0, 0, 0.08)"
        hint_close = "#94A3B8"
        hint_close_hover = "#0F172A"
    else:
        bg_bubble = "#111C2E"
        border_bubble = "#38BDF8"
        text_bubble = "#F8FAFC"
        shadow_bubble = "0 12px 32px rgba(0, 0, 0, 0.65), 0 0 20px rgba(56, 189, 248, 0.22)"
        hint_close = "#64748B"
        hint_close_hover = "#F8FAFC"

    # HTML / CSS hoàn toàn flush (không thụt lề 4 khoảng trắng) để Markdown không bao giờ tạo thẻ <pre><code>
    widget_html = textwrap.dedent(f"""
<style>
#capybara-companion-container {{
position: fixed;
bottom: 20px;
right: 24px;
z-index: 999999;
display: flex;
flex-direction: row;
align-items: flex-end;
gap: 12px;
pointer-events: none;
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}}
#capybara-companion-container * {{
pointer-events: auto;
}}
.capy-bubble-slot {{
position: relative;
animation: capyBubbleSilence 22s infinite ease-in-out;
transform-origin: bottom right;
}}
.capy-bubble {{
position: relative;
width: 300px;
max-width: min(320px, calc(100vw - 130px));
background-color: {bg_bubble};
border: 2px solid {border_bubble};
border-radius: 20px;
padding: 13px 16px;
padding-top: 16px;
box-shadow: {shadow_bubble};
color: {text_bubble};
transform-origin: bottom right;
transition: all 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
margin-bottom: 8px;
}}
/* Mũi tên chỉ ngang sang bên PHẢI trỏ trực tiếp vào chú Capybara */
.capy-bubble::after {{
content: "";
position: absolute;
right: -10px;
bottom: 22px;
width: 0;
height: 0;
border-top: 8px solid transparent;
border-bottom: 8px solid transparent;
border-left: 10px solid {border_bubble};
}}
.capy-bubble::before {{
content: "";
position: absolute;
right: -7px;
bottom: 22px;
width: 0;
height: 0;
border-top: 8px solid transparent;
border-bottom: 8px solid transparent;
border-left: 10px solid {bg_bubble};
z-index: 1;
}}
.capy-bubble-toggle {{
display: none !important;
}}
.capy-bubble-toggle:checked ~ .capy-bubble-slot {{
opacity: 0 !important;
animation: none !important;
transform: scale(0.6) translateX(24px);
pointer-events: none !important;
visibility: hidden;
max-height: 0;
width: 0;
padding: 0;
margin: 0;
border: none;
overflow: hidden;
}}
.capy-close-btn {{
position: absolute;
top: 6px;
right: 8px;
background: transparent;
border: none;
color: {hint_close};
font-size: 13px;
cursor: pointer;
padding: 2px 6px;
border-radius: 6px;
transition: all 0.15s ease;
line-height: 1;
user-select: none;
-webkit-user-select: none;
z-index: 10;
}}
.capy-close-btn:hover {{
color: {hint_close_hover};
transform: scale(1.15);
}}
/* KHUNG CHỨA CÂU THOẠI XOAY VÒNG TỰ ĐỘNG (12s hiện + 10s im lặng / câu) */
.capy-carousel-wrap {{
position: relative;
min-height: 44px;
max-height: 46px;
overflow: hidden;
display: flex;
align-items: center;
}}
.capy-slide {{
position: absolute;
top: 0;
left: 0;
right: 0;
opacity: 0;
font-size: 13.5px;
line-height: 1.4;
font-weight: 600;
color: {text_bubble};
display: -webkit-box;
-webkit-line-clamp: 2;
-webkit-box-orient: vertical;
overflow: hidden;
animation: capyRotateQuotes 66s infinite ease-in-out;
}}
.capy-slide.slide-1 {{
animation-delay: 0s;
}}
.capy-slide.slide-2 {{
animation-delay: 22s;
}}
.capy-slide.slide-3 {{
animation-delay: 44s;
}}
@keyframes capyBubbleSilence {{
0% {{
opacity: 0;
transform: translateY(6px) scale(0.95);
pointer-events: none;
}}
4.5%, 50% {{
opacity: 1;
transform: translateY(0) scale(1);
pointer-events: auto;
}}
54.5%, 99.9% {{
opacity: 0;
transform: translateY(4px) scale(0.94);
pointer-events: none;
}}
100% {{
opacity: 0;
transform: translateY(6px) scale(0.95);
pointer-events: none;
}}
}}
@keyframes capyRotateQuotes {{
0% {{
opacity: 0;
transform: translateY(6px);
}}
1.5%, 16.5% {{
opacity: 1;
transform: translateY(0);
}}
18.2%, 100% {{
opacity: 0;
transform: translateY(-6px);
}}
}}
.capy-avatar-btn {{
width: 86px;
height: 86px;
cursor: pointer;
position: relative;
display: flex;
align-items: flex-end;
justify-content: center;
transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
filter: drop-shadow(0 6px 16px rgba(0, 0, 0, 0.35));
user-select: none;
-webkit-user-select: none;
flex-shrink: 0;
}}
.capy-avatar-btn:hover {{
transform: scale(1.1) translateY(-4px);
}}
.capy-avatar-btn:active {{
transform: scale(0.95);
}}
.capy-svg-wrap {{
animation: capyGentleFloat 3.2s ease-in-out infinite;
display: flex;
align-items: center;
justify-content: center;
}}
@keyframes capyGentleFloat {{
0%, 100% {{ transform: translateY(0); }}
50% {{ transform: translateY(-6px); }}
}}
.capy-status-dot {{
position: absolute;
bottom: 6px;
right: 8px;
width: 14px;
height: 14px;
border-radius: 50%;
background-color: {dot_color};
border: 2px solid {bg_bubble};
box-shadow: 0 0 8px {dot_color};
animation: capyPulse 2s infinite;
}}
@keyframes capyPulse {{
0% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba({dot_rgb}, 0.7); }}
70% {{ transform: scale(1.1); box-shadow: 0 0 0 8px rgba({dot_rgb}, 0); }}
100% {{ transform: scale(0.95); box-shadow: 0 0 0 0 rgba({dot_rgb}, 0); }}
}}
</style>
<div id="capybara-companion-container">
<input type="checkbox" id="capy-bubble-toggle" class="capy-bubble-toggle" />
<div class="capy-bubble-slot">
<div class="capy-bubble">
<label for="capy-bubble-toggle" class="capy-close-btn" title="Thu nhỏ lời thoại">✕</label>
<div class="capy-carousel-wrap">
{quotes_markup}
</div>
</div>
</div>
<label for="capy-bubble-toggle" class="capy-avatar-btn" title="Nhấp vào chú Capybara để ẩn hoặc hiện lời thoại!">
<div class="capy-svg-wrap">
{svg_content}
</div>
<div class="capy-status-dot" title="{status_title}"></div>
</label>
</div>
""").strip()

    st.markdown(widget_html, unsafe_allow_html=True)
