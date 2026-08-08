# app.py
"""
RentMaster-GH - Rental Property Management Web App
Main Entry Point & App Router
"""

import json
from datetime import datetime, timedelta
import streamlit as st
import extra_streamlit_components as stx
from services.helpers import inject_google_analytics, inject_google_site_verification
from services.database import sb, clear_cache
from services.paystack import handle_paystack_callbacks
from components.ads import render_public_ad_banners
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


# ---------------------------------------------------------------------------
# Authentication Screen with Integrated Sponsor Showcase
# ---------------------------------------------------------------------------
def auth_page():
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 2-Column Layout: Login/Signup Card (Left) + Subtle Sponsor Showcase (Right)
    login_col, ad_showcase_col = st.columns([1.2, 1])

    with login_col:
        with st.container(border=True):
            # Public Paystack Payment / Support Banner
            st.markdown(
                """
                <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 0.9rem; margin-bottom: 1rem; text-align: center;">
                    <p style="margin: 0 0 0.4rem 0; font-weight: 600; color: #166534; font-size: 0.88rem;">Looking to make a payment or support without logging in?</p>
                    <a href="https://paystack.shop/pay/zvx0npq7hv" target="_blank" rel="noopener noreferrer" style="display: inline-block; background-color: #09a5db; color: #ffffff; font-weight: 600; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-size: 0.88rem;">💙 Make a Payment / Donation via Paystack</a>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<h2 style='text-align: center; margin-bottom: 1rem;'>RentMaster-GH</h2>", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🔒 Log In", "📝 Sign Up"])
            redirect_url = "https://www.rentmastergh.com"

            # TAB 1: LOG IN
            with tab1:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_pw")
                remember_me = st.checkbox("Remember Me", value=True, key="login_remember_me")

                if st.button("Log In", use_container_width=True, key="login_btn", type="primary"):
                    if not sb:
                        st.error("Database connection missing.")
                    else:
                        try:
                            res = sb.auth.sign_in_with_password({"email": email, "password": password})
                            if res.user:
                                st.session_state["user"] = res.user
                                st.session_state["remember_me"] = remember_me
                                
                                # SAVE PERSISTENT BROWSER COOKIE (Valid for 30 Days)
                                if res.session:
                                    expires_at = datetime.now() + timedelta(days=30)
                                    cookie_data = json.dumps({
                                        "refresh_token": res.session.refresh_token,
                                        "access_token": res.session.access_token,
                                        "user_email": res.user.email
                                    })
                                    cookie_manager.set("rentmaster_session", cookie_data, expires_at=expires_at)
                                
                                clear_cache()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Login Error: {e}")

                st.divider()

                # Google OAuth Login Button
                if sb:
                    try:
                        res = sb.auth.sign_in_with_oauth({
                            "provider": "google",
                            "options": {"redirect_to": redirect_url}
                        })
                        if res.url:
                            st.markdown(
                                f"""
                                <a href="{res.url}" target="_self" style="display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 10px; border: 1px solid #dadce0; border-radius: 6px; background-color: white; color: #3c4043; font-weight: 500; text-decoration: none; box-sizing: border-box; font-size: 0.9rem;">
                                    <img src="https://www.gstatic.com/images/branding/product/1x/gsa_64dp.png" width="18" height="18"> Continue with Google
                                </a>
                                """,
                                unsafe_allow_html=True
                            )
                    except Exception as e:
                        st.error(f"Google OAuth error: {e}")

            # TAB 2: SIGN UP
            with tab2:
                new_email = st.text_input("Email Address", key="signup_email")
                confirm_email = st.text_input("Confirm Email Address", key="confirm_email")
                new_password = st.text_input("Password", type="password", key="signup_pw")
                confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pw")

                if st.button("Create Account", use_container_width=True, key="signup_btn", type="primary"):
                    if new_email != confirm_email:
                        st.error("Emails do not match")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long")
                    elif not sb:
                        st.error("Database connection missing.")
                    else:
                        try:
                            sb.auth.sign_up({"email": new_email, "password": new_password})
                            st.success("✅ Account created! Check your email to confirm registration.")
                        except Exception as e:
                            st.error(f"Sign Up Error: {e}")

    # RIGHT COLUMN: SUBTLE SPONSOR SHOWCASE
    with ad_showcase_col:
        st.markdown("#### 🌟 Featured Partners & Services")
        st.caption("Services recommended for property managers, landlords, and tenants across Ghana & West Africa.")
        
        # Render subtle paid sponsor banners
        render_public_ad_banners(ad_slot="Login Page Sidebar Banner")


# Stop unauthenticated users from accessing app dashboard
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
