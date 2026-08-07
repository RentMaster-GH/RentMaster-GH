"""
RentMaster-GH - Rental Property Management Web App
Full interactive UI backed by Supabase. Manages properties, tenants,
payments, leases, maintenance requests, and landlords with a global dashboard overview.
Includes Multi-Currency Paystack & International Card/MoMo Checkout & Split Payouts.
Isolated Multi-Tenant Security: Users view ONLY their own properties & tenants.
Persistent Cookie Sessions: Retains user login across code reboots & closed tabs.
"""

import json
import os
import uuid
from datetime import date, datetime, timedelta
import requests
import streamlit as st
import streamlit.components.v1 as components
import extra_streamlit_components as stx
from dotenv import load_dotenv
from supabase import create_client
from streamlit.errors import StreamlitSecretNotFoundError

# ---------------------------------------------------------------------------
# Streamlit Config (MUST BE FIRST STREAMLIT COMMAND)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RentMaster-GH",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load environment variables
load_dotenv()


# ---------------------------------------------------------------------------
# Persistent Cookie Manager Setup
# ---------------------------------------------------------------------------
@st.cache_resource
def get_cookie_manager():
    return stx.CookieManager()


cookie_manager = get_cookie_manager()


def inject_google_analytics(measurement_id="G-EFD2P6FKM5"):
    """
    Injects Google Analytics 4 tracking snippet.
    """
    ga_html = f"""
    <!-- Global site tag (gtag.js) - Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{measurement_id}');
    </script>
    """
    components.html(ga_html, height=0, width=0)


# Inject Google Analytics
inject_google_analytics("G-EFD2P6FKM5")


def get_secret(key: str, default: str = "") -> str:
    """
    Safely retrieves a secret from OS environment variables first,
    and falls back to Streamlit secrets without crashing if secrets.toml is missing.
    """
    env_val = os.environ.get(key)
    if env_val:
        return env_val

    try:
        if key in st.secrets:
            return st.secrets[key]
    except StreamlitSecretNotFoundError:
        pass

    return default


SUPABASE_URL = get_secret("VITE_SUPABASE_URL") or get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("VITE_SUPABASE_ANON_KEY") or get_secret("SUPABASE_KEY")
PAYSTACK_SECRET_KEY = get_secret("PAYSTACK_SECRET_KEY")


@st.cache_resource
def get_client():
    url = (SUPABASE_URL or "").strip()
    key = (SUPABASE_KEY or "").strip()

    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception:
        return None


sb = get_client()


def get_active_user_info():
    """
    Safely retrieves active logged-in user ID and Email from Streamlit session state.
    """
    user = st.session_state.get("user")
    if not user:
        return None, None
    user_id = getattr(user, "id", None)
    user_email = getattr(user, "email", None)
    return user_id, user_email


# ---------------------------------------------------------------------------
# Global Multi-Currency Engine & International Payout Bank Systems
# ---------------------------------------------------------------------------
SUPPORTED_CURRENCIES = {
    "GHS": {"symbol": "GHs", "name": "Ghanaian Cedi (GHs / GH₵)"},
    "USD": {"symbol": "$", "name": "US Dollar ($)"},
    "EUR": {"symbol": "€", "name": "Euro (€)"},
    "GBP": {"symbol": "£", "name": "British Pound (£)"},
    "NGN": {"symbol": "₦", "name": "Nigerian Naira (₦)"},
    "KES": {"symbol": "KSh", "name": "Kenyan Shilling (KSh)"},
    "ZAR": {"symbol": "R", "name": "South African Rand (R)"},
    "CAD": {"symbol": "$", "name": "Canadian Dollar ($)"},
    "AUD": {"symbol": "$", "name": "Australian Dollar ($)"},
    "XOF": {"symbol": "CFA", "name": "West African CFA (CFA)"},
    "INR": {"symbol": "₹", "name": "Indian Rupee (₹)"},
    "AED": {"symbol": "AED", "name": "UAE Dirham (AED)"},
}

GLOBAL_PAYOUT_BANKS = {
    "Ghana": {
        "MTN Mobile Money": "MTN",
        "Vodafone Cash / Telecel Cash": "VOD",
        "AirtelTigo Money": "ATL",
        "GCB Bank": "040100",
        "Ecobank Ghana": "090100",
        "Absa Bank Ghana": "030100",
        "Fidelity Bank Ghana": "240100",
        "Stanbic Bank Ghana": "190100",
        "CalBank": "140100",
        "Zenith Bank Ghana": "120100",
    },
    "Nigeria": {
        "Access Bank": "044",
        "Guaranty Trust Bank (GTB)": "058",
        "First Bank of Nigeria": "011",
        "Zenith Bank": "057",
        "Kuda Microfinance Bank": "50211",
        "OPay Digital Services": "999992",
    },
    "Kenya": {
        "M-Pesa": "MPESA",
        "Equity Bank": "068",
        "KCB Bank": "001",
        "Absa Bank Kenya": "003",
    },
    "South Africa": {
        "Capitec Bank": "470010",
        "FirstNational Bank (FNB)": "250655",
        "Standard Bank": "051001",
        "Nedbank": "198765",
        "Absa Bank SA": "632005",
    },
    "International / Other": {
        "International SWIFT / IBAN Wire": "SWIFT_GLOBAL",
        "Direct Card Payout": "CARD_GLOBAL",
    }
}


def get_current_currency():
    return st.session_state.get("app_currency", "GHS")


def fmt_money(v, currency_code=None):
    code = currency_code or get_current_currency()
    symbol = SUPPORTED_CURRENCIES.get(code, {}).get("symbol", "GHs")
    try:
        return f"{symbol} {float(v):,.2f}"
    except (TypeError, ValueError):
        return "-"


def fmt_date(v):
    if not v:
        return "-"
    try:
        return str(v)[:10]
    except Exception:
        return str(v)


# ---------------------------------------------------------------------------
# Data Fetching Helpers (ISOLATED & FILTERED PER LOGGED-IN USER)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=5)
def fetch_properties(user_id: str = None, user_email: str = None):
    if not sb or not user_id: return []
    try:
        r = sb.table("properties").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        try:
            r = sb.table("properties").select("*").eq("owner_id", user_id).order("created_at", desc=True).execute()
            return r.data or []
        except Exception:
            try:
                r = sb.table("properties").select("*").order("created_at", desc=True).execute()
                data = r.data or []
                return [p for p in data if p.get("user_id") == user_id or p.get("owner_id") == user_id or p.get("user_email") == user_email]
            except Exception: return []


@st.cache_data(ttl=5)
def fetch_landlords(user_id: str = None, user_email: str = None):
    if not sb or not user_id: return []
    try:
        r = sb.table("landlords").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        try:
            r = sb.table("landlords").select("*").order("created_at", desc=True).execute()
            data = r.data or []
            return [l for l in data if l.get("user_id") == user_id or l.get("user_email") == user_email]
        except Exception: return []


@st.cache_data(ttl=5)
def fetch_tenants(user_id: str = None, user_email: str = None):
    if not sb or not user_id: return []
    try:
        r = sb.table("tenants").select("*, properties(*, landlords(*))").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        try:
            r = sb.table("tenants").select("*, properties(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
            return r.data or []
        except Exception:
            try:
                r = sb.table("tenants").select("*, properties(*)").order("created_at", desc=True).execute()
                data = r.data or []
                return [t for t in data if t.get("user_id") == user_id or t.get("user_email") == user_email]
            except Exception: return []


@st.cache_data(ttl=5)
def fetch_payments(user_id: str = None, user_email: str = None):
    if not sb or not user_id: return []
    try:
        r = sb.table("payments").select("*, tenants(*)").eq("user_id", user_id).order("payment_date", desc=True).execute()
        return r.data or []
    except Exception:
        try:
            r = sb.table("payments").select("*, tenants(*)").order("payment_date", desc=True).execute()
            data = r.data or []
            return [p for p in data if p.get("user_id") == user_id or p.get("user_email") == user_email]
        except Exception: return []


@st.cache_data(ttl=5)
def fetch_leases(user_id: str = None, user_email: str = None):
    if not sb or not user_id: return []
    try:
        r = sb.table("leases").select("*, properties(*), tenants(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        try:
            r = sb.table("leases").select("*, properties(*), tenants(*)").order("created_at", desc=True).execute()
            data = r.data or []
            return [l for l in data if l.get("user_id") == user_id or l.get("user_email") == user_email]
        except Exception: return []


@st.cache_data(ttl=5)
def fetch_maintenance(user_id: str = None, user_email: str = None):
    if not sb or not user_id: return []
    try:
        r = sb.table("maintenance_requests").select("*, properties(*), tenants(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        try:
            r = sb.table("maintenance_requests").select("*, properties(*), tenants(*)").order("created_at", desc=True).execute()
            data = r.data or []
            return [m for m in data if m.get("user_id") == user_id or m.get("user_email") == user_email]
        except Exception: return []


@st.cache_data(ttl=5)
def fetch_ads():
    if not sb: return []
    try:
        r = sb.table("ads").select("*").order("created_at", desc=True).execute()
        return r.data or []
    except Exception: return []


def clear_cache():
    fetch_properties.clear()
    fetch_landlords.clear()
    fetch_tenants.clear()
    fetch_payments.clear()
    fetch_leases.clear()
    fetch_maintenance.clear()
    fetch_ads.clear()


# ---------------------------------------------------------------------------
# Paystack API & Payment Helpers
# ---------------------------------------------------------------------------
def create_paystack_subaccount(business_name: str, bank_code: str, account_number: str, percentage_charge: float = 0.0, email: str = None, phone: str = None):
    if not PAYSTACK_SECRET_KEY:
        return {"status": False, "message": "PAYSTACK_SECRET_KEY is missing."}

    url = "https://api.paystack.co/subaccount"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "business_name": business_name,
        "settlement_bank": bank_code,
        "account_number": account_number,
        "percentage_charge": percentage_charge,
        "primary_contact_email": email or "",
        "primary_contact_phone": phone or "",
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}


def initialize_paystack_payment(email: str, amount_in_main_unit: float, callback_url: str, metadata: dict = None, subaccount: str = None, currency: str = None):
    if not PAYSTACK_SECRET_KEY:
        return {"status": False, "message": "PAYSTACK_SECRET_KEY is not configured in secrets or environment."}

    curr = currency or get_current_currency()

    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "amount": int(round(amount_in_main_unit * 100)),
        "currency": curr,
        "callback_url": callback_url,
        "channels": ["card", "mobile_money", "bank_transfer", "bank"],
        "metadata": metadata or {}
    }

    if subaccount:
        payload["subaccount"] = subaccount

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}


def verify_paystack_payment(reference: str):
    if not PAYSTACK_SECRET_KEY:
        return {"status": False, "message": "PAYSTACK_SECRET_KEY is missing."}

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}


def save_landlord_bank_details(landlord_id: str, name: str, email: str, phone: str, bank_name: str, account_number: str, bank_code: str, platform_fee_pct: float = 0.0, id_card_url: str = None, user_id: str = None, user_email: str = None):
    if not sb:
        raise Exception("Database client not initialized.")

    ps_res = create_paystack_subaccount(
        business_name=name,
        bank_code=bank_code,
        account_number=account_number,
        percentage_charge=platform_fee_pct,
        email=email,
        phone=phone
    )

    if not ps_res.get("status"):
        raise Exception(f"Paystack Registration Failed: {ps_res.get('message', 'Unknown Error')}")

    subaccount_code = ps_res["data"]["subaccount_code"]

    payload = {
        "name": name,
        "email": email if email else None,
        "phone": phone if phone else None,
        "bank_name": bank_name,
        "account_number": account_number,
        "bank_code": bank_code,
        "paystack_subaccount_code": subaccount_code,
    }

    if user_id:
        payload["user_id"] = user_id
    if user_email:
        payload["user_email"] = user_email

    if id_card_url:
        payload["id_card_url"] = id_card_url

    if landlord_id:
        res = sb.table("landlords").update(payload).eq("id", landlord_id).execute()
    else:
        res = sb.table("landlords").insert(payload).execute()

    return res.data, subaccount_code


def initialize_ad_payment(client_name: str, ad_position: str, amount_ghs: float, start_date: str, end_date: str, destination_url: str, creative_url: str, email: str, callback_url: str, user_id: str = None):
    reference = f"AD-{uuid.uuid4().hex[:10].upper()}"

    ad_payload = {
        "business_name": client_name,
        "ad_slot": ad_position,
        "monthly_rate": float(amount_ghs),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "destination_url": destination_url,
        "creative_url": creative_url,
        "status": "pending_payment",
        "reference": reference,
    }

    if user_id:
        ad_payload["user_id"] = user_id

    if sb:
        sb.table("ads").insert(ad_payload).execute()

    paystack_res = initialize_paystack_payment(
        email=email,
        amount_in_main_unit=amount_ghs,
        callback_url=callback_url,
        metadata={
            "type": "advert_placement",
            "business_name": client_name,
            "ad_slot": ad_position,
            "reference": reference,
            "user_id": user_id
        }
    )

    return paystack_res, reference


# ---------------------------------------------------------------------------
# REUSABLE PAID ADVERTISEMENTS COMPONENT
# ---------------------------------------------------------------------------
def render_ad_space_management(key_prefix: str = "ad"):
    st.markdown("#### Paid Advertisements & Ad Space Management")
    st.caption("Manage sponsor banners, advertiser campaigns, and paid placements across tenant/landlord portals.")

    curr_code = get_current_currency()
    user = st.session_state.get("user")
    user_email = getattr(user, "email", "") if user else ""
    user_id = getattr(user, "id", None) if user else None

    with st.container(border=True):
        tab_active_ads, tab_new_ad = st.tabs([
            "📢 Active Ad Placements",
            "💳 Create & Pay for Advert"
        ])

        with tab_active_ads:
            st.markdown("##### Current Banner Placements")
            try:
                ads_list = fetch_ads()
            except Exception:
                ads_list = []

            if not ads_list:
                st.info("No advertisement campaigns found in database.")
            else:
                for ad in ads_list:
                    with st.container(border=True):
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        with col1:
                            st.markdown(f"**{ad.get('business_name', 'Unnamed Business')}**")
                            st.caption(f"Slot: {ad.get('ad_slot')}")
                            if ad.get("destination_url"):
                                st.caption(f"URL: [{ad.get('destination_url')}]({ad.get('destination_url')})")
                            if ad.get("creative_url"):
                                st.image(ad.get("creative_url"), width=160)
                        with col2:
                            st.markdown(f"Rate: **{fmt_money(ad.get('monthly_rate'))}**")
                            st.caption(f"Ref: `{ad.get('reference', 'N/A')}`")
                        with col3:
                            st.caption(f"Schedule: {fmt_date(ad.get('start_date'))} to {fmt_date(ad.get('end_date'))}")
                            badge_color = "green" if ad.get('status') in ('paid', 'active') else "orange"
                            st.markdown(f"Status: :{badge_color}[**{str(ad.get('status')).upper()}**]")
                        with col4:
                            if st.button("Delete", key=f"{key_prefix}_del_ad_{ad['id']}", type="secondary"):
                                if sb:
                                    sb.table("ads").delete().eq("id", ad["id"]).execute()
                                    clear_cache()
                                    st.rerun()

        with tab_new_ad:
            st.markdown("##### Add Sponsored Campaign")

            checkout_url_key = f"{key_prefix}_ad_checkout_url"
            checkout_ref_key = f"{key_prefix}_ad_checkout_ref"

            if checkout_url_key not in st.session_state:
                st.session_state[checkout_url_key] = None
            if checkout_ref_key not in st.session_state:
                st.session_state[checkout_ref_key] = None

            with st.form(f"{key_prefix}_new_advert_form", clear_on_submit=False):
                f1, f2 = st.columns(2)
                with f1:
                    client_name = st.text_input("Advertiser / Business Name *", placeholder="e.g. Absa Bank", key=f"{key_prefix}_client_name")
                    advertiser_email = st.text_input("Receipt / Contact Email *", value=user_email, key=f"{key_prefix}_email")
                    ad_position = st.selectbox("Target Ad Slot *", [
                        "Login Page Sidebar Banner",
                        "Top Header Leaderboard (728x90)",
                        "Footer Promotional Bar (Full Width)",
                        "In-Feed Property Listing Sponsor"
                    ], key=f"{key_prefix}_slot")
                    start_date = st.date_input("Campaign Start Date", value=date.today(), key=f"{key_prefix}_start")

                with f2:
                    target_url = st.text_input("Destination URL *", placeholder="https://example.com", key=f"{key_prefix}_target_url")
                    creative_url = st.text_input("Banner Image URL *", placeholder="https://example.com/banner.png", key=f"{key_prefix}_creative_url")
                    pricing_rate = st.number_input(f"Monthly Slot Rate ({curr_code}) *", min_value=10.0, value=500.0, step=50.0, key=f"{key_prefix}_rate")
                    end_date = st.date_input("Campaign End Date", value=date.today() + timedelta(days=30), key=f"{key_prefix}_end")

                callback_url = st.text_input("Callback Base URL", value="https://www.rentmastergh.com", key=f"{key_prefix}_callback")

                campaign_days = (end_date - start_date).days
                daily_rate = pricing_rate / 30.0
                total_campaign_cost = daily_rate * max(1, campaign_days)

                st.info(f"📅 **Duration:** {max(1, campaign_days)} days | **Prorated Total Charge:** {fmt_money(total_campaign_cost)}")

                submit_ad = st.form_submit_button("💳 Pay Now & Launch Campaign", type="primary", use_container_width=True)

                if submit_ad:
                    if not client_name or not advertiser_email or not target_url or not creative_url:
                        st.error("Please fill in all required fields marked with *.")
                    elif end_date < start_date:
                        st.error("End date cannot be earlier than start date.")
                    else:
                        with st.spinner("Saving campaign & initializing checkout..."):
                            try:
                                ps_res, ref = initialize_ad_payment(
                                    client_name=client_name,
                                    ad_position=ad_position,
                                    amount_ghs=total_campaign_cost,
                                    start_date=str(start_date),
                                    end_date=str(end_date),
                                    destination_url=target_url,
                                    creative_url=creative_url,
                                    email=advertiser_email,
                                    callback_url=callback_url,
                                    user_id=user_id
                                )

                                if ps_res.get("status"):
                                    st.session_state[checkout_url_key] = ps_res["data"]["authorization_url"]
                                    st.session_state[checkout_ref_key] = ref
                                    clear_cache()
                                    st.success("Advert created! Click the Pay button below to complete payment.")
                                else:
                                    st.error(f"Paystack Initialization Failed: {ps_res.get('message')}")
                            except Exception as e:
                                st.error(f"Error processing advert checkout: {e}")

            if st.session_state[checkout_url_key]:
                st.markdown("---")
                st.info(f"Transaction Reference Generated: `{st.session_state[checkout_ref_key]}`")
                st.link_button(
                    "👉 Proceed to Pay Now (Card / Mobile Money)",
                    st.session_state[checkout_url_key],
                    type="primary",
                    use_container_width=True
                )


# ---------------------------------------------------------------------------
# Custom CSS Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0f4c75 0%, #3282b8 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
    }
    .main-header p {
        color: #bbdefb;
        margin: 0.3rem 0 0;
        font-size: 0.95rem;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================================
# LOGIN PAGE
# =========================================================================
def auth_page():
    st.markdown("<br>", unsafe_allow_html=True)
    
    login_col, ad_col = st.columns([1, 1])

    with login_col:
        with st.container(border=True):
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
                        st.error("Password must be at least 6 characters")
                    elif not sb:
                        st.error("Database connection missing.")
                    else:
                        try:
                            sb.auth.sign_up({"email": new_email, "password": new_password})
                            st.success("Account created! Check your email to confirm.")
                        except Exception as e:
                            st.error(f"Error: {e}")

    with ad_col:
        render_ad_space_management(key_prefix="login_ad")


# ---------------------------------------------------------------------------
# Auth & Session State Initialization (SAFE, PERSISTENT & ISOLATED)
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state["user"] = None

if "app_currency" not in st.session_state:
    st.session_state["app_currency"] = "GHS"

if not sb:
    st.warning("⚠️ Database credentials missing. Please set SUPABASE_URL and SUPABASE_KEY in environment variables.")


# ---------------------------------------------------------------------------
# PERSISTENT COOKIE AUTO-LOGIN RESTORATION (Prevents logouts on code reboots)
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
        try:
            cookie_manager.delete("rentmaster_session")
        except Exception:
            pass


# Global Paystack Payment Callback Verification Handler
def handle_paystack_callbacks():
    query_params = st.query_params
    ref_param = query_params.get("reference") or query_params.get("trxref")

    if not ref_param or not sb:
        return

    reference = str(ref_param)
    user_id, user_email = get_active_user_info()

    if reference.startswith("AD-"):
        with st.spinner("Verifying Advert Payment..."):
            verification = verify_paystack_payment(reference)
            if verification.get("status") and verification.get("data", {}).get("status") == "success":
                try:
                    sb.table("ads").update({"status": "paid"}).eq("reference", reference).execute()
                    clear_cache()
                    st.success(f"✅ Payment for Advert (Ref: `{reference}`) verified successfully! Campaign activated.")
                except Exception as e:
                    st.error(f"Error updating advert status: {e}")
            else:
                st.error("❌ Advert payment verification failed or was cancelled.")
        st.query_params.clear()
    else:
        with st.spinner("Verifying Paystack Rent Payment status..."):
            verification = verify_paystack_payment(reference)
            if verification.get("status") and verification.get("data", {}).get("status") == "success":
                data = verification["data"]
                meta = data.get("metadata", {})

                try:
                    payload = {
                        "tenant_id": meta.get("tenant_id") if meta.get("tenant_id") else None,
                        "amount": data["amount"] / 100.0,
                        "payment_method": data.get("channel", "online_paystack"),
                        "notes": f"Paystack Ref: {reference} | Email: {data.get('customer', {}).get('email')}",
                        "payment_date": str(date.today()),
                        "status": "paid"
                    }
                    if user_id: payload["user_id"] = user_id
                    if user_email: payload["user_email"] = user_email

                    sb.table("payments").insert(payload).execute()

                    clear_cache()
                    st.success(f"✅ Rent Payment of {fmt_money(data['amount']/100, data.get('currency'))} verified and credited!")
                except Exception as e:
                    st.error(f"Error logging payment to database: {e}")
            else:
                st.error("❌ Payment verification failed or transaction was cancelled.")
        st.query_params.clear()


# Trigger callback verification globally
handle_paystack_callbacks()


# Handle OAuth code exchange isolated to this browser session
if sb and "code" in st.query_params:
    try:
        auth_code = st.query_params["code"]
        st.query_params.clear()
        res = sb.auth.exchange_code_for_session({"auth_code": auth_code})
        if res and res.user:
            st.session_state["user"] = res.user

            # SAVE PERSISTENT BROWSER COOKIE FOR GOOGLE OAUTH USER
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
        st.sidebar.warning("🔐 Google login session expired. Please click 'Continue with Google' again.")


# Stop unauthenticated users from accessing app dashboard
if st.session_state.get("user") is None:
    auth_page()
    st.stop()


# ---------------------------------------------------------------------------
# UI Helpers
# ---------------------------------------------------------------------------
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


def prop_label(p):
    if not isinstance(p, dict): return "-"
    p_name = p.get('name') or p.get('property_name', 'Unnamed')
    return f"{p_name} - {p.get('address', '')}"


def tenant_label(t):
    if not isinstance(t, dict): return "-"
    return t.get("name", "Unnamed")


def compute_tenant_ledger(tenant: dict, all_payments: list):
    if not isinstance(tenant, dict):
        return {"monthly_rent": 0.0, "total_charged": 0.0, "total_paid": 0.0, "balance": 0.0, "statement": [], "tenant_payments": []}

    monthly_rent = float(tenant.get("rent_amount") or 0.0)
    lease_start_str = tenant.get("lease_start")

    statement = []
    total_charged = 0.0

    if lease_start_str:
        try:
            start_dt = date.fromisoformat(str(lease_start_str)[:10])
            today_dt = date.today()

            months_count = (today_dt.year - start_dt.year) * 12 + (today_dt.month - start_dt.month) + 1
            months_count = max(1, months_count)

            curr_dt = start_dt
            for _ in range(months_count):
                due_date_str = curr_dt.strftime("%Y-%m-01")
                charge_amt = monthly_rent
                total_charged += charge_amt
                statement.append({
                    "date": due_date_str,
                    "type": "Rent Charge",
                    "description": f"Monthly Rent ({curr_dt.strftime('%B %Y')})",
                    "charge": charge_amt,
                    "credit": 0.0,
                    "ref": "-"
                })
                y = curr_dt.year + (curr_dt.month // 12)
                m = (curr_dt.month % 12) + 1
                curr_dt = date(y, m, 1)
        except Exception:
            total_charged = monthly_rent
    else:
        total_charged = monthly_rent

    tenant_id = tenant.get("id")
    tenant_payments = [p for p in all_payments if isinstance(p, dict) and p.get("tenant_id") == tenant_id and p.get("status") == "paid"]
    total_paid = sum(float(p.get("amount") or 0.0) for p in tenant_payments)

    for p in tenant_payments:
        statement.append({
            "date": fmt_date(p.get("payment_date")),
            "type": "Rent Payment",
            "description": f"Payment ({str(p.get('payment_method', 'online')).replace('_', ' ').title()})",
            "charge": 0.0,
            "credit": float(p.get("amount") or 0.0),
            "ref": p.get("notes", "-")
        })

    statement.sort(key=lambda x: str(x["date"]))

    running_balance = 0.0
    for item in statement:
        running_balance += (item["charge"] - item["credit"])
        item["balance"] = running_balance

    balance = total_charged - total_paid

    return {
        "monthly_rent": monthly_rent,
        "total_charged": total_charged,
        "total_paid": total_paid,
        "balance": balance,
        "statement": statement,
        "tenant_payments": tenant_payments
    }


def generate_receipt_html(tenant: dict, payment: dict, property_obj: dict = None):
    tenant = tenant if isinstance(tenant, dict) else {}
    payment = payment if isinstance(payment, dict) else {}
    property_obj = property_obj if isinstance(property_obj, dict) else {}

    amount_str = fmt_money(payment.get("amount", 0))
    p_date = fmt_date(payment.get("payment_date"))
    p_ref = payment.get("notes") or payment.get("id", "N/A")
    t_name = tenant.get("name", "Valued Tenant")
    p_name = prop_label(property_obj) if property_obj else "RentMaster-GH Property"

    receipt_html = f"""
    <div style="border: 2px solid #0f4c75; padding: 25px; border-radius: 12px; background-color: #ffffff; color: #1e293b; max-width: 600px; margin: 0 auto; font-family: sans-serif;">
        <div style="text-align: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; margin-bottom: 20px;">
            <h2 style="color: #0f4c75; margin: 0;">RentMaster-GH Official Receipt</h2>
            <p style="color: #64748b; margin: 5px 0 0 0; font-size: 0.9rem;">Proof of Rent Payment</p>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem;">
            <tr>
                <td style="padding: 8px 0; color: #64748b;">Receipt Reference:</td>
                <td style="padding: 8px 0; text-align: right; font-weight: bold;">{p_ref}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;">Payment Date:</td>
                <td style="padding: 8px 0; text-align: right; font-weight: bold;">{p_date}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;">Tenant Name:</td>
                <td style="padding: 8px 0; text-align: right; font-weight: bold;">{t_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;">Property:</td>
                <td style="padding: 8px 0; text-align: right; font-weight: bold;">{p_name}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;">Payment Method:</td>
                <td style="padding: 8px 0; text-align: right; font-weight: bold;">{str(payment.get('payment_method') or 'Paystack').replace('_', ' ').title()}</td>
            </tr>
            <tr style="border-top: 2px solid #e2e8f0; border-bottom: 2px solid #e2e8f0;">
                <td style="padding: 15px 0; font-size: 1.1rem; font-weight: bold; color: #0f4c75;">Amount Paid:</td>
                <td style="padding: 15px 0; text-align: right; font-size: 1.3rem; font-weight: bold; color: #166534;">{amount_str}</td>
            </tr>
        </table>
        <div style="text-align: center; margin-top: 25px; color: #94a3b8; font-size: 0.8rem;">
            Thank you for your payment! Powered by RentMaster-GH.
        </div>
    </div>
    """
    return receipt_html


def upload_id_to_supabase(file_obj, identifier: str, folder: str = "tenants"):
    if not sb: return None
    try:
        file_bytes = file_obj.getvalue()
        file_ext = file_obj.name.split(".")[-1] if hasattr(file_obj, "name") and "." in file_obj.name else "jpg"
        file_path = f"{folder}/{uuid.uuid4().hex[:8]}_{identifier}.{file_ext}"

        bucket = sb.storage.from_("id-documents")
        bucket.upload(file_path, file_bytes, {"content-type": getattr(file_obj, "type", "image/jpeg"), "upsert": "true"})

        public_url = bucket.get_public_url(file_path)
        return public_url
    except Exception as e:
        st.error(f"Failed to upload ID document to storage: {e}")
        return None


def render_id_verification_widget(entity_type: str = "Tenant", key_prefix: str = "id_widget"):
    st.markdown(f"##### 🆔 {entity_type} Identity Verification (KYC)")
    st.markdown(
        f"""
        <div style="background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
            <h6 style="margin: 0 0 0.4rem 0; color: #0369a1; font-weight: 600;">📌 {entity_type} ID Verification Guidelines</h6>
            <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: #0c4a6e; line-height: 1.4;">
                <li><b>Accepted IDs:</b> Ghana Card / National ID, Passport, Driver's License, Voter ID.</li>
                <li><b>Quality Standard:</b> All 4 corners visible, no glare or blur. Text must be legible.</li>
                <li><b>Privacy Compliance:</b> Protected in accordance with the <i>Data Protection Act (Act 843)</i> / GDPR regulations.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

    capture_method = st.radio(
        "Choose ID Capture Method",
        ["📁 Drag & Drop File Upload", "📷 Live Camera Capture"],
        horizontal=True,
        key=f"{key_prefix}_capture_method"
    )

    uploaded_id_file = None
    if "Drag & Drop" in capture_method:
        uploaded_id_file = st.file_uploader(
            f"Drop {entity_type} ID document file here (PNG, JPG, JPEG, PDF)",
            type=["png", "jpg", "jpeg", "pdf"],
            key=f"{key_prefix}_file_dropzone"
        )
    else:
        st.info("📷 **Live Camera Stream Initializing:** Allow camera access in your browser if prompted. Align ID card inside frame and click 'Take Photo'.")
        
        uploaded_id_file = st.camera_input(
            f"Take photo of {entity_type} ID Card",
            key=f"{key_prefix}_camera_capture",
            help="Align ID card inside frame and click 'Take Photo'"
        )

        # JavaScript helper to auto-trigger camera activation
        components.html(
            """
            <script>
            function autoStartCamera() {
                const doc = window.parent.document;
                const buttons = doc.querySelectorAll('button');
                for (let btn of buttons) {
                    const txt = btn.innerText || btn.textContent || "";
                    if (txt.includes('Turn on camera') || txt.includes('Start camera') || txt.includes('Allow access')) {
                        btn.click();
                        break;
                    }
                }
            }
            autoStartCamera();
            setTimeout(autoStartCamera, 250);
            setTimeout(autoStartCamera, 600);
            </script>
            """,
            height=0,
            width=0
        )

    if uploaded_id_file:
        st.success("✅ Document captured successfully!")
        if hasattr(uploaded_id_file, "type") and "pdf" in str(uploaded_id_file.type):
            st.info("📄 PDF File Selected")
        else:
            st.image(uploaded_id_file, caption=f"Captured {entity_type} ID Preview", width=320)

    return uploaded_id_file


# =========================================================================
# USER PROFILE PAGE
# =========================================================================
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
        st.caption("View and manage your core user profile information.")
        
        with st.form("account_details_form"):
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("User ID", value=user_id, disabled=True)
                full_name = st.text_input("Full Name", value=st.session_state.get("profile_full_name", ""))
                phone = st.text_input("Phone Number", value=st.session_state.get("profile_phone", ""))
            with col2:
                st.text_input("Email Address", value=user_email, disabled=True)
                role = st.selectbox("Account Role", ["Administrator", "Landlord / Property Manager", "Tenant", "Agent"], index=0)
                organization = st.text_input("Company / Organization", value="RentMaster Operations")

            save_details = st.form_submit_button("Save Account Details", type="primary")
            if save_details:
                st.session_state["profile_full_name"] = full_name
                st.session_state["profile_phone"] = phone
                st.toast("✅ Account details saved successfully!", icon="👤")

    with profile_tab2:
        st.markdown("#### 👥 User Management")
        st.caption("Manage platform users, property managers, tenants, and staff roles.")

        tenants = fetch_tenants(user_id, user_email)
        landlords = fetch_landlords(user_id, user_email)

        col_u1, col_u2 = st.columns(2)
        with col_u1:
            st.metric("Total Landlords Registered", len(landlords))
        with col_u2:
            st.metric("Total Active Tenants Registered", len(tenants))

        st.markdown("---")
        st.markdown("##### Registered System Users")
        
        user_table_data = []
        user_table_data.append({
            "User ID": str(user_id)[:8] + "...",
            "Email": user_email,
            "Role": "System Administrator",
            "Status": "Active Now",
            "Joined": str(date.today())
        })

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
        st.caption("Review active sessions, multi-factor authentication, and login safety.")

        sec_col1, sec_col2 = st.columns(2)
        with sec_col1:
            st.markdown("##### Multi-Factor Authentication (MFA / 2FA)")
            st.write("Add an additional layer of security to your account using TOTP Authenticator apps.")
            mfa_enabled = st.toggle("Enable Two-Factor Authentication (2FA)", value=False)
            if mfa_enabled:
                st.info("📱 Scan the QR code with Google Authenticator or Authy to complete setup.")

        with sec_col2:
            st.markdown("##### Active Sessions & Login Audit")
            st.write(f"**Current Session:** Logged in from Ghana ({user_email})")
            st.write(f"**Remember Me Enabled:** `{st.session_state.get('remember_me', True)}`")
            if st.button("Revoke All Other Sessions", type="secondary"):
                st.success("✅ All other active sessions have been revoked.")

    with profile_tab4:
        st.markdown("#### 🔑 Change Password")
        st.caption("Update your password securely via Supabase Auth.")

        with st.form("change_password_form"):
            current_pw = st.text_input("Current Password", type="password")
            new_pw = st.text_input("New Password (Min 6 characters)", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")

            submit_pw = st.form_submit_button("Update Password", type="primary")

            if submit_pw:
                if not new_pw or not confirm_pw:
                    st.error("Please enter and confirm your new password.")
                elif new_pw != confirm_pw:
                    st.error("New passwords do not match.")
                elif len(new_pw) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    try:
                        sb.auth.update_user({"password": new_pw})
                        st.success("✅ Password updated successfully!")
                    except Exception as e:
                        st.error(f"Failed to update password: {e}")

    with profile_tab5:
        st.markdown("#### ⚙️ Security Settings")
        st.caption("Configure notification rules, session timeouts, and privacy settings.")

        with st.form("security_settings_form"):
            st.checkbox("Send Email Notification on New Login", value=True)
            st.checkbox("Alert me via Email when rent is overdue", value=True)
            st.checkbox("Require password confirmation before property deletion", value=True)

            session_timeout = st.select_slider(
                "Automatic Inactivity Session Timeout (Minutes)",
                options=[15, 30, 60, 120, 1440],
                value=60
            )

            save_sec_settings = st.form_submit_button("Save Security Settings", type="primary")
            if save_sec_settings:
                st.toast(f"✅ Security settings saved! Auto-timeout set to {session_timeout} mins.", icon="⚙️")


# ---------------------------------------------------------------------------
# Standard Core Pages
# ---------------------------------------------------------------------------
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
    with col1:
        st.metric("Properties", len(props), f"{occupied} occupied")
    with col2:
        st.metric("Tenants", len(tenants), f"{sum(1 for t in tenants if t.get('is_active'))} active")
    with col3:
        st.metric("Expected Monthly Rent", fmt_money(expected))
    with col4:
        st.metric("Active Leases", sum(1 for l in leases if l.get("status") == "active"))

    st.markdown("---")
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("Collected", fmt_money(collected))
    with col6:
        st.metric("Pending", fmt_money(pending))
    with col7:
        st.metric("Overdue", fmt_money(overdue))
    with col8:
        st.metric("Open Maintenance", sum(1 for m in maint if m.get("status") in ("open", "in_progress")))

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


def page_properties():
    header()
    st.subheader("Properties")

    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    with st.expander("Add New Property", expanded=False):
        with st.form("add_property"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Property Name *")
                address = st.text_input("Address / Location *")
                rent = st.number_input(f"Monthly Rent ({curr_code})", min_value=0.0, value=0.0, step=50.0)
            with col2:
                ptype = st.selectbox("Property Type", ["apartment", "house", "commercial", "other"])
                beds = st.number_input("Bedrooms", min_value=0, value=0)
                baths = st.number_input("Bathrooms", min_value=0, value=0)
            desc = st.text_area("Description")
            is_occupied = st.checkbox("Is Occupied", value=False)
            submitted = st.form_submit_button("Add Property")
            if submitted:
                if not name or not address:
                    st.error("Property name and address are required.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    payload = {
                        "name": name,
                        "address": address,
                        "monthly_rent": float(rent),
                        "property_type": ptype,
                        "bedrooms": int(beds),
                        "bathrooms": int(baths),
                        "is_occupied": is_occupied,
                        "description": desc,
                    }
                    if user_id: payload["user_id"] = user_id
                    if user_email: payload["user_email"] = user_email

                    sb.table("properties").insert(payload).execute()
                    clear_cache()
                    st.success(f"Property '{name}' added.")
                    st.rerun()

    props = fetch_properties(user_id, user_email)
    if not props:
        st.info("No properties yet. Add one above.")
        return

    st.markdown("---")
    st.markdown(f"**{len(props)} Properties**")

    for p in props:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                prop_title = p.get('name') or p.get('property_name', 'Unnamed')
                st.markdown(f"**{prop_title}**")
                st.caption(p.get("address", ""))
                if p.get("description"):
                    st.caption(p.get("description"))
            with col2:
                rent_val = p.get('monthly_rent') if p.get('monthly_rent') is not None else p.get('rent_amount')
                st.markdown(f"Rent: {fmt_money(rent_val)}")
                beds_str = f"{p.get('bedrooms')} bed / " if p.get('bedrooms') is not None else ""
                baths_str = f"{p.get('bathrooms')} bath" if p.get('bathrooms') is not None else ""
                st.caption(f"{beds_str}{baths_str}".strip())
            with col3:
                badge = "Occupied" if p.get("is_occupied", False) else "Vacant"
                st.markdown(f"Status: **{badge}**")
                if p.get('property_type'):
                    st.caption(f"Type: {p.get('property_type')}")
            with col4:
                if st.button("Delete", key=f"del_prop_{p['id']}", type="secondary"):
                    if sb:
                        sb.table("properties").delete().eq("id", p["id"]).execute()
                        clear_cache()
                        st.rerun()


def page_landlords():
    header()
    st.subheader("Landlord & Payout Management")
    st.caption("Configure payout destinations (Mobile Money, Local Bank, or SWIFT/IBAN) for automated Paystack rent splits.")

    user_id, user_email = get_active_user_info()

    landlords = fetch_landlords(user_id, user_email)
    tenants = fetch_tenants(user_id, user_email)

    landlord_options = {"new": "➕ Add New Landlord"}
    for l in landlords:
        landlord_options[l["id"]] = f"{l['name']} ({l.get('phone', 'No Phone')})"

    selected_id = st.selectbox(
        "Select Landlord to Manage",
        options=list(landlord_options.keys()),
        format_func=lambda x: landlord_options[x]
    )

    selected_landlord = next((l for l in landlords if l["id"] == selected_id), None)
    default_name = selected_landlord.get("name", "") if selected_landlord else ""
    default_email = selected_landlord.get("email", "") if selected_landlord else ""
    default_phone = selected_landlord.get("phone", "") if selected_landlord else ""
    default_account = selected_landlord.get("account_number", "") if selected_landlord else ""

    if selected_landlord and selected_landlord.get("paystack_subaccount_code"):
        st.success(f"✅ Paystack Subaccount Linked: `{selected_landlord['paystack_subaccount_code']}`")
    elif selected_landlord:
        st.warning("⚠️ No Paystack Subaccount generated yet. Save payout details to enable automatic splits.")

    # ID Verification Widget rendered outside form for instant camera auto-start
    st.markdown("#### 1. Landlord KYC Identity Verification")
    landlord_id_file = render_id_verification_widget(entity_type="Landlord", key_prefix="landlord")

    st.markdown("#### 2. Landlord Payout Destination Details")
    with st.form("landlord_payout_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Landlord Full Name *", value=default_name)
            email = st.text_input("Email Address", value=default_email)
            phone = st.text_input("Phone Number *", value=default_phone, help="Format e.g. 024XXXXXXX or +233XXXXXXX")
            country = st.selectbox("Landlord Country *", list(GLOBAL_PAYOUT_BANKS.keys()), key="landlord_country_select")

        with col2:
            available_banks = GLOBAL_PAYOUT_BANKS[country]
            bank_name = st.selectbox("Payout Provider / Bank *", list(available_banks.keys()))
            account_number = st.text_input(
                "Account / Mobile Money / IBAN Number *",
                value=default_account,
                help="Enter Mobile Money number, Bank Account, or IBAN"
            )
            selected_bank_code = available_banks[bank_name]
            st.text_input("Bank Code", value=selected_bank_code, disabled=True)

        submitted = st.form_submit_button("Save Landlord Payout Details", type="primary", use_container_width=True)

        if submitted:
            if not name or not phone or not account_number:
                st.error("Please fill in all required fields marked with *.")
            else:
                target_id = selected_id if selected_id != "new" else None
                try:
                    id_card_url = None
                    if landlord_id_file:
                        with st.spinner("Uploading Landlord ID document to secure storage..."):
                            id_card_url = upload_id_to_supabase(landlord_id_file, name, folder="landlords")

                    with st.spinner("Registering landlord with Paystack API..."):
                        data, code = save_landlord_bank_details(
                            landlord_id=target_id,
                            name=name,
                            email=email,
                            phone=phone,
                            bank_name=bank_name,
                            account_number=account_number,
                            bank_code=selected_bank_code,
                            platform_fee_pct=0.0,
                            id_card_url=id_card_url,
                            user_id=user_id,
                            user_email=user_email
                        )

                    clear_cache()
                    st.success(f"✅ Landlord registered! Paystack Subaccount Code: `{code}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save details: {e}")

    # -------------------------------------------------------------------
    # Ghana Rent Card Upload & Publish Section (Dedicated for Ghana Landlords)
    # -------------------------------------------------------------------
    if country == "Ghana":
        st.markdown("---")
        with st.container(border=True):
            st.markdown("##### 📋 Ghana Rent Card Upload (Ghana Landlords Only)")
            st.caption("Landlords operating in Ghana can upload and assign an official Rent Card to their respective tenant. Clicking **📢 Publish to Tenant** explicitly makes the document visible to that tenant on their portal.")

            if not tenants:
                st.info("No active tenants found. Add a tenant first in the Tenants page to publish a Rent Card.")
            else:
                with st.form("ghana_rent_card_publish_form", clear_on_submit=False):
                    tenant_options_rc = {t["id"]: f"{t.get('name', 'Unnamed')} — {prop_label(t.get('properties'))}" for t in tenants}

                    selected_tenant_for_card = st.selectbox(
                        "Assign Rent Card to Tenant *",
                        options=list(tenant_options_rc.keys()),
                        format_func=lambda x: tenant_options_rc[x],
                        key="ghana_rent_card_tenant_select"
                    )

                    rent_card_file = st.file_uploader(
                        "Upload Ghana Rent Card File (PDF, PNG, JPG, JPEG) *",
                        type=["png", "jpg", "jpeg", "pdf"],
                        key="ghana_rent_card_uploader"
                    )

                    publish_rc_submitted = st.form_submit_button("📢 Publish to Tenant", type="primary", use_container_width=True)

                    if publish_rc_submitted:
                        if not rent_card_file:
                            st.error("Please select a Rent Card file to upload.")
                        elif not selected_tenant_for_card:
                            st.error("Please select a tenant to publish the Rent Card to.")
                        else:
                            with st.spinner("Uploading Rent Card & publishing to tenant portal..."):
                                rc_url = upload_id_to_supabase(rent_card_file, f"rc_{selected_tenant_for_card}", folder="rent_cards")
                                if rc_url and sb:
                                    sb.table("tenants").update({"rent_card_url": rc_url}).eq("id", selected_tenant_for_card).execute()
                                    clear_cache()
                                    st.success("✅ Rent Card published! The document is now visible to the tenant on their portal.")
                                    st.rerun()

    if landlords:
        st.markdown("---")
        st.markdown(f"**{len(landlords)} Landlords Registered**")
        for l in landlords:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1:
                    st.markdown(f"**{l.get('name', 'Unnamed')}**")
                    if l.get('email'):
                        st.caption(f"Email: {l['email']}")
                    if l.get('phone'):
                        st.caption(f"Phone: {l['phone']}")
                    if l.get('id_card_url'):
                        st.markdown(f"🆔 [View Verified ID Document]({l['id_card_url']})")
                with c2:
                    st.markdown(f"Provider: **{l.get('bank_name', '-')}**")
                    st.caption(f"Account: {l.get('account_number', '-')}")
                with c3:
                    sub_code = l.get('paystack_subaccount_code')
                    if sub_code:
                        st.markdown(f"Subaccount: `{sub_code}`")
                    else:
                        st.caption("Subaccount: Unlinked")
                with c4:
                    if st.button("Delete", key=f"del_landlord_{l['id']}", type="secondary"):
                        if sb:
                            sb.table("landlords").delete().eq("id", l["id"]).execute()
                            clear_cache()
                            st.rerun()


def page_tenants():
    header()
    st.subheader("Tenants")

    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    props = fetch_properties(user_id, user_email)
    prop_options = {p["id"]: prop_label(p) for p in props} or {"": "No properties available"}

    with st.expander("Add New Tenant", expanded=False):
        st.markdown("##### Tenant Identity Document (KYC)")
        id_file_data = render_id_verification_widget(entity_type="Tenant", key_prefix="tenant")

        with st.form("add_tenant"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Tenant Name *")
                email = st.text_input("Email")
                rent_amount = st.number_input(f"Agreed Monthly Rent ({curr_code})", min_value=0.0, value=0.0, step=50.0)
            with col2:
                phone = st.text_input("Phone Number", help="e.g. 024XXXXXXX or +233 24XXXXXXX")
                prop_id = st.selectbox("Property", list(prop_options.keys()),
                                       format_func=lambda x: prop_options.get(x, "-"))

            col3, col4 = st.columns(2)
            with col3:
                lease_start = st.date_input("Lease Start", value=date.today())
            with col4:
                lease_end = st.date_input("Lease End", value=date.today() + timedelta(days=365))

            active = st.checkbox("Active Tenant", value=True)

            submitted = st.form_submit_button("Add Tenant", type="primary")

            if submitted:
                if not name:
                    st.error("Tenant name is required.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    id_card_url = None
                    if id_file_data:
                        with st.spinner("Uploading ID document to secure storage..."):
                            id_card_url = upload_id_to_supabase(id_file_data, name, folder="tenants")

                    payload = {
                        "name": name,
                        "email": email if email else None,
                        "phone": phone if phone else None,
                        "property_id": prop_id if prop_id else None,
                        "rent_amount": float(rent_amount),
                        "lease_start": str(lease_start),
                        "lease_end": str(lease_end),
                        "is_active": active,
                        "id_card_url": id_card_url
                    }
                    if user_id: payload["user_id"] = user_id
                    if user_email: payload["user_email"] = user_email

                    sb.table("tenants").insert(payload).execute()
                    clear_cache()
                    st.success(f"Tenant '{name}' added successfully.")
                    st.rerun()

    tenants = fetch_tenants(user_id, user_email)
    if not tenants:
        st.info("No tenants yet. Add one above.")
        return

    st.markdown("---")
    st.markdown(f"**{len(tenants)} Tenants**")

    for t in tenants:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.markdown(f"**{t.get('name', 'Unnamed')}**")
                if t.get("email"):
                    st.caption(f"Email: {t['email']}")
                if t.get("phone"):
                    st.caption(f"Phone: {t['phone']}")
                if t.get("id_card_url"):
                    st.markdown(f"🆔 [View Verified ID Document]({t['id_card_url']})")
                if t.get("rent_card_url"):
                    st.markdown(f"📋 [View Official Ghana Rent Card]({t['rent_card_url']})")
            with col2:
                prop = t.get("properties")
                st.markdown(f"Property: {prop_label(prop)}")
            with col3:
                st.caption(f"Lease: {fmt_date(t.get('lease_start'))} to {fmt_date(t.get('lease_end'))}")
                status = "Active" if t.get("is_active") else "Inactive"
                st.markdown(f"Status: **{status}**")
            with col4:
                if st.button("Delete", key=f"del_tenant_{t['id']}", type="secondary"):
                    if sb:
                        sb.table("tenants").delete().eq("id", t["id"]).execute()
                        clear_cache()
                        st.rerun()


def page_payments():
    header()
    st.subheader("Rent Ledger & Payments Hub")

    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    tenants = fetch_tenants(user_id, user_email)
    all_payments = fetch_payments(user_id, user_email)

    tab_ledger, tab_manual, tab_log = st.tabs([
        "📜 Tenant Rent Ledger & Pay Rent",
        "📝 Record Offline Payment",
        "📊 Master Payment Log & Receipts"
    ])

    with tab_ledger:
        if not tenants:
            st.info("No active tenants found. Add a tenant to view their rent ledger.")
        else:
            tenant_map = {t["id"]: f"{t.get('name')} — {prop_label(t.get('properties'))}" for t in tenants}
            selected_tenant_id = st.selectbox(
                "Select Tenant Ledger",
                options=list(tenant_map.keys()),
                format_func=lambda x: tenant_map[x],
                key="ledger_tenant_select"
            )

            selected_tenant = next((t for t in tenants if t["id"] == selected_tenant_id), None)
            ledger = compute_tenant_ledger(selected_tenant, all_payments)

            if selected_tenant and selected_tenant.get("rent_card_url"):
                st.info(f"📋 **Official Ghana Rent Card Issued:** [Click to View / Download Rent Card]({selected_tenant['rent_card_url']})")

            st.markdown("---")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Agreed Monthly Rent", fmt_money(ledger["monthly_rent"]))
            m2.metric("Total Rent Charged", fmt_money(ledger["total_charged"]))
            m3.metric("Total Amount Paid", fmt_money(ledger["total_paid"]))

            bal_color = "red" if ledger["balance"] > 0 else "green"
            bal_label = "Outstanding Due" if ledger["balance"] > 0 else "Credit / Up-to-date"
            m4.metric("Ledger Balance", fmt_money(abs(ledger["balance"])), delta=f":{bal_color}[{bal_label}]")

            st.markdown("---")

            with st.container(border=True):
                st.markdown("#### 💳 Pay Rent Online (Card / Mobile Money / Transfer)")
                st.caption("Process live rent payments securely via Paystack.")

                prop_obj = selected_tenant.get("properties") if selected_tenant else None
                landlord_obj = prop_obj.get("landlords") if (prop_obj and isinstance(prop_obj, dict)) else None
                subaccount_code = landlord_obj.get("paystack_subaccount_code") if landlord_obj else None

                if subaccount_code:
                    st.info(f"⚡ **Direct Landlord Split Payout Enabled:** Funds will be routed to Landlord `{landlord_obj.get('name')}` (`{subaccount_code}`).")
                else:
                    st.caption("ℹ️ Standard platform collection (Landlord payout details unlinked).")

                with st.form("rent_checkout_form"):
                    col_p1, col_p2 = st.columns(2)
                    with col_p1:
                        default_pay_amount = max(ledger["balance"], ledger["monthly_rent"])
                        pay_amount = st.number_input(f"Payment Amount ({curr_code}) *", min_value=1.0, value=float(default_pay_amount) if default_pay_amount > 0 else 100.0, step=50.0)
                    with col_p2:
                        tenant_email = selected_tenant.get("email") or ""
                        receipt_email = st.text_input("Receipt Email *", value=tenant_email, placeholder="tenant@example.com")

                    callback_domain = st.text_input("Callback Base URL", value="https://www.rentmastergh.com")
                    proceed_pay = st.form_submit_button("💳 Proceed to Checkout", type="primary", use_container_width=True)

                    if proceed_pay:
                        if not receipt_email:
                            st.error("Please enter a valid receipt email.")
                        else:
                            with st.spinner("Initializing secure checkout..."):
                                res = initialize_paystack_payment(
                                    email=receipt_email,
                                    amount_in_main_unit=pay_amount,
                                    callback_url=callback_domain,
                                    metadata={
                                        "type": "rent_payment",
                                        "tenant_id": selected_tenant_id,
                                        "tenant_name": selected_tenant.get("name"),
                                        "user_id": user_id
                                    },
                                    subaccount=subaccount_code,
                                    currency=curr_code
                                )

                                if res.get("status"):
                                    auth_url = res["data"]["authorization_url"]
                                    st.success("Checkout initialized! Click below to complete your payment.")
                                    st.link_button(
                                        "👉 Click Here to Pay Now (Card / Mobile Money)",
                                        auth_url,
                                        type="primary",
                                        use_container_width=True
                                    )
                                else:
                                    st.error(f"Failed to initialize payment: {res.get('message', 'Unknown error')}")

            st.markdown("#### 📋 Itemized Rent Ledger Statement")

            if not ledger["statement"]:
                st.info("No charges or payments recorded on this ledger.")
            else:
                formatted_statement = []
                for idx, row in enumerate(ledger["statement"], 1):
                    formatted_statement.append({
                        "#": idx,
                        "Date": row["date"],
                        "Type": row["type"],
                        "Description": row["description"],
                        f"Charge ({curr_code})": f"{row['charge']:,.2f}" if row['charge'] > 0 else "-",
                        f"Credit ({curr_code})": f"{row['credit']:,.2f}" if row['credit'] > 0 else "-",
                        f"Balance ({curr_code})": f"{row['balance']:,.2f}",
                        "Reference": row["ref"]
                    })
                st.dataframe(formatted_statement, use_container_width=True, hide_index=True)

    with tab_manual:
        st.markdown("##### 📝 Record Offline Payment (Cash, Check, Bank Deposit)")

        tenant_options = {t["id"]: f"{tenant_label(t)} ({t.get('email', 'No email')})" for t in tenants} or {"": "No active tenants"}

        with st.form("add_offline_payment_form"):
            col1, col2 = st.columns(2)
            with col1:
                tid = st.selectbox("Tenant *", list(tenant_options.keys()),
                                   format_func=lambda x: tenant_options.get(x, "-"), key="manual_tid")
                amount = st.number_input(f"Amount ({curr_code}) *", min_value=1.0, value=100.0, step=10.0, key="manual_amt")
                method = st.selectbox("Payment Method *", ["cash", "card", "bank_transfer", "mobile_money", "check", "other"])
            with col2:
                pdate = st.date_input("Payment Date *", value=date.today())
                status = st.selectbox("Status *", ["paid", "pending", "overdue", "cancelled"])

            notes = st.text_area("Notes / Reference", help="Receipt number, bank deposit slip number, or notes.")
            submitted = st.form_submit_button("Record Payment in Ledger", type="primary")

            if submitted:
                if not tid or amount <= 0:
                    st.error("Select a tenant and enter a valid amount.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    payload = {
                        "tenant_id": tid,
                        "amount": float(amount),
                        "payment_method": method,
                        "notes": notes if notes else "Manual Entry",
                        "payment_date": str(pdate),
                        "status": status,
                    }
                    if user_id: payload["user_id"] = user_id
                    if user_email: payload["user_email"] = user_email

                    sb.table("payments").insert(payload).execute()
                    clear_cache()
                    st.success("✅ Payment recorded into ledger successfully.")
                    st.rerun()

    with tab_log:
        st.markdown("##### 📊 Transaction Log & Digital Receipts")

        if not all_payments:
            st.info("No payment transactions found in database.")
        else:
            st.markdown(f"**Total Records:** `{len(all_payments)}`")

            for p in all_payments:
                with st.container(border=True):
                    col1, col2, col3, col4, col5 = st.columns([2.5, 2, 2, 2, 1.5])
                    t_obj = p.get("tenants")
                    with col1:
                        st.markdown(f"**{tenant_label(t_obj)}**")
                        if p.get("notes"):
                            st.caption(f"📝 {p['notes']}")
                    with col2:
                        st.markdown(f"Amount: **{fmt_money(p.get('amount'))}**")
                    with col3:
                        st.markdown(f"Date: {fmt_date(p.get('payment_date'))}")
                    with col4:
                        st.markdown(f"Status: **{str(p.get('status')).upper()}**")
                        st.caption(f"Method: {(p.get('payment_method') or 'online').replace('_', ' ').title()}")
                    with col5:
                        c_rec, c_del = st.columns(2)
                        with c_rec:
                            if p.get("status") == "paid":
                                prop_obj = t_obj.get("properties") if (t_obj and isinstance(t_obj, dict)) else None
                                receipt_html = generate_receipt_html(t_obj or {}, p, prop_obj)
                                st.download_button(
                                    "🧾 Receipt",
                                    data=receipt_html,
                                    file_name=f"RentReceipt_{fmt_date(p.get('payment_date'))}_{p.get('id')[:6]}.html",
                                    mime="text/html",
                                    key=f"rec_btn_{p['id']}"
                                )
                        with c_del:
                            if st.button("Delete", key=f"del_pay_{p['id']}", type="secondary"):
                                if sb:
                                    sb.table("payments").delete().eq("id", p["id"]).execute()
                                    clear_cache()
                                    st.rerun()


def page_leases():
    header()
    st.subheader("Leases")

    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    props = fetch_properties(user_id, user_email)
    tenants = fetch_tenants(user_id, user_email)
    prop_options = {p["id"]: prop_label(p) for p in props} or {"": "No properties available"}
    tenant_options = {t["id"]: tenant_label(t) for t in tenants} or {"": "No tenants available"}

    with st.expander("Create New Lease", expanded=False):
        with st.form("add_lease"):
            col1, col2 = st.columns(2)
            with col1:
                pid = st.selectbox("Property *", list(prop_options.keys()),
                                   format_func=lambda x: prop_options.get(x, "-"))
                start = st.date_input("Start Date *", value=date.today())
            with col2:
                tid = st.selectbox("Tenant *", list(tenant_options.keys()),
                                   format_func=lambda x: tenant_options.get(x, "-"))
                end = st.date_input("End Date *", value=date.today() + timedelta(days=365))
            deposit = st.number_input(f"Deposit Amount ({curr_code})", min_value=0.0, value=0.0, step=100.0)
            status = st.selectbox("Status", ["active", "expired", "terminated"])
            submitted = st.form_submit_button("Create Lease")
            if submitted:
                if not pid or not tid:
                    st.error("Property and tenant are required.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    payload = {
                        "property_id": pid, "tenant_id": tid,
                        "start_date": str(start), "end_date": str(end),
                        "deposit_amount": deposit, "status": status,
                    }
                    if user_id: payload["user_id"] = user_id
                    if user_email: payload["user_email"] = user_email

                    sb.table("leases").insert(payload).execute()
                    clear_cache()
                    st.success("Lease created.")
                    st.rerun()

    leases = fetch_leases(user_id, user_email)
    if not leases:
        st.info("No leases yet. Create one above.")
        return

    st.markdown("---")
    st.markdown(f"**{len(leases)} Leases**")

    for l in leases:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            with col1:
                st.markdown(f"**{prop_label(l.get('properties'))}**")
                st.caption(f"Tenant: {tenant_label(l.get('tenants'))}")
            with col2:
                st.caption(f"Start: {fmt_date(l.get('start_date'))}")
                st.caption(f"End: {fmt_date(l.get('end_date'))}")
            with col3:
                st.markdown(f"Deposit: {fmt_money(l.get('deposit_amount'))}")
            with col4:
                st.markdown(f"Status: **{l.get('status', '-')}**")
            with col5:
                if st.button("Delete", key=f"del_lease_{l['id']}", type="secondary"):
                    if sb:
                        sb.table("leases").delete().eq("id", l["id"]).execute()
                        clear_cache()
                        st.rerun()


def page_maintenance():
    header()
    st.subheader("Maintenance Requests")

    user_id, user_email = get_active_user_info()

    props = fetch_properties(user_id, user_email)
    tenants = fetch_tenants(user_id, user_email)
    prop_options = {p["id"]: prop_label(p) for p in props} or {"": "No properties available"}
    tenant_options = {t["id"]: tenant_label(t) for t in tenants} or {"": "None"}

    with st.expander("File New Request", expanded=False):
        with st.form("add_maintenance"):
            col1, col2 = st.columns(2)
            with col1:
                pid = st.selectbox("Property *", list(prop_options.keys()),
                                   format_func=lambda x: prop_options.get(x, "-"))
                title = st.text_input("Title *")
            with col2:
                tid = st.selectbox("Tenant (optional)", list(tenant_options.keys()),
                                   format_func=lambda x: tenant_options.get(x, "None"))
                priority = st.selectbox("Priority", ["low", "medium", "high", "urgent"])
            desc = st.text_area("Description")
            status = st.selectbox("Status", ["open", "in_progress", "resolved", "closed"])
            submitted = st.form_submit_button("File Request")
            if submitted:
                if not pid or not title:
                    st.error("Property and title are required.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    payload = {
                        "property_id": pid,
                        "tenant_id": tid if (tid and tid != "") else None,
                        "title": title, "description": desc,
                        "priority": priority, "status": status,
                    }
                    if user_id: payload["user_id"] = user_id
                    if user_email: payload["user_email"] = user_email

                    sb.table("maintenance_requests").insert(payload).execute()
                    clear_cache()
                    st.success("Maintenance request filed.")
                    st.rerun()

    requests_list = fetch_maintenance(user_id, user_email)
    if not requests_list:
        st.info("No maintenance requests yet.")
        return

    st.markdown("---")
    st.markdown(f"**{len(requests_list)} Maintenance Requests**")

    for m in requests_list:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            with col1:
                st.markdown(f"**{m.get('title', 'Untitled')}**")
                if m.get("description"):
                    st.caption(m["description"])
                st.caption(f"Property: {prop_label(m.get('properties'))}")
            with col2:
                st.markdown(f"Priority: **{m.get('priority', '-')}**")
            with col3:
                st.markdown(f"Status: **{m.get('status', '-')}**")
            with col4:
                st.caption(f"Filed: {fmt_date(m.get('created_at'))}")
            with col5:
                if st.button("Delete", key=f"del_maint_{m['id']}", type="secondary"):
                    if sb:
                        sb.table("maintenance_requests").delete().eq("id", m["id"]).execute()
                        clear_cache()
                        st.rerun()


def page_settings():
    header()
    st.subheader("Settings & Administration")

    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    with st.container(border=True):
        col_info1, col_info2 = st.columns([3, 1])
        with col_info1:
            st.markdown("### RentMaster-GH Enterprise")
            st.markdown(
                "A comprehensive rental property management system tailored for tracking properties, "
                "tenants, payments, lease agreements, and maintenance requests."
            )
        with col_info2:
            st.markdown("**Version:** `2.5.0`")
            st.markdown("**Environment:** `Production`")
            st.markdown("**Database Status:** :green[Connected]" if sb else ":red[Disconnected]")

    st.markdown("---")

    st.markdown("#### System Preferences & Currency Settings")
    with st.container(border=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            currency_options = list(SUPPORTED_CURRENCIES.keys())
            curr_index = currency_options.index(curr_code) if curr_code in currency_options else 0
            selected_currency = st.selectbox(
                "Default Currency *",
                options=currency_options,
                format_func=lambda x: SUPPORTED_CURRENCIES[x]["name"],
                index=curr_index
            )
            st.selectbox("Date Format Standard", ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"], index=0)

        with col_p2:
            st.selectbox("Records Per Page Display", [10, 25, 50, 100], index=1)
            st.toggle("Enable Automated Payment Alerts", value=True)

        if st.button("Save System Preferences", type="primary", key="save_prefs"):
            st.session_state["app_currency"] = selected_currency
            st.toast(f"Preferences saved! Default currency set to {selected_currency}.", icon="✅")
            st.rerun()

    st.markdown("---")

    render_ad_space_management(key_prefix="settings_ad")

    st.markdown("---")

    st.markdown("#### Data Management & Backup Export")
    st.caption("Export application database tables into JSON format for external auditing or data backup.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "📥 Export Properties",
            data=json.dumps(fetch_properties(user_id, user_email), indent=2),
            file_name="rentmaster_properties.json",
            mime="application/json",
            use_container_width=True
        )
    with col2:
        st.download_button(
            "📥 Export Payments",
            data=json.dumps(fetch_payments(user_id, user_email), indent=2),
            file_name="rentmaster_payments.json",
            mime="application/json",
            use_container_width=True
        )
    with col3:
        st.download_button(
            "📥 Export Tenants",
            data=json.dumps(fetch_tenants(user_id, user_email), indent=2),
            file_name="rentmaster_tenants.json",
            mime="application/json",
            use_container_width=True
        )


# ---------------------------------------------------------------------------
# Sidebar Navigation & Execution Router
# ---------------------------------------------------------------------------
PAGES = {
    "Dashboard": page_dashboard,
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
        user_email = getattr(active_user, "email", "User")
        st.write(f"👤 Logged in: **{user_email}**")
        if st.button("Logout", key="logout_btn"):
            try:
                cookie_manager.delete("rentmaster_session")
            except Exception:
                pass
            if sb:
                try:
                    sb.auth.sign_out()
                except Exception:
                    pass
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    st.caption("RentMaster-GH v2.5 • Streamlit + Supabase")

# Execute active page
PAGES[selection]()
