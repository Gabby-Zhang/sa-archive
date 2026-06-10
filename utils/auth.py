import streamlit as st

_MAX_ATTEMPTS = 5  # 单会话最多尝试次数，超过后本会话锁定


def admin_sidebar():
    """在侧边栏显示管理员登录，所有页面都可以调用"""
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False
    if "_login_attempts" not in st.session_state:
        st.session_state._login_attempts = 0

    with st.sidebar:
        st.divider()
        if not st.session_state.is_admin:
            with st.expander("🔐 管理员登录"):
                if st.session_state._login_attempts >= _MAX_ATTEMPTS:
                    st.error("尝试次数过多，请刷新页面后再试")
                    return
                pwd = st.text_input("密码", type="password", key="admin_pwd_sidebar")
                if st.button("登录", key="admin_login_btn"):
                    admin_pwd = st.secrets.get("ADMIN_PASSWORD", "")
                    # admin_pwd 必须非空：secret 未配置时拒绝一切登录，而不是空密码放行
                    if admin_pwd and pwd == admin_pwd:
                        st.session_state.is_admin = True
                        st.session_state._login_attempts = 0
                        st.rerun()
                    else:
                        st.session_state._login_attempts += 1
                        st.error("密码错误")
        else:
            st.success("✅ 管理员模式")
            if st.button("退出登录", key="admin_logout_btn"):
                st.session_state.is_admin = False
                st.rerun()
