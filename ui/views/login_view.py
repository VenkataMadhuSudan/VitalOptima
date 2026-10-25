"""
VitalOptima Secure Authentication & Role-Based Access Control View
Provides server-side credential verification, demo quick-fill credentials, and role routing.
"""
import streamlit as st
from services.auth_service import authenticate_user
from config import HOSPITAL_NAME


def _login_as_user(user: dict):
    """Stores user in session state and routes to appropriate workspace."""
    st.session_state["authenticated_user"] = user
    if user["role"] == "ADMISSION_OFFICER":
        st.session_state["current_page"] = "Admission Workspace"
    else:
        st.session_state["current_page"] = "Dashboard"
    st.toast(f"✅ Signed in as {user.get('full_name')} ({user.get('role')})")
    st.rerun()


def show_login_view():
    """Renders the hospital portal login view."""
    # Ensure default pre-filled credentials for seamless one-click sign in
    if "login_username_field" not in st.session_state:
        st.session_state["login_username_field"] = "admin"
    if "login_password_field" not in st.session_state:
        st.session_state["login_password_field"] = "Admin@Vital2026!"

    # Centered container
    _, col_mid, _ = st.columns([1, 1.8, 1])

    with col_mid:
        st.html("""
        <div style="text-align: center; margin-top: 1.5rem; margin-bottom: 1.25rem;">
            <div style="font-size: 2.8rem; line-height: 1; margin-bottom: 0.35rem;">🫀</div>
            <h2 style="font-weight: 800; color: #0F172A; margin: 0; font-size: 1.85rem; letter-spacing: -0.5px;">VitalOptima</h2>
            <div style="font-size: 0.88rem; color: #64748B; font-weight: 500; margin-top: 0.25rem;">
                Hospital Resource Management & Command Center
            </div>
            <div style="display: inline-block; margin-top: 0.5rem; font-size: 0.75rem; background: #EFF6FF; color: #1E60F2; font-weight: 700; padding: 0.2rem 0.65rem; border-radius: 20px; border: 1px solid #BFDBFE;">
                🏥 City General Hospital • Clinical Access Gateway
            </div>
        </div>
        """)

        with st.container(border=True):
            st.markdown("""
            <div style="margin-bottom: 0.75rem;">
                <h4 style="margin: 0; color: #1E293B; font-weight: 700;">Sign in to your account</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #64748B;">Enter your hospital credentials or select a quick demo role below.</p>
            </div>
            """, unsafe_allow_html=True)

            # Quick Demo One-Click Access Buttons
            st.markdown("""
            <div style="font-size: 0.74rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 0.35rem;">
                ⚡ One-Click Demo Access
            </div>
            """, unsafe_allow_html=True)
            demo_c1, demo_c2 = st.columns(2)
            with demo_c1:
                if st.button("👑 Admin (Command Center)", type="primary", use_container_width=True, key="quick_admin_btn"):
                    with st.spinner("Authenticating Medical Director..."):
                        u = authenticate_user("admin", "Admin@Vital2026!")
                        if u:
                            _login_as_user(u)
            with demo_c2:
                if st.button("🏥 Admission Officer", type="secondary", use_container_width=True, key="quick_admit_btn"):
                    with st.spinner("Authenticating Triage Officer..."):
                        u = authenticate_user("admit_officer", "Admit@Vital2026!")
                        if u:
                            _login_as_user(u)

            st.markdown("""
            <div style="position: relative; text-align: center; margin: 0.9rem 0 0.75rem 0;">
                <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 0;">
                <span style="position: absolute; top: -9px; left: 50%; transform: translateX(-50%); background: #FFFFFF; padding: 0 0.5rem; font-size: 0.72rem; color: #94A3B8; font-weight: 600;">OR ENTER CREDENTIALS</span>
            </div>
            """, unsafe_allow_html=True)

            # Standard Credential Form
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input(
                    "Username or Employee ID",
                    value=st.session_state.get("login_username_field", "admin"),
                    placeholder="e.g. admin or admit_officer",
                    key="login_user_input"
                )
                password = st.text_input(
                    "Password",
                    value=st.session_state.get("login_password_field", "Admin@Vital2026!"),
                    type="password",
                    placeholder="Enter password",
                    key="login_pass_input"
                )

                st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        with st.spinner("Authenticating credentials..."):
                            user = authenticate_user(username.strip(), password)
                            if user:
                                _login_as_user(user)
                            else:
                                st.error("❌ Invalid username or password. Please verify your credentials against the pre-configured accounts below.")

            # Demo Accounts Reference Card
            st.markdown("""
            <div style="margin-top: 0.85rem; padding: 0.65rem 0.8rem; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; font-size: 0.75rem;">
                <div style="font-weight: 700; color: #1E293B; margin-bottom: 0.35rem;">📋 Pre-configured Demo Accounts:</div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                    <span><b>Admin:</b> <code style="background:#E2E8F0; padding:1px 4px; border-radius:3px;">admin</code></span>
                    <span>Password: <code style="background:#E2E8F0; padding:1px 4px; border-radius:3px;">Admin@Vital2026!</code></span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span><b>Admission Officer:</b> <code style="background:#E2E8F0; padding:1px 4px; border-radius:3px;">admit_officer</code></span>
                    <span>Password: <code style="background:#E2E8F0; padding:1px 4px; border-radius:3px;">Admit@Vital2026!</code></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Role Access Description
            st.markdown("""
            <div style="margin-top: 0.75rem; font-size: 0.72rem; color: #64748B;">
                <b>Role Capabilities:</b>
                <ul style="margin: 0.25rem 0 0 1rem; padding: 0; line-height: 1.4;">
                    <li><b>ADMIN:</b> Full Command Center, AI Insights, OR-Tools Optimizer, Demand Forecasts, Crisis Simulator, Audit Trail.</li>
                    <li><b>ADMISSION_OFFICER:</b> Patient Triage & Bed Allocation Workspace, Active Census, Safe Patient Discharge.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

