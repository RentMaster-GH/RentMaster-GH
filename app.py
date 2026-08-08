# app.py
"""
RentMaster-GH - Rental Property Management Web App
Main Entry Point & App Router
"""

import json
import streamlit as st
import extra_streamlit_components as stx
from services.helpers import inject_google_analytics, inject_google_site_verification
from services.database import sb, clear_cache
from services.paystack import handle_paystack_callbacks
from ui.pages_core import (
    header, show_support_dialog, page_dashboard,
    page_user_profile, page_settings
)
from ui.pages_management import (
    page_properties, page_landlords, page_tenants,
    page_payments, page_leases, page_maintenance
)
from ui.tenant_portal import render_tenant_portal

# ---------------------------------------------------------------------------
# Streamlit Config (MUST BE FIRST)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RentMaster-GH",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Cookie Manager Instance
cookie_manager = stx.CookieManager(key="rentmaster_cookie_mgr")

# Inject Google Analytics & Site Verification
inject_google_analytics("G-EFD2P6FKM5")
inject_google_site_verification("SXu9dztavBBjKgrko60Tx2CjufX2KvyRhW42SOczZrc")

# Initialize Session State Defaults
if "user" not in st.session_state:
    st.session_state["user"] = None

if "app_currency" not in st.session_state:
    st.session_state["app_currency"] = "GHS"

# ---------------------------------------------------------------------------
# Persistent Cookie Auto-Login
# ---------------------------------------------------------------------------
if st.session_state.get("user") is None and sb:
    try:
        saved_session_cookie = cookie_manager.get(cookie="rentmaster_session")
        if saved_session_cookie:
            session_data = json.loads(saved_session_cookie) if isinstance(saved_session_cookie, str) else saved_session_cookie
            ref_token = session_data.get("refresh_token")
            acc_token = session_data.get("access_token")

            if ref_token and acc_token:
                res = sb.auth.set_session(acc_token, ref_token)
                if res and res.user:
                    st.session_state["user"] = res.user
    except Exception:
        try: cookie_manager.delete("rentmaster_session")
        except Exception: pass

# Global Paystack Payment Callback Verification Handler
handle_paystack_callbacks()

# Handle OAuth code exchange
if sb and "code" in st.query_params:
    try:
        auth_code = st.query_params["code"]
        st.query_params.clear()
        res = sb.auth.exchange_code_for_session({"auth_code": auth_code})
        if res and res.user:
            st.session_state["user"] = res.user
            clear_cache()
            st.rerun()
    except Exception:
        pass


# Login Page Render
def auth_page():
    st.markdown("<h2 style='text-align: center;'>RentMaster-GH</h2>", unsafe_allow_html=True)
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Log In", type="primary", use_container_width=True):
        if sb:
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": password})
                if res.user:
                    st.session_state["user"] = res.user
                    clear_cache()
                    st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")


if st.session_state.get("user") is None:
    auth_page()
    st.stop()

# Navigation Router
PAGES = {
    "Dashboard": page_dashboard,
    "Tenant Portal": render_tenant_portal,
    "User Profile": page_user_profile,
    "Properties": page_properties,
    "Landlords": page_landlords,
    "Tenants": page_tenants,
    "Payments": page_payments,
    "Leases": page_leases,
    "Maintenance": page_maintenance,
    "Settings": page_settings,
}

with st.sidebar:
    st.markdown("### Navigation")
    selection = st.radio("Go to", list(PAGES.keys()))
    st.markdown("---")
    if st.button("💬 Support & Suggestions", use_container_width=True):
        show_support_dialog()
    st.markdown("---")
    active_user = st.session_state.get("user")
    if active_user:
        st.write(f"👤 Logged in: **{getattr(active_user, 'email', 'User')}**")
        if st.button("Logout", key="logout_btn"):
            try: cookie_manager.delete("rentmaster_session")
            except Exception: pass
            if sb: sb.auth.sign_out()
            st.session_state.clear()
            st.rerun()

# Run Selected Page
PAGES[selection]()
