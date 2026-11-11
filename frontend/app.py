import streamlit as st

from services.api_client import (
    APIError,
    API_BASE_URL,
    check_health,
    register_account,
    login_account,
    get_current_user,
    ask_contract_question,
    get_qa_history,
    assess_contract_risk,
    get_risk_history,
    get_contracts,
    upload_contract,
    delete_contract,
    activate_contract,
)


# =========================================================
# 1. CẤU HÌNH GIAO DIỆN
# =========================================================

st.set_page_config(
    page_title="Contract AI Assistant",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp {
            background-color: #f7f8fa;
        }

        .block-container {
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }

        .brand-title {
            font-size: 1.55rem;
            font-weight: 750;
            color: #172033;
            letter-spacing: -0.5px;
        }

        .muted-text {
            color: #6b7280;
            font-size: 0.95rem;
        }

        .auth-heading {
            text-align: center;
            color: #172033;
            font-size: 2rem;
            font-weight: 750;
            letter-spacing: -0.7px;
        }

        .auth-description {
            text-align: center;
            color: #6b7280;
            margin-bottom: 1.5rem;
        }

        .section-title {
            font-size: 1.7rem;
            font-weight: 700;
            color: #172033;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 1rem;
        }

        div[data-testid="stForm"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 1.25rem;
        }

        .footer-note {
            color: #6b7280;
            font-size: 0.82rem;
            text-align: center;
            margin-top: 1.5rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 2. KHỞI TẠO SESSION STATE
# =========================================================

def initialize_state():
    defaults = {
        "access_token": None,
        "user": None,
        "auth_page": "login",
        "selected_menu": "Tổng quan",
        "selected_contract_id": None,
        "chat_messages": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()


# =========================================================
# 3. HÀM TIỆN ÍCH
# =========================================================

def show_error(error):
    st.error(str(error))


def extract_list(data, *possible_keys):
    """Lấy danh sách từ các kiểu response JSON thường gặp."""

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in possible_keys:
            value = data.get(key)

            if isinstance(value, list):
                return value

    return []


def display_contract_name(contract):
    if not isinstance(contract, dict):
        return str(contract)

    return (
        contract.get("file_name")
        or contract.get("filename")
        or contract.get("name")
        or str(contract.get("id", "Hợp đồng"))
    )


def logout():
    """Xóa dữ liệu phiên ở frontend."""

    st.session_state.access_token = None
    st.session_state.user = None
    st.session_state.auth_page = "login"
    st.session_state.selected_menu = "Tổng quan"
    st.session_state.selected_contract_id = None
    st.session_state.chat_messages = []

    st.rerun()


def get_user_name():
    user = st.session_state.user or {}

    if isinstance(user, dict):
        return (
        user.get("username")
        or user.get("full_name")
        or user.get("name")
        or user.get("email")
        or "Người dùng"
    )

    return "Người dùng"


def load_user_contracts():
    """Lấy danh sách hợp đồng từ backend."""

    data = get_contracts(st.session_state.access_token)

    return extract_list(
        data,
        "contracts",
        "items",
        "data"
    )


def show_api_error_note():
    st.caption(f"Backend API: {API_BASE_URL}")


# =========================================================
# 4. MÀN HÌNH ĐĂNG NHẬP / ĐĂNG KÝ
# =========================================================

def render_auth_page():
    # Căn biểu mẫu ra giữa màn hình
    left, center, right = st.columns(
        [1, 1.15, 1]
    )

    with center:
        st.write("")

        st.markdown(
            '<div class="auth-heading">'
            'Contract AI Assistant'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="auth-description">'
            'Trợ lý hỏi đáp và rà soát hợp đồng bằng AI'
            '</div>',
            unsafe_allow_html=True,
        )

        st.write("")

        if st.session_state.auth_page == "login":
            render_login_form()
        else:
            render_register_form()

        st.markdown(
            """
            <div class="footer-note">
                Hệ thống hỗ trợ tham khảo thông tin pháp lý.
                Kết quả không thay thế tư vấn của luật sư.
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_login_form():
    st.subheader("Đăng nhập")

    st.write(
        "Đăng nhập để tiếp tục sử dụng hệ thống."
    )

    with st.form("login_form"):
        email = st.text_input(
            "Email",
            placeholder="name@example.com",
        )

        password = st.text_input(
            "Mật khẩu",
            type="password",
            placeholder="Nhập mật khẩu",
        )

        submitted = st.form_submit_button(
            "Đăng nhập",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not email.strip() or not password:
            st.warning(
                "Vui lòng nhập email và mật khẩu."
            )
        else:
            with st.spinner("Đang xác thực tài khoản..."):
                try:
                    result = login_account(
                        email=email.strip(),
                        password=password,
                    )

                    # FastAPI cần trả access_token khi đăng nhập thành công.
                    token = result.get("access_token")

                    if not token:
                        st.error(
                            "API đăng nhập chưa trả về access_token. "
                            "Hãy kiểm tra response của FastAPI."
                        )
                        return

                    # Token được cấp bởi backend, không tự tạo ở frontend.
                    current_user = get_current_user(token)
 
                    # Chỉ lưu phiên sau khi xác minh thành công.
                    st.session_state.access_token = token
                    st.session_state.user = current_user.get(
                        "user",
                        current_user,
                    )
                    st.session_state.selected_menu = "Tổng quan"

                    st.success("Đăng nhập thành công.")
                    st.rerun()

                except APIError as error:
                    if error.status_code == 401:
                        st.session_state.access_token = None
                        st.session_state.user = None

                    show_error(error)

    st.write("")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.caption("Chưa có tài khoản?")

    with col2:
        if st.button(
            "Đăng ký ngay",
            use_container_width=True,
        ):
            st.session_state.auth_page = "register"
            st.rerun()

    show_api_error_note()


def render_register_form():
    st.subheader("Tạo tài khoản")

    st.write(
        "Điền thông tin để đăng ký tài khoản mới."
    )

    with st.form("register_form"):
        username = st.text_input(
            "Tên đăng nhập",
            placeholder="Nguyễn Văn A",
        )

        email = st.text_input(
            "Email",
            placeholder="name@example.com",
        )

        password = st.text_input(
            "Mật khẩu",
            type="password",
            placeholder="Tạo mật khẩu",
        )

        confirm_password = st.text_input(
            "Xác nhận mật khẩu",
            type="password",
            placeholder="Nhập lại mật khẩu",
        )

        submitted = st.form_submit_button(
            "Tạo tài khoản",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not username.strip():
            st.warning("Vui lòng nhập họ và tên.")

        elif not email.strip():
            st.warning("Vui lòng nhập email.")

        elif not password:
            st.warning("Vui lòng nhập mật khẩu.")

        elif len(password) < 8:
            st.warning(
                "Mật khẩu cần có ít nhất 8 ký tự."
            )

        elif password != confirm_password:
            st.warning(
                "Mật khẩu xác nhận không khớp."
            )

        else:
            with st.spinner("Đang tạo tài khoản..."):
                try:
                    register_account(
                        username=username.strip(),
                        email=email.strip(),
                        password=password,
                    )

                    st.success(
                        "Đăng ký thành công. "
                        "Bạn có thể đăng nhập bằng tài khoản vừa tạo."
                    )

                    st.session_state.auth_page = "login"
                    st.rerun()

                except APIError as error:
                    show_error(error)

    st.write("")

    if st.button(
        "← Quay lại đăng nhập",
        use_container_width=True,
    ):
        st.session_state.auth_page = "login"
        st.rerun()

    show_api_error_note()


# =========================================================
# 5. SIDEBAR SAU KHI ĐĂNG NHẬP
# =========================================================

MENU_ITEMS = [
    "Tổng quan",
    "Hỏi đáp hợp đồng",
    "Đánh giá rủi ro",
    "Lịch sử hội thoại",
    "Lịch sử đánh giá rủi ro",
    "Quản lý hợp đồng",
    "Tài khoản của tôi",
]


def render_sidebar():
    with st.sidebar:
        st.markdown(
            '<div class="brand-title">'
            '⚖️ Contract AI'
            '</div>',
            unsafe_allow_html=True,
        )

        st.caption("Trợ lý pháp lý thông minh")

        st.divider()

        st.write(f"Xin chào, **{get_user_name()}**")

        selected = st.radio(
            "Điều hướng",
            MENU_ITEMS,
            key="selected_menu",
            label_visibility="collapsed",
        )

        st.divider()

        if st.button(
            "Đăng xuất",
            use_container_width=True,
        ):
            logout()

        try:
            check_health()
            st.caption("● Backend đang hoạt động")
        except APIError:
            st.caption("○ Không kết nối được backend")

    return selected


# =========================================================
# 6. TRANG TỔNG QUAN
# =========================================================

def render_dashboard():
    st.markdown(
        '<div class="section-title">Tổng quan</div>',
        unsafe_allow_html=True,
    )

    st.write(
        "Chào mừng bạn đến với Contract AI Assistant."
    )

    st.write(
        "Chọn một chức năng bên dưới để bắt đầu làm việc "
        "với hợp đồng."
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            st.subheader("💬 Hỏi đáp hợp đồng")

            st.write(
                "Đặt câu hỏi về điều khoản, nghĩa vụ, quyền lợi "
                "và nội dung hợp đồng."
            )

            if st.button(
                "Mở hỏi đáp",
                key="go_qa",
                use_container_width=True,
            ):
                st.session_state.selected_menu = "Hỏi đáp hợp đồng"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("🔎 Đánh giá rủi ro")

            st.write(
                "Phân tích các điều khoản có dấu hiệu rủi ro, "
                "căn cứ pháp luật và khuyến nghị."
            )

            if st.button(
                "Mở đánh giá",
                key="go_risk",
                use_container_width=True,
            ):
                st.session_state.selected_menu = "Đánh giá rủi ro"
                st.rerun()

    st.divider()

    st.subheader("Quy trình sử dụng")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("### 01")
        st.markdown("**Cung cấp hợp đồng**")
        st.caption("Tải lên và quản lý tài liệu.")

    with c2:
        st.markdown("### 02")
        st.markdown("**Phân tích nội dung**")
        st.caption("Hỏi đáp hoặc đánh giá rủi ro.")

    with c3:
        st.markdown("### 03")
        st.markdown("**Xem kết quả**")
        st.caption("Đọc bằng chứng và khuyến nghị.")

    st.info(
        "Kết quả đánh giá phụ thuộc vào nội dung hợp đồng, "
        "căn cứ pháp luật truy xuất được và kết quả kiểm chứng."
    )


# =========================================================
# 7. HỎI ĐÁP HỢP ĐỒNG
# =========================================================

def render_qa_page():
    st.title("Hỏi đáp hợp đồng")

    st.write(
        "Đặt câu hỏi về hợp đồng đã được tải lên hệ thống."
    )

    try:
        contracts = load_user_contracts()
        

    except APIError as error:
        show_error(error)
        return

    if not contracts:
        st.info(
            "Bạn chưa có hợp đồng nào. "
            "Hãy vào mục Quản lý hợp đồng để tải tài liệu lên."
        )
        return

    contract_options = {
        display_contract_name(contract): contract
        for contract in contracts
        if isinstance(contract, dict)
        and contract.get("id") is not None
    }

    if not contract_options:
        st.warning(
            "API danh sách hợp đồng cần trả về trường id "
            "và tên tệp hoặc tên hợp đồng."
        )
        return

    selected_name = st.selectbox(
        "Chọn hợp đồng",
        list(contract_options.keys()),
    )

    selected_contract = contract_options[selected_name]
    contract_id = selected_contract["id"]

    st.divider()

    # Hiển thị hội thoại trong phiên hiện tại.
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input(
        "Nhập câu hỏi về hợp đồng..."
    )

    if question:
        st.session_state.chat_messages.append({
            "role": "user",
            "content": question,
        })

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Đang phân tích câu hỏi..."):
                try:
                    result = ask_contract_question(
                        token=st.session_state.access_token,
                        question=question,
                        contract_id=str(contract_id),
                    )

                    answer = result.get(
                        "answer",
                        result.get(
                            "response",
                            "Backend chưa trả về câu trả lời."
                        )
                    )

                    st.markdown(answer)

                    sources = result.get(
                        "sources",
                        result.get("citations", []),
                    )

                    if sources:
                        with st.expander("Căn cứ và nguồn tham khảo"):
                            # Tìm kết quả có rank cao nhất
                            top_source = min(
                                sources,
                                key=lambda source: source.get("rank", float("inf"))
                                if isinstance(source, dict)
                                else float("inf"),
                            )

                            if isinstance(top_source, dict):
                                article = top_source.get("article")
                                hierarchy_path = top_source.get("hierarchy_path")

                                if article:
                                    st.write(f"**Article:** {article}")

                                if hierarchy_path:
                                    st.write(f"**Hierarchy path:** {hierarchy_path}")

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": answer,
                    })

                except APIError as error:
                    show_error(error)


# =========================================================
# 8. ĐÁNH GIÁ RỦI RO
# =========================================================

def render_risk_page():
    st.title("Đánh giá rủi ro pháp lý")

    st.write(
        "Chọn hợp đồng đã tải lên để bắt đầu đánh giá."
    )

    try:
        contracts = load_user_contracts()

    except APIError as error:
        show_error(error)
        return

    if not contracts:
        st.info(
            "Bạn chưa có hợp đồng. "
            "Hãy tải hợp đồng lên trước khi đánh giá."
        )
        return

    contract_options = {
        display_contract_name(contract): contract
        for contract in contracts
        if isinstance(contract, dict)
        and contract.get("id") is not None
    }

    if not contract_options:
        st.warning(
            "API danh sách hợp đồng cần trả về id và tên hợp đồng."
        )
        return

    selected_name = st.selectbox(
        "Hợp đồng cần đánh giá",
        list(contract_options.keys()),
    )

    contract = contract_options[selected_name]

    st.caption(f"Hợp đồng: {selected_name}")

    if st.button(
        "Bắt đầu đánh giá",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Đang đánh giá rủi ro..."):
            try:
                result = assess_contract_risk(
                    token=st.session_state.access_token,
                    contract_id=str(contract["id"]),
                )

                st.session_state["last_risk_result"] = result

            except APIError as error:
                show_error(error)

    result = st.session_state.get("last_risk_result")

    if not result:
        return

    st.divider()
    st.subheader("Kết quả tổng quan")

    level = str(
        result.get("risk_level", "unknown")
    ).lower()

    labels = {
        "low": "Thấp",
        "medium": "Trung bình",
        "high": "Cao",
        "unknown": "Chưa xác định",
    }

    st.metric(
        "Mức độ rủi ro",
        labels.get(level, level.title()),
    )

    st.write(
        result.get(
            "summary",
            "Backend chưa trả về phần tóm tắt.",
        )
    )

    issues = extract_list(
        result,
        "issues",
        "verified_issues",
        "findings",
    )

    st.subheader(f"Các vấn đề được ghi nhận ({len(issues)})")

    if not issues:
        st.write(
            "Không có vấn đề nào được trả về trong kết quả này. "
            "Điều đó không tự động chứng minh hợp đồng hoàn toàn "
            "không có rủi ro pháp lý."
        )

    for index, issue in enumerate(issues, start=1):
        if not isinstance(issue, dict):
            st.write(issue)
            continue

        title = (
            issue.get("risk_type")
            or issue.get("title")
            or f"Vấn đề {index}"
        )

        severity = issue.get(
            "severity",
            "Chưa xác định",
        )

        with st.expander(
            f"{index}. {title} — {severity}",
            expanded=True,
        ):
            st.write(
                issue.get(
                    "description",
                    issue.get("analysis", "Chưa có mô tả."),
                )
            )

            legal_basis = (
                issue.get("legal_basis")
                or issue.get("legal_references")
                or issue.get("legal_reference")
            )

            if legal_basis:
                st.markdown("**Căn cứ pháp luật**")
                st.write(legal_basis)

            evidence = issue.get(
                "evidence",
                issue.get("evidence_text"),
            )

            if evidence:
                st.markdown("**Bằng chứng đối chiếu**")
                st.write(evidence)

            recommendation = issue.get("recommendation")

            if recommendation:
                st.markdown("**Khuyến nghị**")
                st.write(recommendation)

    recommendations = extract_list(
        result,
        "recommendations",
    )

    if recommendations:
        st.subheader("Khuyến nghị tổng thể")

        for recommendation in recommendations:
            st.markdown(f"- {recommendation}")


# =========================================================
# 9. LỊCH SỬ HỘI THOẠI
# =========================================================

def render_qa_history_page():
    st.title("Lịch sử hội thoại")

    try:
        data = get_qa_history(
            st.session_state.access_token
        )

        history = extract_list(
            data,
            "history",
            "conversations",
            "items",
            "data",
        )

    except APIError as error:
        show_error(error)
        return

    if not history:
        st.info("Chưa có lịch sử hội thoại.")
        return

    for index, item in enumerate(history, start=1):
        if not isinstance(item, dict):
            st.write(item)
            continue

        title = (
            item.get("title")
            or item.get("question")
            or f"Hội thoại {index}"
        )

        with st.expander(title):
            st.caption(
                item.get("created_at", "Không có thời gian")
            )

            if item.get("question"):
                st.markdown("**Câu hỏi**")
                st.write(item["question"])

            if item.get("answer"):
                st.markdown("**Câu trả lời**")
                st.write(item["answer"])

            if item.get("messages"):
                for message in item["messages"]:
                    if isinstance(message, dict):
                        role = message.get("role", "message")
                        content = message.get("content", "")
                        st.markdown(f"**{role}:** {content}")


# =========================================================
# 10. LỊCH SỬ ĐÁNH GIÁ RỦI RO
# =========================================================

def render_risk_history_page():
    st.title("Lịch sử đánh giá rủi ro")

    try:
        data = get_risk_history(
            st.session_state.access_token
        )

        history = extract_list(
            data,
            "history",
            "assessments",
            "items",
            "data",
        )

    except APIError as error:
        show_error(error)
        return

    if not history:
        st.info("Chưa có lịch sử đánh giá rủi ro.")
        return

    for index, item in enumerate(history, start=1):
        if not isinstance(item, dict):
            st.write(item)
            continue

        title = (
            item.get("contract_name")
            or item.get("title")
            or f"Lần đánh giá {index}"
        )

        with st.expander(title):
            st.caption(
                item.get("created_at", "Không có thời gian")
            )

            level = str(
                item.get("risk_level", "unknown")
            ).lower()

            labels = {
                "low": "Thấp",
                "medium": "Trung bình",
                "high": "Cao",
                "unknown": "Chưa xác định",
            }

            st.write(
                "Mức độ rủi ro: "
                + labels.get(level, level.title())
            )

            st.write(
                item.get(
                    "summary",
                    "Không có phần tóm tắt.",
                )
            )


# =========================================================
# 11. QUẢN LÝ HỢP ĐỒNG
# =========================================================

def render_contract_management_page():
    st.title("Quản lý hợp đồng")

    st.write(
        "Tải lên, xem danh sách và quản lý hợp đồng "
        "được lưu trong tài khoản của bạn."
    )

    st.subheader("Tải hợp đồng lên")

    uploaded_file = st.file_uploader(
        "Chọn tệp hợp đồng",
        type=["pdf", "docx", "txt"],
        help="Chỉ tải lên tài liệu bạn có quyền cung cấp.",
        key="contract_upload",
    )

    if uploaded_file:
        st.caption(
            f"Tệp đã chọn: {uploaded_file.name} "
            f"({uploaded_file.size:,} byte)"
        )

        if st.button(
            "Tải lên hệ thống",
            type="primary",
        ):
            with st.spinner("Đang tải hợp đồng lên..."):
                try:
                    result = upload_contract(
                        token=st.session_state.access_token,
                        uploaded_file=uploaded_file,
                    )

                    st.success(
                        result.get(
                            "message",
                            "API đã tiếp nhận yêu cầu tải lên.",
                        )
                    )

                    st.rerun()

                except APIError as error:
                    show_error(error)

    st.divider()
    st.subheader("Hợp đồng đã tải lên")

    try:
        contracts = load_user_contracts()
        st.write("DEBUG CONTRACTS:", contracts)

    except APIError as error:
        show_error(error)
        return

    if not contracts:
        st.info("Bạn chưa tải hợp đồng nào lên hệ thống.")
        return

    for contract in contracts:
        if not isinstance(contract, dict):
            st.write(contract)
            continue

        contract_id = contract.get("id")
        name = display_contract_name(contract)

        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 2, 1])

            with col1:
                st.markdown(f"**📄 {name}**")

                if contract.get("created_at"):
                    st.caption(
                        f"Ngày tải lên: {contract['created_at']}"
                    )

                if contract.get("status"):
                    st.caption(
                        f"Trạng thái: {contract['status']}"
                    )

            with col2:
                if contract.get("is_active"):
                    st.success("Đang sử dụng")
                elif contract_id is not None:
                    if st.button(
                        "Chọn hợp đồng",
                        key=f"activate_contract_{contract_id}",
                    ):
                        try:
                            activate_contract(
                                token=st.session_state.access_token,
                                contract_id=str(contract_id),
                            )

                            st.success(
                                "Đã chọn hợp đồng hiện hành."
                            )
                            st.rerun()

                        except APIError as error:
                            show_error(error)

            with col3:
                if contract_id is not None:
                    if st.button(
                        "Xóa",
                        key=f"delete_contract_{contract_id}",
                    ):
                        st.session_state[
                            "confirm_delete_contract_id"
                        ] = str(contract_id)


    # Xác nhận trước khi xóa tài liệu.
    delete_id = st.session_state.get(
        "confirm_delete_contract_id"
    )

    if delete_id is not None:
        st.warning(
            "Bạn có chắc muốn xóa hợp đồng này? "
            "Thao tác chỉ thực hiện sau khi bạn xác nhận."
        )

        yes_col, no_col = st.columns(2)

        with yes_col:
            if st.button(
                "Xác nhận xóa",
                type="primary",
            ):
                try:
                    delete_contract(
                        token=st.session_state.access_token,
                        contract_id=delete_id,
                    )

                    st.session_state[
                        "confirm_delete_contract_id"
                    ] = None

                    st.success("Đã gửi yêu cầu xóa hợp đồng.")
                    st.rerun()

                except APIError as error:
                    show_error(error)

        with no_col:
            if st.button("Hủy xóa"):
                st.session_state[
                    "confirm_delete_contract_id"
                ] = None
                st.rerun()


# =========================================================
# 12. TÀI KHOẢN CỦA TÔI
# =========================================================

def render_account_page():
    st.title("Tài khoản của tôi")

    try:
        data = get_current_user(
            st.session_state.access_token
        )

        user = data.get("user", data)
        st.session_state.user = user

    except APIError as error:
        show_error(error)
        return

    if not isinstance(user, dict):
        st.info("Backend chưa trả về thông tin tài khoản.")
        return

    with st.container(border=True):
        st.subheader("Thông tin tài khoản")

        st.text_input(
            "Tên đăng nhập",
            value=user.get("username", ""),
            disabled=True,
        )

        st.text_input(
            "Email",
            value=user.get("email", ""),
            disabled=True,
        )

        if user.get("created_at"):
            st.caption(
                f"Ngày tạo tài khoản: {user['created_at']}"
            )

    st.info(
        "Chức năng đổi mật khẩu và cập nhật hồ sơ sẽ cần "
        "các endpoint tương ứng ở backend FastAPI."
    )


# =========================================================
# 13. ĐIỀU PHỐI ỨNG DỤNG
# =========================================================

def main():
    token = st.session_state.access_token

    # Chưa đăng nhập: hiện giao diện đăng nhập.
    if not token:
        render_auth_page()
        return

    # Xác minh phiên đăng nhập với backend.
    try:
        result = get_current_user(token)

        st.session_state.user = result.get(
            "user",
            result,
        )

    except APIError as error:
        if error.status_code == 401:
            st.session_state.access_token = None
            st.session_state.user = None
            st.session_state.auth_page = "login"

            st.warning(
                "Phiên đăng nhập không hợp lệ hoặc đã hết hạn. "
                "Vui lòng đăng nhập lại."
            )

            render_auth_page()
            return

        show_error(error)

        if st.button(
            "Thử xác minh phiên lại",
            type="primary",
        ):
            st.rerun()

        return

    # Phiên hợp lệ: hiển thị sidebar.
    selected_menu = render_sidebar()

    # Điều hướng đến trang tương ứng.
    if selected_menu == "Tổng quan":
        render_dashboard()

    elif selected_menu == "Hỏi đáp hợp đồng":
        render_qa_page()

    elif selected_menu == "Đánh giá rủi ro":
        render_risk_page()

    elif selected_menu == "Lịch sử hội thoại":
        render_qa_history_page()

    elif selected_menu == "Lịch sử đánh giá rủi ro":
        render_risk_history_page()

    elif selected_menu == "Quản lý hợp đồng":
        render_contract_management_page()

    elif selected_menu == "Tài khoản của tôi":
        render_account_page()


main()
