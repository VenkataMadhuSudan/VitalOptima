"""
VitalOptima Settings & Access Management View
Allows hospital administrators to view existing accessors, provision new Admin or Admission Officer accounts,
audit security events, and manage role credentials.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from config import HOSPITAL_NAME, ADMIN_USER, ADMIN_INITIALS, get_system_timestamp
from services.auth_service import (
    get_current_user, require_permission, has_permission,
    get_all_users, create_new_user, toggle_user_status, delete_user,
    get_recent_audit_logs, ROLE_ADMIN, ROLE_ADMISSION_OFFICER
)
from ui.components import render_top_nav, render_footer


def show_settings_view():
    """Renders the administrative settings and accessor management view."""
    user = get_current_user()
    if not user:
        st.error("Authentication required.")
        return

    # Least-privilege backend check
    try:
        require_permission("users.manage", user)
    except PermissionError as e:
        st.error(f"⛔ {str(e)}")
        return

    user_name = user.get("full_name", ADMIN_USER)
    user_initials = user.get("username", ADMIN_INITIALS)[:2].upper()
    render_top_nav(HOSPITAL_NAME, get_system_timestamp(), user_initials, user_name)

    st.markdown("""
    <div style="margin-bottom: 1.25rem;">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <h2 style="font-weight: 800; color: #0F172A; margin: 0; font-size: 1.75rem;">⚙️ Settings & Access Management</h2>
            <span style="background: #EFF6FF; color: #1E60F2; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.6rem; border-radius: 6px; border: 1px solid #BFDBFE;">
                Administrator Console
            </span>
        </div>
        <p style="color: #64748B; margin-top: 0.25rem; font-size: 0.88rem;">
            Inspect existing hospital system accessors, audit role assignments, and provision new Administrator or Admission Officer credentials.
        </p>
    </div>
    """, unsafe_allow_html=True)

    users_list = get_all_users()
    admin_count = sum(1 for u in users_list if u.get("role") == ROLE_ADMIN and u.get("is_active", 1))
    officer_count = sum(1 for u in users_list if u.get("role") == ROLE_ADMISSION_OFFICER and u.get("is_active", 1))

    # Metric Cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Registered Accessors", f"{len(users_list)} Users", "Active Directory")
    with m2:
        st.metric("Hospital Administrators", f"{admin_count} Admins", "Full Command Access")
    with m3:
        st.metric("Admission Officers", f"{officer_count} Officers", "Admission Scoped")
    with m4:
        st.metric("Security Level", "NIST PBKDF2-SHA256", "Salted Hash Storage")

    st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    tab_users, tab_add, tab_audit = st.tabs([
        f"👥 Existing System Accessors ({len(users_list)})",
        "➕ Provision New Accessor Account",
        "📜 Security & RBAC Audit Trail"
    ])

    # =========================================================================
    # TAB 1: EXISTING USERS & ACCESS MANAGEMENT
    # =========================================================================
    with tab_users:
        st.markdown("""
        <div style="margin-bottom: 0.85rem;">
            <h4 style="margin: 0; color: #0F172A; font-weight: 700; font-size: 1.15rem;">Registered Accessors & Active Privileges</h4>
            <p style="margin: 0; font-size: 0.8rem; color: #64748B;">
                Authoritative user registry stored securely in the hospital database.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if not users_list:
            st.info("No accessors registered in database.")
        else:
            display_users = []
            for u in users_list:
                status_label = "🟢 Active" if u.get("is_active", 1) else "🔴 Deactivated"
                display_users.append({
                    "User ID": u.get("id"),
                    "Username": u.get("username"),
                    "Full Name": u.get("full_name"),
                    "Assigned Role": u.get("role"),
                    "Department": u.get("department", "Hospital"),
                    "Account Status": status_label,
                    "Created On": u.get("created_at", "Baseline"),
                    "Last Login": u.get("last_login") or "Never"
                })

            df_users = pd.DataFrame(display_users)
            st.dataframe(df_users, width="stretch", hide_index=True)

            # Account Management Actions
            st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<div style='font-size: 0.88rem; font-weight: 700; color: #1E293B; margin-bottom: 0.4rem;'>🛡️ Modify Accessor Status</div>", unsafe_allow_html=True)
                
                c_sel, c_act1, c_act2 = st.columns([2.5, 1.2, 1.2])
                with c_sel:
                    user_options = {
                        f"{u['username']} — {u['full_name']} ({u['role']})": u['username']
                        for u in users_list
                    }
                    selected_label = st.selectbox("Select Accessor to Manage", list(user_options.keys()), key="sb_manage_user")
                    selected_username = user_options[selected_label]
                    selected_obj = next((u for u in users_list if u['username'] == selected_username), None)

                with c_act1:
                    st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
                    if selected_obj:
                        is_currently_active = bool(selected_obj.get("is_active", 1))
                        btn_label = "🔴 Deactivate" if is_currently_active else "🟢 Activate"
                        if st.button(btn_label, width="stretch", key="btn_toggle_user_status"):
                            try:
                                toggle_user_status(selected_username, not is_currently_active, actor_user=user)
                                st.success(f"Accessor '{selected_obj['username']}' status updated!")
                                st.rerun()
                            except Exception as ex:
                                st.error(str(ex))

                with c_act2:
                    st.markdown("<div style='height: 1.7rem;'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ Delete", width="stretch", type="secondary", key="btn_del_user"):
                        try:
                            delete_user(selected_username, actor_user=user)
                            st.success(f"Accessor account removed.")
                            st.rerun()
                        except Exception as ex:
                            st.error(str(ex))

    # =========================================================================
    # TAB 2: PROVISION NEW ACCESSOR ACCOUNT
    # =========================================================================
    with tab_add:
        st.markdown("""
        <div style="margin-bottom: 0.85rem;">
            <h4 style="margin: 0; color: #0F172A; font-weight: 700; font-size: 1.15rem;">Provision New Hospital Accessor</h4>
            <p style="margin: 0; font-size: 0.8rem; color: #64748B;">
                Create an authenticated user account and grant authorized Administrator or Admission Officer role boundaries.
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_form, col_info = st.columns([1.3, 1.0], gap="medium")

        with col_form:
            with st.container(border=True):
                st.markdown("<div style='font-size: 0.88rem; font-weight: 700; color: #1E293B; margin-bottom: 0.5rem;'>Accessor Credentials & Role Definition</div>", unsafe_allow_html=True)

                f1, f2 = st.columns(2)
                with f1:
                    new_username = st.text_input("Username / Employee ID *", placeholder="e.g. dr_verma or admit_officer_3", key="new_u_username")
                with f2:
                    new_fullname = st.text_input("Full Name *", placeholder="e.g. Dr. Kavita Verma", key="new_u_fullname")

                f3, f4 = st.columns(2)
                with f3:
                    new_role = st.selectbox(
                        "Assigned Role *",
                        [ROLE_ADMISSION_OFFICER, ROLE_ADMIN],
                        format_func=lambda x: "📋 Admission Officer (Admission Scoped)" if x == ROLE_ADMISSION_OFFICER else "👑 Admin (Full Command Center)",
                        key="new_u_role"
                    )
                with f4:
                    new_dept = st.selectbox(
                        "Clinical Department",
                        [
                            "Central Admissions & Triage",
                            "Hospital Administration",
                            "Emergency Medicine",
                            "Internal Medicine",
                            "Critical Care / ICU",
                            "Surgical Services",
                            "Pediatrics",
                            "Obstetrics & Gynecology",
                            "Orthopedics"
                        ],
                        key="new_u_dept"
                    )

                p1, p2 = st.columns(2)
                with p1:
                    new_pw = st.text_input("Password *", type="password", placeholder="Min 6 characters", key="new_u_pw")
                with p2:
                    new_pw_conf = st.text_input("Confirm Password *", type="password", placeholder="Re-enter password", key="new_u_pw_conf")

                st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)
                if st.button("👤 Provision Accessor Account", type="primary", width="stretch", key="btn_submit_new_user"):
                    if not new_username.strip():
                        st.error("Username is required.")
                    elif not new_fullname.strip():
                        st.error("Full Name is required.")
                    elif not new_pw or len(new_pw.strip()) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif new_pw != new_pw_conf:
                        st.error("Passwords do not match. Please verify your entries.")
                    else:
                        try:
                            created = create_new_user(
                                username=new_username,
                                password=new_pw,
                                role=new_role,
                                full_name=new_fullname,
                                department=new_dept,
                                actor_user=user
                            )
                            st.success(f"✅ Accessor account successfully provisioned for **{created['full_name']}** (`{created['username']}`) with role **{created['role']}**!")
                            st.toast(f"Account '{created['username']}' provisioned successfully!")
                            st.rerun()
                        except Exception as ex:
                            st.error(f"❌ Failed to provision account: {str(ex)}")

        with col_info:
            with st.container(border=True):
                st.markdown("<div style='font-size: 0.88rem; font-weight: 700; color: #1E293B; margin-bottom: 0.45rem;'>🔐 Role-Based Permission Scope</div>", unsafe_allow_html=True)
                
                st.markdown("""
                <div style="background: #F8FAFC; border-radius: 8px; border: 1px solid #E2E8F0; padding: 0.75rem; font-size: 0.78rem; color: #334155; line-height: 1.55;">
                    <b style="color: #1E60F2;">👑 ADMIN Capabilities:</b>
                    <ul style="margin: 0.2rem 0 0.5rem 1rem; padding: 0;">
                        <li>Full Hospital Command Center Dashboard & Operational KPIs</li>
                        <li>AI Dashboard Summarizer & Follow-up Q&A Assistant</li>
                        <li>ML Emergency Patient Demand Forecasting</li>
                        <li>Linear Programming Resource Allocation Optimizer</li>
                        <li>What-if Scenario Disaster Simulator</li>
                        <li>Clinical Decision Audit Logging & Historical Records</li>
                        <li>System Settings & User Access Management</li>
                    </ul>
                    <b style="color: #10B981;">📋 ADMISSION_OFFICER Capabilities:</b>
                    <ul style="margin: 0.2rem 0 0 1rem; padding: 0;">
                        <li>Admission & Bed Allocation Workspace</li>
                        <li>Patient Clinical Intake & Demographic Registration</li>
                        <li>Real-Time Departmental Bed Availability Matrix</li>
                        <li>Active Inpatient Roster & Disposition Tracking</li>
                        <li>Clinical Patient Discharge & Immediate Bed Release</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

    # =========================================================================
    # TAB 3: SECURITY & AUDIT TRAIL
    # =========================================================================
    with tab_audit:
        st.markdown("""
        <div style="margin-bottom: 0.85rem;">
            <h4 style="margin: 0; color: #0F172A; font-weight: 700; font-size: 1.15rem;">Recent Security & RBAC Audit Logs</h4>
            <p style="margin: 0; font-size: 0.8rem; color: #64748B;">
                Tamper-resistant audit events tracking authentication attempts, account creation, and role updates.
            </p>
        </div>
        """, unsafe_allow_html=True)

        logs = get_recent_audit_logs(limit=100)
        if not logs:
            st.info("No audit logs recorded yet.")
        else:
            log_rows = []
            for l in logs:
                log_rows.append({
                    "Timestamp": l.get("timestamp"),
                    "Actor": l.get("actor_username"),
                    "Role": l.get("actor_role"),
                    "Action": l.get("action"),
                    "Target ID": l.get("target_id") or "-",
                    "Target Type": l.get("target_type") or "-",
                    "Outcome": "✅ " + l.get("status") if l.get("status") == "SUCCESS" else "❌ " + l.get("status"),
                    "Details": l.get("details") or ""
                })
            df_logs = pd.DataFrame(log_rows)
            st.dataframe(df_logs, width="stretch", hide_index=True)

    render_footer()
