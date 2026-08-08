"""
RentMaster-GH - Rental Property Management Web App
Main Entry Point & App Router with Strict Role-Based Navigation Filtering
"""
import os
import sys
import json
from datetime import datetime, timedelta

# 1. Add the root directory to sys.path FIRST
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. Third-party library imports
import streamlit as st
import extra_streamlit_components as stx

# 3. Streamlit Config (MUST BE CALLED BEFORE LOCAL UI/COMPONENT IMPORTS)
st.set_page_config(
    page_title="RentMaster-GH | Rental Property Management System",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 4. Local application imports
from services.helpers import (
    inject_google_analytics, inject_google_site_verification, get_user_role
)
from services.database import sb, clear_cache
from services.paystack import handle_paystack_callbacks
from components.ads import render_public_ad_banners
from components.public_showcase import (
    render_public_featured_properties,
    show_public_property_listing_dialog
)
from ui.pages_core import (
    header, show_support_dialog, page_dashboard,
    page_user_profile, page_settings
)
from ui.pages_management import (
    page_properties, page_landlords, page_tenants,
    page_payments, page_leases
)
from ui.tenant_portal import render_tenant_portal
from ui.sponsor_portal import render_sponsor_portal, show_sponsor_support_dialog

# Cookie Manager Instance
try:
    cookie_manager = stx.CookieManager(key="rentmaster_cookie_mgr")
except Exception:
    cookie_manager = None


def safe_get_cookie(cookie_name):
    if not cookie_manager: return None
    try: return cookie_manager.get(cookie=cookie_name)
    except Exception: return None


def safe_set_cookie(cookie_name, value, expires_at):
    if not cookie_manager: return
    try: cookie_manager.set(cookie_name, value, expires_at=expires_at)
    except Exception: pass


def safe_delete_cookie(cookie_name):
    if not cookie_manager: return
    try: cookie_manager.delete(cookie_name)
    except Exception: pass


# Inject Google Analytics & Site Verification
inject_google_analytics("G-EFD2P6FKM5")
inject_google_site_verification("SXu9dztavBBjKgrko60Tx2CjufX2KvyRhW42SOczZrc")

# Initialize Session State Defaults
if "user" not in st.session_state:
    st.session_state["user"] = None

if "app_currency" not in st.session_state:
    st.session_state["app_currency"] = "GHS"

# Persistent Cookie Auto-Login
if st.session_state.get("user") is None and sb:
    saved_session_cookie = safe_get_cookie("rentmaster_session")
    if saved_session_cookie:
        try:
            session_data = json.loads(saved_session_cookie) if isinstance(saved_session_cookie, str) else saved_session_cookie
            ref_token = session_data.get("refresh_token")
            acc_token = session_data.get("access_token")

            if ref_token and acc_token:
                res = sb.auth.set_session(acc_token, ref_token)
                if res and res.user:
                    st.session_state["user"] = res.user
        except Exception:
            safe_delete_cookie("rentmaster_session")

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


@st.dialog("📢 Self-Service Sponsor & Advertiser Hub", width="large")
def show_public_sponsor_launch_dialog():
    render_sponsor_portal()


# ---------------------------------------------------------------------------
# Role-Aware Authentication Screen
# ---------------------------------------------------------------------------
def auth_page():
    st.markdown(
        """
        <style>
            .auth-hero-banner {
                background: linear-gradient(135deg, #0f4c75 0%, #1b262c 50%, #3282b8 100%);
                padding: 2.2rem 2rem;
                border-radius: 16px;
                text-align: center;
                color: white;
                margin-bottom: 2rem;
                box-shadow: 0 12px 30px rgba(15, 76, 117, 0.18);
            }
            .auth-hero-banner h1 {
                color: #ffffff !important;
                font-size: 2.3rem !important;
                font-weight: 800 !important;
                margin-bottom: 0.4rem !important;
            }
            .paystack-quick-banner {
                background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
                border: 1px solid #a7f3d0;
                border-radius: 12px;
                padding: 1.1rem;
                text-align: center;
                margin-bottom: 1.2rem;
            }
            .paystack-quick-btn {
                display: inline-block;
                background-color: #059669;
                color: white !important;
                font-weight: 700;
                padding: 10px 22px;
                border-radius: 8px;
                text-decoration: none;
                font-size: 0.9rem;
            }
            div[data-testid="stButton"] button:has(p:contains("Launch Advert")),
            div[data-testid="stButton"] button:has(span:contains("Launch Advert")),
            div[data-testid="stButton"] button:has(div:contains("Launch Advert")) {
                background-color: #16a34a !important;
                border-color: #16a34a !important;
                color: #ffffff !important;
                font-weight: 700 !important;
            }
            .feature-pill {
                display: inline-block;
                background-color: #f1f5f9;
                border: 1px solid #e2e8f0;
                color: #334155;
                font-size: 0.8rem;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 20px;
                margin-right: 6px;
                margin-bottom: 8px;
            }
            .trust-bar {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 1.8rem;
                margin-top: 2rem;
                padding-top: 1.2rem;
                border-top: 1px solid #e2e8f0;
                color: #64748b;
                font-size: 0.85rem;
                font-weight: 500;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="auth-hero-banner">
            <h1>🏠 RentMaster-GH Enterprise</h1>
            <p>Smart Rental Property Management System &middot; Landlord & Tenant Portals &middot; Split Payouts &middot; Ghana Rent Cards</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    login_col, ad_showcase_col = st.columns([1.2, 1], gap="large")

    with login_col:
        with st.container(border=True):
            st.markdown(
                """
                <div class="paystack-quick-banner">
                    <p>💡 Tenant or Sponsor making a payment without logging in?</p>
                    <a href="https://paystack.shop/pay/zvx0npq7hv" target="_blank" rel="noopener noreferrer" class="paystack-quick-btn">
                        💙 Quick Pay / Support via Paystack
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<h3 style='text-align: center; margin-bottom: 1rem; color: #0f4c75;'>Account Access</h3>", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🔒 Log In", "📝 Sign Up"])
            redirect_url = "https://www.rentmastergh.com"

            with tab1:
                email = st.text_input("Email Address", key="login_email", placeholder="user@example.com")
                password = st.text_input("Password", type="password", key="login_pw")
                remember_me = st.checkbox("Keep me logged in (30 Days)", value=True, key="login_remember_me")

                if st.button("Log In to Account", use_container_width=True, key="login_btn", type="primary"):
                    if not sb:
                        st.error("Database connection missing.")
                    else:
                        try:
                            res = sb.auth.sign_in_with_password({"email": email, "password": password})
                            if res.user:
                                st.session_state["user"] = res.user
                                st.session_state["remember_me"] = remember_me
                                st.session_state.pop("current_page", None)
                                st.session_state.pop("user_role_override", None)

                                if res.session and remember_me:
                                    expires_at = datetime.now() + timedelta(days=30)
                                    cookie_data = json.dumps({
                                        "refresh_token": res.session.refresh_token,
                                        "access_token": res.session.access_token,
                                        "user_email": res.user.email
                                    })
                                    safe_set_cookie("rentmaster_session", cookie_data, expires_at=expires_at)
                                
                                clear_cache()
                                st.rerun()
                        except Exception as e:
                            st.error(f"Login Error: {e}")

                st.divider()

                if sb:
                    try:
                        res = sb.auth.sign_in_with_oauth({
                            "provider": "google",
                            "options": {"redirect_to": redirect_url}
                        })
                        if res.url:
                            st.markdown(
                                f"""
                                <a href="{res.url}" target="_self" style="display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 11px; border: 1px solid #dadce0; border-radius: 8px; background-color: white; color: #3c4043; font-weight: 600; text-decoration: none; box-sizing: border-box; font-size: 0.92rem;">
                                    <img src="https://www.gstatic.com/images/branding/product/1x/gsa_64dp.png" width="18" height="18"> Continue with Google
                                </a>
                                """,
                                unsafe_allow_html=True
                            )
                    except Exception as e:
                        st.error(f"Google OAuth error: {e}")

            with tab2:
                new_email = st.text_input("Email Address", key="signup_email", placeholder="user@example.com")
                confirm_email = st.text_input("Confirm Email Address", key="confirm_email")
                new_password = st.text_input("Create Password", type="password", key="signup_pw")
                confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pw")

                role_choice = st.radio(
                    "Account Type / Role *",
                    ["🏠 Landlord / Property Manager", "👤 Tenant"],
                    horizontal=True,
                    key="signup_role_choice"
                )
                selected_role = "landlord" if "Landlord" in role_choice else "tenant"

                if st.button("Create Account", use_container_width=True, key="signup_btn", type="primary"):
                    if new_email != confirm_email:
                        st.error("Email addresses do not match.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif not sb:
                        st.error("Database connection missing.")
                    else:
                        try:
                            sb.auth.sign_up({
                                "email": new_email,
                                "password": new_password,
                                "options": {
                                    "data": {
                                        "role": selected_role
                                    }
                                }
                            })
                            st.success(f"✅ Account created as **{selected_role.title()}**! Check your email inbox to confirm registration.")
                        except Exception as e:
                            st.error(f"Sign Up Error: {e}")

    with ad_showcase_col:
        with st.container(border=True):
            st.markdown("#### 📢 Promote & List Properties")
            st.caption("Promote your business or list your vacant property for rent (GH₵ 50 / $5) to visitors across Ghana.")
            
            c_btn1, c_btn2, c_btn3 = st.columns(3)
            with c_btn1:
                if st.button("🚀 Launch Advert", use_container_width=True, type="primary"):
                    show_public_sponsor_launch_dialog()
            with c_btn2:
                if st.button("🏠 List Property", use_container_width=True, type="secondary"):
                    show_public_property_listing_dialog()
            with c_btn3:
                if st.button("💬 Manager", use_container_width=True, type="secondary"):
                    show_sponsor_support_dialog()

        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("#### ⚡ Platform Features")
            st.markdown(
                """
                <div style="margin-bottom: 0.5rem;">
                    <span class="feature-pill">💳 Paystack Split Payouts</span>
                    <span class="feature-pill">📋 Ghana Rent Cards</span>
                    <span class="feature-pill">🆔 Live Camera KYC</span>
                    <span class="feature-pill">📱 WhatsApp Reminders</span>
                    <span class="feature-pill">📄 PDF Rent Receipts</span>
                    <span class="feature-pill">🌍 Multi-Currency (GHS/USD/EUR)</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)
        render_public_ad_banners(ad_slot="Login Page Sidebar Banner")

    render_public_featured_properties()

    st.markdown(
        """
        <div class="trust-bar">
            <span>🔒 256-Bit SSL Encrypted</span>
            <span>🛡️ Data Protection Act (Act 843) Compliant</span>
            <span>⚡ Powered by Supabase & Paystack</span>
        </div>
        """,
        unsafe_allow_html=True
    )


# Stop unauthenticated users from accessing app dashboard
if st.session_state.get("user") is None:
    auth_page()
    st.stop()


# ---------------------------------------------------------------------------
# STRICT ROLE-BASED NAVIGATION ROUTER
# ---------------------------------------------------------------------------
active_user = st.session_state.get("user")
user_role = get_user_role(active_user)

# Strictly define allowed navigation items per role
if user_role == "tenant":
    PAGES = {
        "Tenant Portal": render_tenant_portal,
        "User Profile": page_user_profile,
        "Settings": page_settings,
        "Sponsor Portal": render_sponsor_portal,
    }
else:  # Landlord / Property Manager View ('Maintenance' EXCLUDED)
    PAGES = {
        "Dashboard": page_dashboard,
        "User Profile": page_user_profile,
        "Properties": page_properties,
        "Landlords": page_landlords,
        "Tenants": page_tenants,
        "Payments": page_payments,
        "Leases": page_leases,
        "Settings": page_settings,
        "Sponsor Portal": render_sponsor_portal,
    }

# Auto-set default page if none selected or invalid for current role
nav_keys = list(PAGES.keys())
if "current_page" not in st.session_state or st.session_state["current_page"] not in nav_keys:
    st.session_state["current_page"] = "Tenant Portal" if user_role == "tenant" else "Dashboard"

with st.sidebar:
    st.markdown(f"### Navigation ({user_role.title()} View)")
    
    default_index = nav_keys.index(st.session_state["current_page"])
    selection = st.radio("Go to", nav_keys, index=default_index)
    st.session_state["current_page"] = selection

    # 1-CLICK ROLE VIEW SWITCHER
    st.markdown("---")
    st.caption("🔄 Switch View Mode")
    target_switch = "landlord" if user_role == "tenant" else "tenant"
    if st.button(f"Switch to {target_switch.title()} View", use_container_width=True, type="secondary"):
        st.session_state["user_role_override"] = target_switch
        st.session_state.pop("current_page", None)
        st.rerun()

    st.markdown("---")
    if st.button("💬 Support & Suggestions", use_container_width=True):
        show_support_dialog()
    st.markdown("---")
    
    if active_user:
        st.write(f"👤 Logged in: **{getattr(active_user, 'email', 'User')}**")
        st.caption(f"Active View: `{user_role.title()}`")
        if st.button("Logout", key="logout_btn"):
            safe_delete_cookie("rentmaster_session")
            if sb: sb.auth.sign_out()
            st.session_state.clear()
            st.rerun()

# Execute Active Page View
PAGES[st.session_state["current_page"]]()
