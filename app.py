"""
RentMaster-GH - Rental Property Management Web App
Main Entry Point & App Router with Automatic Role-Based Portal Filtering
"""
import os
import sys
import json
from datetime import datetime, timedelta

# 1. Add the root directory to sys.path FIRST
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. Third-party library imports
import streamlit as st
import streamlit.components.v1 as components
import extra_streamlit_components as stx

# 3. Streamlit Config (MUST BE CALLED BEFORE ANY OTHER STREAMLIT COMMANDS OR LOCAL UI IMPORTS)
st.set_page_config(
    page_title="RentMaster-GH | Rental Property Management System",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# GOOGLE SITE VERIFICATION + GTM INJECTION
components.html(
    """
    <!-- Google Site Verification - HTML TAG METHOD -->
    <meta name="google-site-verification" content="25ade72139f11424" />

    <!-- Google Tag Manager -->
    <script>
    (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
    new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
    j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
    'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
    })(window,document,'script','dataLayer','GTM-M8WLPHJW');
    </script>
    <!-- End Google Tag Manager -->

    <!-- Google Tag Manager (noscript) -->
    <noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-M8WLPHJW"
    height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
    <!-- End Google Tag Manager (noscript) -->
    """,
    height=0,
    width=0,
)

# 3.5 INJECT GTM + GA4 + SITE VERIFICATION (<head> & <body> NOSCRIPT)
components.html(
    """
    <script>
    (function() {
        try {
            var head = window.parent.document.head;
            var body = window.parent.document.body;
            
            // 1. Inject Google Tag Manager (GTM-M8WLPHJW) into <head>
            if (!window.parent.document.getElementById('gtm-script')) {
                var gtmInit = window.parent.document.createElement('script');
                gtmInit.id = 'gtm-init';
                gtmInit.innerHTML = `
                    window.dataLayer = window.dataLayer || [];
                    window.dataLayer.push({'gtm.start': new Date().getTime(), event: 'gtm.js'});
                `;
                head.appendChild(gtmInit);

                var gtmScript = window.parent.document.createElement('script');
                gtmScript.id = 'gtm-script';
                gtmScript.async = true;
                gtmScript.src = 'https://www.googletagmanager.com/gtm.js?id=GTM-M8WLPHJW';
                head.appendChild(gtmScript);
            }

            // 2. Inject GTM <noscript> iframe immediately after opening <body> tag
            if (!window.parent.document.getElementById('gtm-noscript')) {
                var noscript = window.parent.document.createElement('noscript');
                noscript.id = 'gtm-noscript';
                
                var iframe = window.parent.document.createElement('iframe');
                iframe.src = 'https://www.googletagmanager.com/ns.html?id=GTM-M8WLPHJW';
                iframe.height = '0';
                iframe.width = '0';
                iframe.style.display = 'none';
                iframe.style.visibility = 'hidden';
                
                noscript.appendChild(iframe);
                body.insertBefore(noscript, body.firstChild);
            }

            // 3. Inject Google Analytics 4 (G-4SEHLP8VTN)
            if (!window.parent.document.getElementById('ga-gtag-js')) {
                var gaScript = window.parent.document.createElement('script');
                gaScript.id = 'ga-gtag-js';
                gaScript.async = true;
                gaScript.src = 'https://www.googletagmanager.com/gtag/js?id=G-4SEHLP8VTN';
                head.appendChild(gaScript);

                var gaInit = window.parent.document.createElement('script');
                gaInit.id = 'ga-gtag-init';
                gaInit.innerHTML = `
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    gtag('js', new Date());
                    gtag('config', 'G-4SEHLP8VTN');
                `;
                head.appendChild(gaInit);
            }

            // 4. Inject Google Site Verification Meta Tag
            if (!window.parent.document.querySelector('meta[name="google-site-verification"]')) {
                var meta = window.parent.document.createElement('meta');
                meta.name = 'google-site-verification';
                meta.content = 'vFWqfkLEFQARiYcF9r1M5FKhC6aQZD7P_LUli5fVN_M';
                head.appendChild(meta);
            }
        } catch (e) {
            console.error("Head/Body Injection Error:", e);
        }
    })();
    </script>
    """,
    height=0,
    width=0,
)

# 4. Local application imports
from services.helpers import get_user_role
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


# Initialize Session State Defaults
if "user" not in st.session_state:
    st.session_state["user"] = None

if "app_currency" not in st.session_state:
    st.session_state["app_currency"] = "GHS"


def resolve_user_active_role(user):
    """
    Precision Role Resolver: Automatically detects whether the logged in user is:
    1. prospective_tenant
    2. tenant (active)
    3. landlord / property_manager
    """
    if not user:
        return "prospective_tenant"
    
    # 1. Manual user override via view switcher
    if st.session_state.get("user_role_override"):
        return st.session_state["user_role_override"]

    # 2. Inspect metadata attached to Supabase Auth user
    meta = getattr(user, "user_metadata", {}) or {}
    role = meta.get("role") or get_user_role(user)
    subtype = meta.get("account_subtype")

    if role == "landlord" or role == "property_manager":
        return "landlord"
    elif role == "tenant":
        if subtype == "prospective":
            return "prospective_tenant"
        return "tenant"

    # 3. Fallback database lookup
    db_role = get_user_role(user)
    if db_role in ["prospective_tenant", "tenant", "landlord"]:
        return db_role

    return "landlord"


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
            st.session_state.pop("user_role_override", None)
            st.session_state.pop("current_page", None)
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
                background: linear-gradient(135deg, #111827 0%, #1f2937 50%, #111827 100%);
                padding: 2.2rem 2rem;
                border-radius: 16px;
                text-align: center;
                color: white;
                margin-bottom: 2rem;
                box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
                border-bottom: 3px solid #f59e0b;
            }
            .auth-hero-banner h1 {
                color: #ffffff !important;
                font-size: 2.3rem !important;
                font-weight: 800 !important;
                margin-bottom: 0.4rem !important;
            }
            .auth-hero-banner p {
                color: #d1d5db !important;
            }
            .paystack-quick-banner {
                background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%);
                border: 1px solid #fecdd3;
                border-radius: 12px;
                padding: 1.1rem;
                text-align: center;
                margin-bottom: 1.2rem;
                color: #9f1239;
            }
            .paystack-quick-btn {
                display: inline-block;
                background-color: #e11d48;
                color: white !important;
                font-weight: 700;
                padding: 10px 22px;
                border-radius: 8px;
                text-decoration: none;
                font-size: 0.9rem;
                transition: all 0.2s ease;
            }
            .paystack-quick-btn:hover {
                background-color: #be123c !important;
            }
            /* AMBER GOLD LOGIN BUTTON & ACCENT STYLING */
            div[data-testid="stFormSubmitButton"] button {
                background-color: #f59e0b !important;
                border-color: #f59e0b !important;
                color: #ffffff !important;
                font-weight: 800 !important;
            }
            div[data-testid="stFormSubmitButton"] button:hover {
                background-color: #d97706 !important;
                border-color: #d97706 !important;
            }
            .feature-pill {
                display: inline-block;
                background-color: #fffbeb;
                border: 1px solid #fef3c7;
                color: #b45309;
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
                border-top: 1px solid #374151;
                color: #9ca3af;
                font-size: 0.85rem;
                font-weight: 500;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Autofill attributes helper script
    components.html(
        """
        <script>
            setTimeout(function() {
                try {
                    const inputs = window.parent.document.querySelectorAll('input[type="text"]');
                    inputs.forEach(i => i.setAttribute('autocomplete', 'username'));
                    const pwInputs = window.parent.document.querySelectorAll('input[type="password"]');
                    pwInputs.forEach(i => i.setAttribute('autocomplete', 'current-password'));
                } catch(e){}
            }, 800);
        </script>
        """,
        height=0,
        width=0
    )

    st.markdown(
        """
        <div class="auth-hero-banner">
            <h1>🏠 RentMaster-GH Enterprise</h1>
            <p>Smart Rental Property Management System &middot; Landlord & Tenant Portals &middot; Split Payouts</p>
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
                    <p style="margin-bottom: 0.6rem; font-weight: 600;">💡 Tenant or Sponsor making a payment without logging in?</p>
                    <a href="https://paystack.shop/pay/zvx0npq7hv" target="_blank" rel="noopener noreferrer" class="paystack-quick-btn">
                        💖 Quick Pay / Support via Paystack
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("<h3 style='text-align: center; margin-bottom: 1rem; color: #f59e0b;'>Account Access</h3>", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🔒 Log In", "📝 Sign Up"])
            redirect_url = "https://www.rentmastergh.com"

            with tab1:
                with st.form("login_credentials_form", clear_on_submit=False):
                    email = st.text_input("Email Address", key="login_email", placeholder="user@example.com")
                    password = st.text_input("Password", type="password", key="login_pw")
                    remember_me = st.checkbox("Keep me logged in (30 Days)", value=True, key="login_remember_me")

                    login_submitted = st.form_submit_button("Log In to Account", use_container_width=True, type="primary")

                    if login_submitted:
                        clean_email = email.strip() if email else ""
                        clean_password = password.strip() if password else ""

                        if not clean_email or not clean_password:
                            st.error("Please enter both email address and password.")
                        elif not sb:
                            st.error("Database connection missing.")
                        else:
                            try:
                                res = sb.auth.sign_in_with_password({"email": clean_email, "password": clean_password})
                                if res.user:
                                    st.session_state["user"] = res.user
                                    st.session_state["remember_me"] = remember_me
                                    # Reset override to ensure automatic role detection
                                    st.session_state.pop("user_role_override", None)
                                    st.session_state.pop("current_page", None)

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
                    [
                        "🏠 Landlord / Property Manager", 
                        "🔍 Prospective Tenant (Looking for Property)",
                        "👤 Active Tenant (Already Renting)"
                    ],
                    horizontal=False,
                    key="signup_role_choice"
                )
                
                # Precise role extraction
                if "Landlord" in role_choice:
                    selected_role = "landlord"
                    account_subtype = "manager"
                elif "Prospective" in role_choice:
                    selected_role = "tenant"
                    account_subtype = "prospective"
                else:
                    selected_role = "tenant"
                    account_subtype = "active"

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
                            res = sb.auth.sign_up({
                                "email": new_email,
                                "password": new_password,
                                "options": {
                                    "data": {
                                        "role": selected_role,
                                        "account_subtype": account_subtype
                                    }
                                }
                            })
                            st.success(f"✅ Account created as **{role_choice}**! Check your email inbox to confirm registration.")
                        except Exception as e:
                            st.error(f"Sign Up Error: {e}")

    with ad_showcase_col:
        with st.container(border=True):
            st.markdown("#### 📢 Promote & List Properties")
            st.caption("Promote your business or list your vacant property for rent (GH₵ 50 / $5) to visitors across the world.")
            
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
# AUTOMATIC ROLE-BASED NAVIGATION ROUTER WITH VIEW MODE SWITCHER
# ---------------------------------------------------------------------------
active_user = st.session_state.get("user")
active_view_role = resolve_user_active_role(active_user)

# Strictly define allowed navigation items per active view
if active_view_role == "prospective_tenant":
    PAGES = {
        "Tenant Portal": render_tenant_portal,
        "User Profile": page_user_profile,
        "Settings": page_settings,
        "Sponsor Portal": render_sponsor_portal,
    }
elif active_view_role in ["tenant", "active_tenant"]:
    PAGES = {
        "Tenant Portal": render_tenant_portal,
        "User Profile": page_user_profile,
        "Settings": page_settings,
        "Sponsor Portal": render_sponsor_portal,
    }
else:  # Landlord / Property Manager View
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
    st.session_state["current_page"] = "Tenant Portal" if active_view_role in ["tenant", "prospective_tenant"] else "Dashboard"

with st.sidebar:
    # Role Badge Display
    role_titles = {
        "prospective_tenant": "🔍 Prospective Tenant",
        "tenant": "👤 Active Tenant",
        "landlord": "🏠 Landlord / Manager"
    }
    display_role = role_titles.get(active_view_role, "🏠 Landlord / Manager")
    
    st.markdown(f"### Portal View")
    st.info(f"Active Mode: **{display_role}**")
    
    default_index = nav_keys.index(st.session_state["current_page"])
    selection = st.radio("Go to", nav_keys, index=default_index)
    st.session_state["current_page"] = selection

    # 3-WAY VIEW MODE SWITCHER
    st.markdown("---")
    st.caption("🔄 Switch Active View Mode")

    view_modes = [
        "🏠 Landlord / Manager View",
        "👤 Active Tenant View",
        "🔍 Prospective Tenant View"
    ]

    current_mode_idx = 0
    if active_view_role == "prospective_tenant":
        current_mode_idx = 2
    elif active_view_role in ["tenant", "active_tenant"]:
        current_mode_idx = 1

    selected_mode = st.selectbox("Select View Mode", view_modes, index=current_mode_idx, key="active_view_mode_select")

    override_mode = st.session_state.get("user_role_override")
    if "Prospective" in selected_mode and override_mode != "prospective_tenant":
        st.session_state["user_role_override"] = "prospective_tenant"
        st.session_state.pop("current_page", None)
        st.rerun()
    elif "Active Tenant" in selected_mode and override_mode != "tenant":
        st.session_state["user_role_override"] = "tenant"
        st.session_state.pop("current_page", None)
        st.rerun()
    elif "Landlord" in selected_mode and override_mode != "landlord":
        st.session_state["user_role_override"] = "landlord"
        st.session_state.pop("current_page", None)
        st.rerun()

    st.markdown("---")
    if st.button("💬 Support & Suggestions", use_container_width=True):
        show_support_dialog()
    st.markdown("---")
    
    if active_user:
        st.write(f"👤 Logged in: **{getattr(active_user, 'email', 'User')}**")
        if st.button("Logout", key="logout_btn"):
            safe_delete_cookie("rentmaster_session")
            if sb: sb.auth.sign_out()
            st.session_state.clear()
            st.rerun()

# Execute Active Page View
PAGES[st.session_state["current_page"]]()
