import streamlit as st

def admin_sidebar():
    """在侧边栏显示管理员登录，所有页面都可以调用"""
    if "is_admin" not in st.session_state:
        st.session_state.is_admin = False

    with st.sidebar:
        st.divider()
        if not st.session_state.is_admin:
            with st.expander("🔐 管理员登录"):
                pwd = st.text_input("密码", type="password", key="admin_pwd_sidebar")
                if st.button("登录", key="admin_login_btn"):
                    if pwd == st.secrets.get("ADMIN_PASSWORD", ""):
                        st.session_state.is_admin = True
                        st.rerun()
                    else:
                        st.error("密码错误")
        else:
            st.success("✅ 管理员模式")
            if st.button("退出登录", key="admin_logout_btn"):
                st.session_state.is_admin = False
                st.rerun()
