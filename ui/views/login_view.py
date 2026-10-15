"""
VitalOptima Secure Authentication & Role-Based Access Control View
Provides server-side credential verification, demo quick-fill credentials, and role routing.
"""
import streamlit as st
from services.auth_service import authenticate_user
from config import HOSPITAL_NAME


def show_login_view():
    """Renders the hospital portal login view."""
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
            <div style="margin-bottom: 0.85rem;">
                <h4 style="margin: 0; color: #1E293B; font-weight: 700;">Sign in to your account</h4>
                <p style="margin: 0; font-size: 0.8rem; color: #64748B;">Enter your hospital credentials to access your designated workspace.</p>
            </div>
            """, unsafe_allow_html=True)

            # Quick credential pre-fill helpers
            st.markdown("<div style='font-size: 0.75rem; font-weight: 600; color: #475569; margin-bottom: 0.3rem;'>Quick Demo Role Selection:</div>", unsafe_allow_html=True)
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if st.button("👑 Admin Role", width="stretch", help="Fill administrator credentials"):
                    st.session_state["login_user_input"] = "admin"
                    st.session_state["login_pass_input"] = "Admin@Vital2026!"
                    st.rerun()
            with c_btn2:
                if st.button("📋 Admission Officer", width="stretch", help="Fill admission officer credentials"):
                    st.session_state["login_user_input"] = "admit_officer"
                    st.session_state["login_pass_input"] = "Admit@Vital2026!"
                    st.rerun()

            default_user = st.session_state.get("login_user_input", "")
            default_pass = st.session_state.get("login_pass_input", "")

            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username or Employee ID", value=default_user, placeholder="e.g. admin or admit_officer")
                password = st.text_input("Password", value=default_pass, type="password", placeholder="Enter your secure password")
                
                st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Sign In →", type="primary", width="stretch")

                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        with st.spinner("Authenticating credentials..."):
                            user = authenticate_user(username, password)
                            if user:
                                st.session_state["authenticated_user"] = user
                                # Route initial view based on role
                                if user["role"] == "ADMISSION_OFFICER":
                                    st.session_state["current_page"] = "Admission Workspace"
                                else:
                                    st.session_state["current_page"] = "Dashboard"
                                st.toast(f"Welcome, {user['full_name']} ({user['role']})")
                                st.rerun()
                            else:
                                st.error("❌ Invalid username or password. Please verify your credentials.")

            st.markdown("""
            <div style="margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid #E2E8F0; font-size: 0.75rem; color: #64748B;">
                <b>Role Access Permissions:</b>
                <ul style="margin: 0.35rem 0 0 1rem; padding: 0; line-height: 1.45;">
                    <li><b>ADMIN:</b> Full Command Center Dashboard, AI Summarizer, ML Forecasting, Optimization, What-if Simulator, Records.</li>
                    <li><b>ADMISSION_OFFICER:</b> Admission Workspace, Bed Allocation, Active Patient Roster, Bed Capacity, Safe Discharge.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
