# ui/pages_core.py
import json
import streamlit as st
from datetime import date
from services.helpers import get_active_user_info, fmt_money, fmt_date, get_current_currency, SUPPORTED_CURRENCIES
from services.database import (
    sb, fetch_properties, fetch_tenants, fetch_payments,
    fetch_leases, fetch_maintenance, fetch_landlords, clear_cache
)
from components.ads import render_ad_space_management
from services.alerts import render_overdue_alerts_widget


def header():
    st.markdown("""
    <div class="main-header">
        <h1>RentMaster-GH</h1>
        <p>Rental Property Management System &middot; Version 2.5</p>
    </div>
    """, unsafe_allow_html=True)


@st.dialog("Submit Support Request or Suggestion")
def show_support_dialog():
    st.write("Have a complaint, feature suggestion, or running into an issue? Let us know below!")
    with st.form("support_form", clear_on_submit=True):
        category = st.selectbox("Category *", ["Complaint", "Suggestion", "Bug Report", "General Query"])
        subject = st.text_input("Subject *")
        message = st.text_area("Details / Message *", help="Please describe your suggestion or complaint in detail.")
        submitted = st.form_submit_button("Submit Request", type="primary", use_container_width=True)

        if submitted:
            if not subject or not message:
                st.error("Please fill in all required fields marked with *.")
            elif not sb:
                st.error("Database connection missing.")
            else:
                try:
                    user_id, user_email = get_active_user_info()
                    sb.table("support_requests").insert({
                        "category": category,
                        "subject": subject,
                        "message": message,
                        "user_email": user_email,
                        "created_at": str(date.today()),
                    }).execute()
                    st.success("✅ Your request has been submitted. Thank you!")
                except Exception as e:
                    st.error(f"Failed to submit request: {e}")


def page_dashboard():
    header()
    st.subheader("Dashboard Overview")
    user_id, user_email = get_active_user_info()

    props = fetch_properties(user_id, user_email)
    tenants = fetch_tenants(user_id, user_email)
    payments = fetch_payments(user_id, user_email)
    leases = fetch_leases(user_id, user_email)
    maint = fetch_maintenance(user_id, user_email)

    expected = sum(float(p.get("monthly_rent") or p.get("rent_amount") or 0) for p in props)
    collected = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("status") == "paid")
    pending = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("status") == "pending")
    overdue = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("status") == "overdue")
    occupied = sum(1 for p in props if p.get("is_occupied", False))

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Properties", len(props), f"{occupied} occupied")
    col2.metric("Tenants", len(tenants), f"{sum(1 for t in tenants if t.get('is_active'))} active")
    col3.metric("Expected Monthly Rent", fmt_money(expected))
    col4.metric("Active Leases", sum(1 for l in leases if l.get("status") == "active"))

    st.markdown("---")
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Collected", fmt_money(collected))
    col6.metric("Pending", fmt_money(pending))
    col7.metric("Overdue", fmt_money(overdue))
    col8.metric("Open Maintenance", sum(1 for m in maint if m.get("status") in ("open", "in_progress")))

    # -------------------------------------------------------------------
    # RENT OVERDUE ALERT ENGINE WIDGET (ADDED)
    # -------------------------------------------------------------------
    st.markdown("---")
    render_overdue_alerts_widget(tenants, payments)

    st.markdown("---")
    st.markdown("#### Portfolio Summary")
    left, right = st.columns(2)
    with left:
        st.markdown("**Payment Status Breakdown**")
        status_counts = {}
        for p in payments:
            s = p.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        if status_counts:
            st.bar_chart(status_counts)
        else:
            st.info("No payments recorded yet.")
    with right:
        st.markdown("**Maintenance by Priority**")
        priority_counts = {}
        for m in maint:
            pr = m.get("priority", "medium")
            priority_counts[pr] = priority_counts.get(pr, 0) + 1
        if priority_counts:
            st.bar_chart(priority_counts)
        else:
            st.info("No maintenance requests yet.")


def page_user_profile():
    header()
    st.subheader("👤 User Profile & Control Panel")

    user = st.session_state.get("user")
    user_email = getattr(user, "email", "Unknown User") if user else "Unknown User"
    user_id = getattr(user, "id", "N/A") if user else "N/A"

    profile_tab1, profile_tab2, profile_tab3, profile_tab4, profile_tab5 = st.tabs([
        "1. Account Details",
        "2. User Management",
        "3. Account Security",
        "4. Change Password",
        "5. Security Settings"
    ])

    with profile_tab1:
        st.markdown("#### 📄 Account Details")
        with st.form("account_details_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("User ID", value=user_id, disabled=True)
                full_name = st.text_input("Full Name", value=st.session_state.get("profile_full_name", ""))
                phone = st.text_input("Phone Number", value=st.session_state.get("profile_phone", ""))
            with col2:
                st.text_input("Email Address", value=user_email, disabled=True)
                st.selectbox("Account Role", ["Administrator", "Landlord / Property Manager", "Tenant", "Agent"], index=0)
                st.text_input("Company / Organization", value="RentMaster Operations")

            if st.form_submit_button("Save Account Details", type="primary"):
                st.session_state["profile_full_name"] = full_name
                st.session_state["profile_phone"] = phone
                st.toast("✅ Account details saved successfully!", icon="👤")

    with profile_tab2:
        st.markdown("#### 👥 User Management")
        tenants = fetch_tenants(user_id, user_email)
        landlords = fetch_landlords(user_id, user_email)

        col_u1, col_u2 = st.columns(2)
        col_u1.metric("Total Landlords Registered", len(landlords))
        col_u2.metric("Total Active Tenants Registered", len(tenants))

        st.markdown("---")
        st.markdown("##### Registered System Users")
        user_table_data = [{
            "User ID": str(user_id)[:8] + "...",
            "Email": user_email,
            "Role": "System Administrator",
            "Status": "Active Now",
            "Joined": str(date.today())
        }]
        for l in landlords:
            user_table_data.append({
                "User ID": str(l["id"])[:8] + "...",
                "Email": l.get("email", "N/A"),
                "Role": "Landlord",
                "Status": "Active",
                "Joined": fmt_date(l.get("created_at"))
            })
        st.dataframe(user_table_data, use_container_width=True, hide_index=True)

    with profile_tab3:
        st.markdown("#### 🛡️ Account Security")
        sec_col1, sec_col2 = st.columns(2)
        with sec_col1:
            st.markdown("##### Multi-Factor Authentication (MFA / 2FA)")
            if st.toggle("Enable Two-Factor Authentication (2FA)", value=False):
                st.info("📱 Scan the QR code with Google Authenticator or Authy to complete setup.")
        with sec_col2:
            st.markdown("##### Active Sessions & Login Audit")
            st.write(f"**Current Session:** Logged in ({user_email})")
            st.write(f"**Remember Me Enabled:** `{st.session_state.get('remember_me', True)}`")

    with profile_tab4:
        st.markdown("#### 🔑 Change Password")
        with st.form("change_password_form"):
            st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password (Min 6 characters)", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")

            if st.form_submit_button("Update Password", type="primary"):
                if not new_pw or not confirm_pw or new_pw != confirm_pw or len(new_pw) < 6:
                    st.error("Please enter matching passwords (min 6 characters).")
                elif sb:
                    try:
                        sb.auth.update_user({"password": new_pw})
                        st.success("✅ Password updated successfully!")
                    except Exception as e:
                        st.error(f"Failed to update password: {e}")

    with profile_tab5:
        st.markdown("#### ⚙️ Security Settings")
        with st.form("security_settings_form"):
            st.checkbox("Send Email Notification on New Login", value=True)
            st.checkbox("Alert me via Email when rent is overdue", value=True)
            session_timeout = st.select_slider("Session Timeout (Minutes)", options=[15, 30, 60, 120, 1440], value=60)
            if st.form_submit_button("Save Security Settings", type="primary"):
                st.toast(f"✅ Settings saved! Timeout set to {session_timeout} mins.", icon="⚙️")


def page_settings():
    header()
    st.subheader("Settings & Administration")

    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    with st.container(border=True):
        col_info1, col_info2 = st.columns([3, 1])
        with col_info1:
            st.markdown("### RentMaster-GH Enterprise")
            st.markdown("A comprehensive rental property management system.")
        with col_info2:
            st.markdown("**Version:** `2.5.0`")
            st.markdown("**Database Status:** :green[Connected]" if sb else ":red[Disconnected]")

    st.markdown("---")
    st.markdown("#### System Preferences & Currency Settings")
    with st.container(border=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            currency_options = list(SUPPORTED_CURRENCIES.keys())
            curr_index = currency_options.index(curr_code) if curr_code in currency_options else 0
            selected_currency = st.selectbox("Default Currency *", options=currency_options, format_func=lambda x: SUPPORTED_CURRENCIES[x]["name"], index=curr_index)
        with col_p2:
            st.toggle("Enable Automated Payment Alerts", value=True)

        if st.button("Save System Preferences", type="primary", key="save_prefs"):
            st.session_state["app_currency"] = selected_currency
            st.toast(f"Preferences saved! Currency: {selected_currency}.", icon="✅")
            st.rerun()

    st.markdown("---")
    render_ad_space_management(key_prefix="settings_ad")

    st.markdown("---")
    st.markdown("#### Data Management & Backup Export")
    col1, col2, col3 = st.columns(3)
    col1.download_button("📥 Export Properties", data=json.dumps(fetch_properties(user_id, user_email), indent=2), file_name="properties.json", mime="application/json", use_container_width=True)
    col2.download_button("📥 Export Payments", data=json.dumps(fetch_payments(user_id, user_email), indent=2), file_name="payments.json", mime="application/json", use_container_width=True)
    col3.download_button("📥 Export Tenants", data=json.dumps(fetch_tenants(user_id, user_email), indent=2), file_name="tenants.json", mime="application/json", use_container_width=True)
