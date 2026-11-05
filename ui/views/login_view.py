"""
VitalOptima Secure Authentication & Role-Based Access Control View
Provides modern clinical SaaS aesthetic, server-side credential verification,
persistent brute-force lockout handling, forced password rotation, and environment-aware demo helpers.
"""
import os
import streamlit as st
from services.auth_service import (
    authenticate_user, is_account_locked, is_ip_locked,
    change_user_password, validate_password_complexity
)
from config import HOSPITAL_NAME


def _login_as_user(user: dict):
    """Stores user in session state and routes to appropriate workspace."""
    import time
    st.session_state["authenticated_user"] = user
    st.session_state["_last_token_validation_ts"] = time.time()
    if user["role"] == "ADMISSION_OFFICER":
        st.session_state["current_page"] = "Admission Workspace"
    else:
        st.session_state["current_page"] = "Dashboard"
    st.toast(f"✅ Signed in as {user.get('full_name')} ({user.get('role')})")
    st.rerun()


def _render_password_change_modal(pending_user: dict):
    """Renders mandatory first-time / administrative password change dialog."""
    st.markdown("""
    <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
            <span style="font-size: 1.25rem;">⚠️</span>
            <h4 style="margin: 0; color: #92400E; font-weight: 700; font-size: 1.05rem;">Password Change Required</h4>
        </div>
        <p style="margin: 0; font-size: 0.82rem; color: #B45309;">
            Your account was provisioned with temporary or initial credentials. 
            For clinical information security and HIPAA compliance, you must set a new strong password before accessing patient data.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("force_pw_change_form", clear_on_submit=False):
        current_pw = st.text_input("Current Temporary Password", type="password", key="force_curr_pw")
        new_pw = st.text_input("New Password", type="password", key="force_new_pw",
                               help="Must be at least 8 characters with uppercase, lowercase, numbers, and special symbols.")
        confirm_pw = st.text_input("Confirm New Password", type="password", key="force_conf_pw")

        st.markdown("""
        <div style="font-size: 0.72rem; color: #64748B; margin-top: 0.25rem; margin-bottom: 0.5rem;">
            <b>Complexity Requirements:</b>
            <ul style="margin: 0.2rem 0 0 1rem; padding: 0;">
                <li>Minimum 8 characters in length</li>
                <li>At least one uppercase (A-Z) and one lowercase (a-z) letter</li>
                <li>At least one numerical digit (0-9)</li>
                <li>At least one special symbol (!@#$%^&*...)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        submitted_pw = st.form_submit_button("Update Password & Continue →", type="primary", use_container_width=True)
        if submitted_pw:
            if not current_pw or not new_pw or not confirm_pw:
                st.error("Please fill in all password fields.")
            elif new_pw != confirm_pw:
                st.error("New password and confirmation do not match.")
            else:
                valid, msg = validate_password_complexity(new_pw)
                if not valid:
                    st.error(f"❌ {msg}")
                else:
                    success, res_msg = change_user_password(pending_user["username"], current_pw, new_pw)
                    if success:
                        st.success("✅ Password updated successfully! Redirecting...")
                        del st.session_state["pending_pw_change_user"]
                        pending_user["must_change_password"] = False
                        _login_as_user(pending_user)
                    else:
                        st.error(f"❌ {res_msg}")

    if st.button("Cancel & Return to Sign In", use_container_width=True):
        del st.session_state["pending_pw_change_user"]
        st.rerun()


def show_login_view():
    """Renders the hospital portal login view."""
    app_env = os.getenv("APP_ENV", "development").lower()
    seed_demo = os.getenv("SEED_DEMO_USERS", "true").lower() == "true"
    is_demo_mode = seed_demo or (app_env != "production")

    # Check if user is in mandatory password change flow
    if "pending_pw_change_user" in st.session_state:
        _, col_mid, _ = st.columns([1, 1.8, 1])
        with col_mid:
            with st.container(border=True):
                _render_password_change_modal(st.session_state["pending_pw_change_user"])
        return

    # Centered container
    _, col_mid, _ = st.columns([1, 1.8, 1])

    with col_mid:
        st.html("""
        <div style="text-align: center; margin-top: 1.5rem; margin-bottom: 1.25rem;">
            <div style="font-size: 2.8rem; line-height: 1; margin-bottom: 0.35rem;">🫀</div>
            <h2 style="font-weight: 800; color: #0F172A; margin: 0; font-size: 1.85rem; letter-spacing: -0.5px;">VitalOptima</h2>
            <div style="font-size: 0.88rem; color: #64748B; font-weight: 500; margin-top: 0.25rem;">
                Hospital Operations Intelligence & Resource Optimization
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
                <p style="margin: 0; font-size: 0.8rem; color: #64748B;">Enter your hospital credentials to access the operational intelligence platform.</p>
            </div>
            """, unsafe_allow_html=True)

            # Quick Demo One-Click Access Buttons (Only rendered in development/demo environments)
            if is_demo_mode:
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
                                if u.get("must_change_password"):
                                    st.session_state["pending_pw_change_user"] = u
                                    st.rerun()
                                else:
                                    _login_as_user(u)
                with demo_c2:
                    if st.button("🏥 Admission Officer", type="secondary", use_container_width=True, key="quick_admit_btn"):
                        with st.spinner("Authenticating Triage Officer..."):
                            u = authenticate_user("admit_officer", "Admit@Vital2026!")
                            if u:
                                if u.get("must_change_password"):
                                    st.session_state["pending_pw_change_user"] = u
                                    st.rerun()
                                else:
                                    _login_as_user(u)

                st.markdown("""
                <div style="position: relative; text-align: center; margin: 0.9rem 0 0.75rem 0;">
                    <hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 0;">
                    <span style="position: absolute; top: -9px; left: 50%; transform: translateX(-50%); background: #FFFFFF; padding: 0 0.5rem; font-size: 0.72rem; color: #94A3B8; font-weight: 600;">OR ENTER CREDENTIALS</span>
                </div>
                """, unsafe_allow_html=True)

            # Show/Hide password toggle state
            show_pw = st.checkbox("Show password characters", value=False, key="toggle_show_pw")
            pw_input_type = "default" if show_pw else "password"

            default_uname = "admin" if is_demo_mode else ""
            default_pw = "Admin@Vital2026!" if is_demo_mode else ""

            # Robust single-click form batching (native enter-to-submit without blur race conditions)
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input(
                    "Username or Employee ID",
                    value=default_uname,
                    placeholder="e.g. admin or admit_officer",
                    key="login_user_input"
                )

                password = st.text_input(
                    "Password",
                    value=default_pw,
                    type=pw_input_type,
                    placeholder="Enter account password",
                    key="login_pass_input"
                )

                st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("Please enter both username and password.")
                else:
                    clean_u = username.strip().lower()
                    # Check lockout status first for immediate feedback
                    is_locked, rem_sec = is_account_locked(clean_u)
                    if is_locked:
                        rem_min = max(1, rem_sec // 60)
                        st.error(f"🔒 Account temporarily locked due to excessive failed attempts. Please retry in {rem_min} minute(s) or contact your hospital system administrator.")
                    else:
                        with st.spinner("Authenticating credentials..."):
                            user = authenticate_user(clean_u, password)
                            if user:
                                if user.get("must_change_password"):
                                    st.session_state["pending_pw_change_user"] = user
                                    st.rerun()
                                else:
                                    _login_as_user(user)
                            else:
                                # Check again if this attempt triggered a new lockout
                                now_locked, now_rem = is_account_locked(clean_u)
                                if now_locked:
                                    rem_min = max(1, now_rem // 60)
                                    st.error(f"🔒 Account has been locked due to 5 consecutive failed login attempts. Cooldown active for {rem_min} minute(s).")
                                else:
                                    st.error("❌ Invalid username or password. Please verify your credentials.")

            # Demo Accounts Reference Card (Only visible in demo/development mode)
            if is_demo_mode:
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
            else:
                # Production Security Notice
                st.markdown("""
                <div style="margin-top: 0.85rem; padding: 0.65rem 0.8rem; background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 0.74rem; color: #475569;">
                    <div style="font-weight: 700; color: #1E293B; margin-bottom: 0.25rem;">🛡️ Clinical Security Gateway</div>
                    Authorized clinical access only. Unregistered or unauthorized access attempts are logged with client IP address and reported in accordance with hospital data governance standards.
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
