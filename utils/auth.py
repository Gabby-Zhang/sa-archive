import streamlit as st

_MAX_ATTEMPTS = 5  # 单会话最多尝试次数，超过后本会话锁定


def _admin_accounts():
    """读取管理员账号表。

    优先用 secrets 里的 [admins.*] 多账号配置；每个账号形如：

        [admins.gabby]
        password = "xxx"
        role = "super"   # super=最终管理员，admin=普通管理员

    若没配 [admins]，回退到旧的单一 ADMIN_PASSWORD（视为超级管理员），
    保证已有部署不受影响。返回 {名字: {password, role}} 字典。
    """
    accounts = {}
    raw = st.secrets.get("admins", None)
    if raw:
        for name, info in raw.items():
            # info 可能是 dict（带 role）或纯字符串（只给了密码，默认普通管理员）
            # 密码一律转成字符串：TOML 里纯数字密码（如 password = 1626，没加引号）
            # 会被解析成整数，和登录框传来的字符串永远不相等，导致登不上
            if isinstance(info, dict):
                accounts[name] = {
                    "password": str(info.get("password", "")),
                    "role": info.get("role", "admin"),
                }
            else:
                accounts[name] = {"password": str(info), "role": "admin"}
    # 兼容旧配置：ADMIN_PASSWORD 作为超级管理员账号
    legacy = st.secrets.get("ADMIN_PASSWORD", "")
    if legacy:
        accounts.setdefault("管理员", {"password": str(legacy), "role": "super"})
    return accounts


def _match_admin(pwd):
    """按密码匹配管理员账号；非空密码且命中才返回 (名字, 角色)，否则 None。"""
    if not pwd:
        return None
    for name, info in _admin_accounts().items():
        if info["password"] and pwd == info["password"]:
            return name, info["role"]
    return None


def is_super_admin():
    """当前会话是否是最终（超级）管理员。敏感设置入口用这个判断。"""
    return st.session_state.get("is_admin") and st.session_state.get("admin_role") == "super"


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
                    matched = _match_admin(pwd)
                    # 必须命中某个账号才放行：secret 未配置时拒绝一切登录，而不是空密码放行
                    if matched:
                        name, role = matched
                        st.session_state.is_admin = True
                        st.session_state.admin_name = name
                        st.session_state.admin_role = role
                        st.session_state._login_attempts = 0
                        st.rerun()
                    else:
                        st.session_state._login_attempts += 1
                        st.error("密码错误")
        else:
            role = st.session_state.get("admin_role", "admin")
            name = st.session_state.get("admin_name", "管理员")
            if role == "super":
                st.success(f"👑 最终管理员：{name}")
            else:
                st.success(f"✅ 管理员：{name}")
            if st.button("退出登录", key="admin_logout_btn"):
                st.session_state.is_admin = False
                st.session_state.admin_role = None
                st.session_state.admin_name = None
                st.rerun()
