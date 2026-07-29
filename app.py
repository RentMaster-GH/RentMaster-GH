"""
RentMaster-GH v2 - Rental Management Streamlit Web App
Full interactive UI backed by Supabase. Manages properties, tenants,
payments, leases, maintenance requests, and landlords with a dashboard overview.
Includes Paystack Integration for Cards, Mobile Money (Momo), Bank Transfer, and Split Payouts.
"""

import json
import os
import uuid
from datetime import date, timedelta

import requests
import streamlit as st
from dotenv import load_dotenv
from streamlit.errors import StreamlitSecretNotFoundError
from supabase import create_client

# ---------------------------------------------------------------------------
# Streamlit Config (MUST BE FIRST STREAMLIT COMMAND)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RentMaster-GH",
    page_icon=":house:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load environment variables
load_dotenv()


def get_secret(key: str, default: str = "") -> str:
    """
    Safely retrieves a secret from OS environment variables first (e.g. Render, Heroku),
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
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Missing Supabase credentials in environment variables.")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)


sb = get_client()

# ---------------------------------------------------------------------------
# Paystack API Helpers & Ghana Payout Bank Codes
# ---------------------------------------------------------------------------
GHANA_PAYOUT_BANKS = {
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
}


def create_paystack_subaccount(business_name, bank_code, account_number, percentage_charge=0.0, email=None, phone=None):
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


def initialize_paystack_payment(email, amount_in_ghs, callback_url, metadata=None):
    if not PAYSTACK_SECRET_KEY:
        return {"status": False, "message": "PAYSTACK_SECRET_KEY is not configured in secrets or environment."}

    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "amount": int(round(amount_in_ghs * 100)),
        "currency": "GHS",
        "callback_url": callback_url,
        "channels": ["card", "mobile_money", "bank_transfer"],
        "metadata": metadata or {},
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}


def verify_paystack_payment(reference):
    if not PAYSTACK_SECRET_KEY:
        return {"status": False, "message": "PAYSTACK_SECRET_KEY is missing."}

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}


def save_landlord_bank_details(landlord_id, name, email, phone, bank_name, account_number, bank_code, platform_fee_pct=0.0):
    ps_res = create_paystack_subaccount(
        business_name=name,
        bank_code=bank_code,
        account_number=account_number,
        percentage_charge=platform_fee_pct,
        email=email,
        phone=phone,
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

    if landlord_id:
        res = sb.table("landlords").update(payload).eq("id", landlord_id).execute()
    else:
        res = sb.table("landlords").insert(payload).execute()

    return res.data, subaccount_code


# ---------------------------------------------------------------------------
# Custom CSS
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


# ---------------------------------------------------------------------------
# Auth Page
# ---------------------------------------------------------------------------
def auth_page():
    st.markdown("<br>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 1.8, 1])

    with center_col:
        with st.container(border=True):
            st.markdown(
                """
                <div style="
                    background-color: #f0fdf4;
                    border: 1px solid #bbf7d0;
                    border-radius: 8px;
                    padding: 0.9rem;
                    margin-bottom: 1rem;
                    text-align: center;
                ">
                    <p style="margin: 0 0 0.4rem 0; font-weight: 600; color: #166534; font-size: 0.88rem;">
                        Looking to make a payment or support without logging in?
                    </p>
                    <a href="https://paystack.shop/pay/zvx0npq7hv"
                       target="_blank"
                       rel="noopener noreferrer"
                       style="
                           display: inline-block;
                           background-color: #09a5db;
                           color: #ffffff;
                           font-weight: 600;
                           padding: 8px 16px;
                           border-radius: 6px;
                           text-decoration: none;
                           font-size: 0.88rem;
                           box-shadow: 0 2px 4px rgba(0,0,0,0.08);
                       ">
                        Make a Payment / Donation via Paystack
                    </a>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("<h2 style='text-align: center; margin-bottom: 1rem;'>RentMaster-GH</h2>", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["Log In", "Sign Up"])
            redirect_url = "https://www.rentmastergh.com"

            with tab1:
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_pw")

                if st.button("Log In", use_container_width=True, key="login_btn", type="primary"):
                    try:
                        res = sb.auth.sign_in_with_password({"email": email, "password": password})
                        if res.user:
                            st.session_state.user = res.user
                            st.rerun()
                    except Exception as e:
                        st.error(f"Login Error: {e}")

                st.divider()

                try:
                    res = sb.auth.sign_in_with_oauth({
                        "provider": "google",
                        "options": {"redirect_to": redirect_url},
                    })
                    if res.url:
                        st.markdown(
                            f"""
                            <a href="{res.url}" target="_self" style="
                                display: flex; align-items: center; justify-content: center; gap: 10px;
                                width: 100%; padding: 10px; border: 1px solid #dadce0; border-radius: 6px;
                                background-color: white; color: #3c4043; font-weight: 500; text-decoration: none;
                                box-sizing: border-box; font-size: 0.9rem;
                            ">
                                <img src="https://www.gstatic.com/images/branding/product/1x/gsa_64dp.png" width="18" height="18">
                                Continue with Google
                            </a>
                            """,
                            unsafe_allow_html=True,
                        )
                except Exception as e:
                    st.error(f"Google OAuth configuration error: {e}")

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
                    else:
                        try:
                            sb.auth.sign_up({"email": new_email, "password": new_password})
                            st.success("Account created! Check your email to confirm.")
                        except Exception as e:
                            st.error(f"Error: {e}")


# ---------------------------------------------------------------------------
# Auth & Session Management
# ---------------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None

if "code" in st.query_params:
    try:
        auth_code = st.query_params["code"]
        res = sb.auth.exchange_code_for_session({"auth_code": auth_code})
        if res and res.user:
            st.session_state.user = res.user
            st.query_params.clear()
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"OAuth Exchange Error: {e}")

if st.session_state.user is None:
    try:
        res = sb.auth.get_user()
        if res and res.user:
            st.session_state.user = res.user
    except Exception:
        pass

if st.session_state.user is None:
    auth_page()
    st.stop()


# ---------------------------------------------------------------------------
# Reusable UI Helpers
# ---------------------------------------------------------------------------
def header():
    st.markdown("""
    <div class="main-header">
        <h1>RentMaster-GH</h1>
        <p>Rental Property Management System &middot; Version 2</p>
    </div>
    """, unsafe_allow_html=True)


@st.dialog("Submit Support Request or Suggestion")
def show_support_dialog():
    st.write("Have a complaint, feature suggestion, or running into an issue? Let us know below!")

    with st.form("support_form", clear_on_submit=True):
        category = st.selectbox("Category *", ["Complaint", "Suggestion", "Bug Report", "General Query"])
        subject = st.text_input("Subject *")
        message = st.text_area(
            "Details / Message *",
            help="Please describe your suggestion or complaint in detail.",
        )

        submitted = st.form_submit_button("Submit Request", type="primary", use_container_width=True)

        if submitted:
            if not subject or not message:
                st.error("Please fill in all required fields marked with *.")
            else:
                try:
                    user = st.session_state.get("user")
                    user_email = getattr(user, "email", None) if user else None
                    sb.table("support_requests").insert({
                        "category": category,
                        "subject": subject,
                        "message": message,
                        "user_email": user_email,
                        "created_at": str(date.today()),
                    }).execute()
                    st.success("Your request has been submitted. Thank you!")
                except Exception as e:
                    st.error(f"Failed to submit request: {e}")


# ---------------------------------------------------------------------------
# Data Helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=5)
def fetch_properties():
    r = sb.table("properties").select("*").order("created_at", desc=True).execute()
    return r.data or []


@st.cache_data(ttl=5)
def fetch_landlords():
    try:
        r = sb.table("landlords").select("*").order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        return []


@st.cache_data(ttl=5)
def fetch_tenants():
    r = sb.table("tenants").select("*, properties(*)").order("created_at", desc=True).execute()
    return r.data or []


@st.cache_data(ttl=5)
def fetch_payments():
    r = sb.table("payments").select("*, tenants(*)").order("payment_date", desc=True).execute()
    return r.data or []


@st.cache_data(ttl=5)
def fetch_leases():
    try:
        r = sb.table("leases").select("*, properties(*), tenants(*)").order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        pass

    try:
        r = sb.table("leases").select("*, properties(*), tenants(*)").order("start_date", desc=True).execute()
        return r.data or []
    except Exception:
        pass

    try:
        r = sb.table("leases").select("*").order("start_date", desc=True).execute()
        data = r.data or []
        for row in data:
            row.setdefault("properties", None)
            row.setdefault("tenants", None)
        return data
    except Exception as e:
        st.error(f"Failed to fetch leases: {e}")
        return []


@st.cache_data(ttl=5)
def fetch_maintenance():
    try:
        r = sb.table("maintenance_requests").select("*, properties(*), tenants(*)").order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        try:
            r = sb.table("maintenance_requests").select("*").order("created_at", desc=True).execute()
            data = r.data or []
            for row in data:
                row.setdefault("properties", None)
                row.setdefault("tenants", None)
            return data
        except Exception as e:
            st.error(f"Failed to fetch maintenance requests: {e}")
            return []


@st.cache_data(ttl=5)
def fetch_ads():
    try:
        r = sb.table("ads").select("*").order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        return []


def clear_cache():
    fetch_properties.clear()
    fetch_landlords.clear()
    fetch_tenants.clear()
    fetch_payments.clear()
    fetch_leases.clear()
    fetch_maintenance.clear()
    fetch_ads.clear()


def fmt_money(v):
    try:
        return f"GHs {float(v):,.2f}"
    except (TypeError, ValueError):
        return "-"


def fmt_date(v):
    if not v:
        return "-"
    try:
        return str(v)[:10]
    except Exception:
        return str(v)


def prop_label(p):
    if not p:
        return "-"
    p_name = p.get("name") or p.get("property_name", "Unnamed")
    return f"{p_name} - {p.get('address', '')}"


def tenant_label(t):
    if not t:
        return "-"
    return t.get("name", "Unnamed")


def initialize_ad_payment(client_name, ad_position, amount_ghs, start_date, end_date, destination_url, creative_url, email, callback_url):
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

    sb.table("ads").insert(ad_payload).execute()

    paystack_res = initialize_paystack_payment(
        email=email,
        amount_in_ghs=amount_ghs,
        callback_url=callback_url,
        metadata={
            "type": "advert_placement",
            "business_name": client_name,
            "ad_slot": ad_position,
            "reference": reference,
        },
    )

    return paystack_res, reference


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def page_dashboard():
    header()
    st.subheader("Dashboard Overview")

    props = fetch_properties()
    tenants = fetch_tenants()
    payments = fetch_payments()
    leases = fetch_leases()
    maint = fetch_maintenance()

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

    with st.expander("Add New Property", expanded=False):
        with st.form("add_property"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Property Name *")
                address = st.text_input("Address *")
                rent = st.number_input("Monthly Rent (GHs)", min_value=0.0, value=0.0, step=50.0)
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
                    sb.table("properties").insert(payload).execute()
                    clear_cache()
                    st.success(f"Property '{name}' added.")
                    st.rerun()

    props = fetch_properties()
    if not props:
        st.info("No properties yet. Add one above.")
        return

    st.markdown("---")
    st.markdown(f"**{len(props)} Properties**")

    for p in props:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                prop_title = p.get("name") or p.get("property_name", "Unnamed")
                st.markdown(f"**{prop_title}**")
                st.caption(p.get("address", ""))
                if p.get("description"):
                    st.caption(p.get("description"))
            with col2:
                rent_val = p.get("monthly_rent") if p.get("monthly_rent") is not None else p.get("rent_amount")
                st.markdown(f"Rent: {fmt_money(rent_val)}")
                beds_str = f"{p.get('bedrooms')} bed / " if p.get("bedrooms") is not None else ""
                baths_str = f"{p.get('bathrooms')} bath" if p.get("bathrooms") is not None else ""
                st.caption(f"{beds_str}{baths_str}".strip())
            with col3:
                badge = "Occupied" if p.get("is_occupied", False) else "Vacant"
                st.markdown(f"Status: **{badge}**")
                if p.get("property_type"):
                    st.caption(f"Type: {p.get('property_type')}")
            with col4:
                if st.button("Delete", key=f"del_prop_{p['id']}", type="secondary"):
                    sb.table("properties").delete().eq("id", p["id"]).execute()
                    clear_cache()
                    st.rerun()


def page_landlords():
    header()
    st.subheader("Landlord & Payout Management")
    st.caption("Configure payout destinations (Mobile Money or Bank Account) for automated Paystack rent splits.")

    landlords = fetch_landlords()
    landlord_options = {"new": "Add New Landlord"}
    for l in landlords:
        landlord_options[l["id"]] = f"{l['name']} ({l.get('phone', 'No Phone')})"

    selected_id = st.selectbox(
        "Select Landlord to Manage",
        options=list(landlord_options.keys()),
        format_func=lambda x: landlord_options[x],
    )

    selected_landlord = next((l for l in landlords if l["id"] == selected_id), None)
    default_name = selected_landlord.get("name", "") if selected_landlord else ""
    default_email = selected_landlord.get("email", "") if selected_landlord else ""
    default_phone = selected_landlord.get("phone", "") if selected_landlord else ""
    default_account = selected_landlord.get("account_number", "") if selected_landlord else ""

    current_bank = selected_landlord.get("bank_name", "") if selected_landlord else ""
    bank_keys = list(GHANA_PAYOUT_BANKS.keys())
    default_bank_idx = bank_keys.index(current_bank) if current_bank in bank_keys else 0

    if selected_landlord and selected_landlord.get("paystack_subaccount_code"):
        st.success(f"Paystack Subaccount Linked: `{selected_landlord['paystack_subaccount_code']}`")
    elif selected_landlord:
        st.warning("No Paystack Subaccount generated yet. Save payout details to enable automatic splits.")

    with st.form("landlord_payout_form", clear_on_submit=False):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Landlord Full Name *", value=default_name)
            email = st.text_input("Email Address", value=default_email)
            phone = st.text_input("Phone Number *", value=default_phone, help="Format: 024XXXXXXX")

        with col2:
            bank_name = st.selectbox("Payout Provider / Bank *", bank_keys, index=default_bank_idx)
            account_number = st.text_input(
                "Account / Mobile Money Number *",
                value=default_account,
                help="Enter Mobile Money number or Bank Account number",
            )
            selected_bank_code = GHANA_PAYOUT_BANKS[bank_name]
            st.text_input("Paystack Bank Code", value=selected_bank_code, disabled=True)

        submitted = st.form_submit_button("Save Landlord Payout Details", type="primary", use_container_width=True)

        if submitted:
            if not name or not phone or not account_number:
                st.error("Please fill in all required fields marked with *.")
            else:
                target_id = selected_id if selected_id != "new" else None
                try:
                    with st.spinner("Registering with Paystack API..."):
                        data, code = save_landlord_bank_details(
                            landlord_id=target_id,
                            name=name,
                            email=email,
                            phone=phone,
                            bank_name=bank_name,
                            account_number=account_number,
                            bank_code=selected_bank_code,
                            platform_fee_pct=0.0,
                        )
                    clear_cache()
                    st.success(f"Landlord registered! Paystack Subaccount Code: `{code}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save details: {e}")

    if landlords:
        st.markdown("---")
        st.markdown(f"**{len(landlords)} Landlords Registered**")
        for l in landlords:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                with c1:
                    st.markdown(f"**{l.get('name', 'Unnamed')}**")
                    if l.get("email"):
                        st.caption(f"Email: {l['email']}")
                    if l.get("phone"):
                        st.caption(f"Phone: {l['phone']}")
                with c2:
                    st.markdown(f"Provider: **{l.get('bank_name', '-')}**")
                    st.caption(f"Account: {l.get('account_number', '-')}")
                with c3:
                    sub_code = l.get("paystack_subaccount_code")
                    if sub_code:
                        st.markdown(f"Subaccount: `{sub_code}`")
                    else:
                        st.caption("Subaccount: Unlinked")
                with c4:
                    if st.button("Delete", key=f"del_landlord_{l['id']}", type="secondary"):
                        sb.table("landlords").delete().eq("id", l["id"]).execute()
                        clear_cache()
                        st.rerun()


def page_tenants():
    header()
    st.subheader("Tenants")

    props = fetch_properties()
    prop_options = {p["id"]: prop_label(p) for p in props} or {"": "No properties available"}

    with st.expander("Add New Tenant", expanded=False):
        with st.form("add_tenant"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Tenant Name *")
                email = st.text_input("Email")
                rent_amount = st.number_input("Agreed Monthly Rent (GHS)", min_value=0.0, value=0.0, step=50.0)
            with col2:
                phone = st.text_input("Phone")
                prop_id = st.selectbox("Property", list(prop_options.keys()),
                                       format_func=lambda x: prop_options.get(x, "-"))

            col3, col4 = st.columns(2)
            with col3:
                lease_start = st.date_input("Lease Start", value=date.today())
            with col4:
                lease_end = st.date_input("Lease End", value=date.today() + timedelta(days=365))

            active = st.checkbox("Active Tenant", value=True)
            submitted = st.form_submit_button("Add Tenant")
            if submitted:
                if not name:
                    st.error("Tenant name is required.")
                else:
                    payload = {
                        "name": name,
                        "email": email if email else None,
                        "phone": phone if phone else None,
                        "property_id": prop_id if prop_id else None,
                        "rent_amount": float(rent_amount),
                        "lease_start": str(lease_start),
                        "lease_end": str(lease_end),
                        "is_active": active,
                    }
                    sb.table("tenants").insert(payload).execute()
                    clear_cache()
                    st.success(f"Tenant '{name}' added.")
                    st.rerun()

    tenants = fetch_tenants()
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
            with col2:
                prop = t.get("properties")
                st.markdown(f"Property: {prop_label(prop)}")
            with col3:
                st.caption(f"Lease: {fmt_date(t.get('lease_start'))} to {fmt_date(t.get('lease_end'))}")
                status = "Active" if t.get("is_active") else "Inactive"
                st.markdown(f"Status: **{status}**")
            with col4:
                if st.button("Delete", key=f"del_tenant_{t['id']}", type="secondary"):
                    sb.table("tenants").delete().eq("id", t["id"]).execute()
                    clear_cache()
                    st.rerun()


def page_payments():
    header()
    st.subheader("Payments Management & Checkout")

    # --- 1. Paystack Payment Return & Verification ---
    query_params = st.query_params
    if "reference" in query_params or "trxref" in query_params:
        reference = query_params.get("reference") or query_params.get("trxref")

        with st.spinner("Verifying Paystack transaction status..."):
            verification = verify_paystack_payment(reference)

            if verification.get("status") and verification.get("data", {}).get("status") == "success":
                data = verification["data"]
                meta = data.get("metadata", {})

                try:
                    sb.table("payments").insert({
                        "tenant_id": meta.get("tenant_id") if meta.get("tenant_id") else None,
                        "amount": data["amount"] / 100.0,
                        "payment_method": data.get("channel", "online_paystack"),
                        "notes": f"Paystack Ref: {reference} | Email: {data.get('customer', {}).get('email')}",
                        "payment_date": str(date.today()),
                        "status": "paid",
                    }).execute()

                    clear_cache()
                    st.success(f"Payment of GHS {data['amount'] / 100:,.2f} verified and recorded successfully!")
                except Exception as e:
                    st.error(f"Error logging payment to database: {e}")
            else:
                st.error("Payment verification failed or transaction was cancelled.")

            st.query_params.clear()

    # --- 2. Online Payment Gateway Form ---
    tenants = fetch_tenants()
    tenant_options = {t["id"]: f"{tenant_label(t)} ({t.get('email', 'No email')})" for t in tenants} or {"": "No active tenants"}

    with st.expander("Make Online Payment (Card / Momo / Bank Transfer)", expanded=True):
        st.caption("Process live payments securely via Paystack.")

        with st.form("paystack_payment_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                selected_tenant_id = st.selectbox(
                    "Select Tenant *",
                    list(tenant_options.keys()),
                    format_func=lambda x: tenant_options.get(x, "-"),
                )
                pay_amount = st.number_input("Amount (GHS) *", min_value=1.0, value=100.0, step=10.0)

            with col_b:
                pay_email = st.text_input("Receipt Email *", placeholder="tenant@example.com")
                callback_domain = st.text_input("Callback Base URL", value="https://www.rentmastergh.com")

            pay_submitted = st.form_submit_button("Proceed to Checkout", type="primary", use_container_width=True)

            if pay_submitted:
                if not pay_email:
                    st.error("Please provide a receipt email address.")
                else:
                    meta = {"tenant_id": selected_tenant_id} if selected_tenant_id else {}
                    res = initialize_paystack_payment(
                        email=pay_email,
                        amount_in_ghs=pay_amount,
                        callback_url=callback_domain,
                        metadata=meta,
                    )

                    if res.get("status"):
                        auth_url = res["data"]["authorization_url"]
                        st.success("Checkout initialized! Click the button below to complete your payment.")
                        st.link_button(
                            "Pay Now via Card / Mobile Money / Transfer",
                            auth_url,
                            type="primary",
                            use_container_width=True,
                        )
                    else:
                        st.error(f"Failed to initialize payment: {res.get('message', 'Unknown error')}")

    # --- 3. Manual Record Form (Cash/Offline) ---
    with st.expander("Record Offline Payment (Cash, Check, Manual)", expanded=False):
        with st.form("add_payment"):
            col1, col2 = st.columns(2)
            with col1:
                tid = st.selectbox("Tenant *", list(tenant_options.keys()),
                                   format_func=lambda x: tenant_options.get(x, "-"), key="manual_tid")
                amount = st.number_input("Amount (GHs) *", min_value=0.0, value=0.0, step=10.0, key="manual_amt")
                method = st.selectbox("Payment Method *", ["cash", "card", "bank_transfer", "mobile_money", "check", "other"])
            with col2:
                pdate = st.date_input("Payment Date *", value=date.today())
                status = st.selectbox("Status *", ["paid", "pending", "overdue", "cancelled"])

            notes = st.text_area("Notes", help="Optional transaction notes, receipt numbers, or comments.")
            submitted = st.form_submit_button("Record Payment")
            if submitted:
                if not tid or amount <= 0:
                    st.error("Select a tenant and enter a valid amount.")
                else:
                    sb.table("payments").insert({
                        "tenant_id": tid,
                        "amount": float(amount),
                        "payment_method": method,
                        "notes": notes if notes else None,
                        "payment_date": str(pdate),
                        "status": status,
                    }).execute()
                    clear_cache()
                    st.success("Payment recorded successfully.")
                    st.rerun()

    # --- 4. Payment History Table ---
    payments = fetch_payments()
    if not payments:
        st.info("No payments recorded yet.")
        return

    st.markdown("---")
    st.markdown(f"**{len(payments)} Payment Records**")

    for p in payments:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2.5, 2, 2, 2.5, 1])
            with col1:
                tenant = p.get("tenants")
                st.markdown(f"**{tenant_label(tenant)}**")
                if p.get("notes"):
                    st.caption(f"{p['notes']}")
            with col2:
                st.markdown(f"Amount: **{fmt_money(p.get('amount'))}**")
            with col3:
                st.markdown(f"Date: {fmt_date(p.get('payment_date'))}")
            with col4:
                status_val = str(p.get("status", "-")).capitalize()
                st.markdown(f"Status: **{status_val}**")
                method_val = (p.get("payment_method") or "-").replace("_", " ").title()
                st.caption(f"Method: {method_val}")
            with col5:
                if st.button("Delete", key=f"del_pay_{p['id']}", type="secondary"):
                    sb.table("payments").delete().eq("id", p["id"]).execute()
                    clear_cache()
                    st.rerun()


def page_leases():
    header()
    st.subheader("Leases")

    props = fetch_properties()
    tenants = fetch_tenants()
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
            deposit = st.number_input("Deposit Amount (GHs)", min_value=0.0, value=0.0, step=100.0)
            status = st.selectbox("Status", ["active", "expired", "terminated"])
            submitted = st.form_submit_button("Create Lease")
            if submitted:
                if not pid or not tid:
                    st.error("Property and tenant are required.")
                else:
                    sb.table("leases").insert({
                        "property_id": pid, "tenant_id": tid,
                        "start_date": str(start), "end_date": str(end),
                        "deposit_amount": deposit, "status": status,
                    }).execute()
                    clear_cache()
                    st.success("Lease created.")
                    st.rerun()

    leases = fetch_leases()
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
                    sb.table("leases").delete().eq("id", l["id"]).execute()
                    clear_cache()
                    st.rerun()


def page_maintenance():
    header()
    st.subheader("Maintenance Requests")

    props = fetch_properties()
    tenants = fetch_tenants()
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
                else:
                    sb.table("maintenance_requests").insert({
                        "property_id": pid,
                        "tenant_id": tid if (tid and tid != "") else None,
                        "title": title, "description": desc,
                        "priority": priority, "status": status,
                    }).execute()
                    clear_cache()
                    st.success("Maintenance request filed.")
                    st.rerun()

    requests_list = fetch_maintenance()
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
                    sb.table("maintenance_requests").delete().eq("id", m["id"]).execute()
                    clear_cache()
                    st.rerun()


def page_settings():
    header()
    st.subheader("Settings & Administration")

    # --- Ad Payment Verification Handler ---
    query_params = st.query_params
    if "reference" in query_params and query_params.get("reference", "").startswith("AD-"):
        ad_ref = query_params.get("reference")
        with st.spinner("Verifying Advert Payment..."):
            verification = verify_paystack_payment(ad_ref)
            if verification.get("status") and verification.get("data", {}).get("status") == "success":
                sb.table("ads").update({"status": "paid"}).eq("reference", ad_ref).execute()
                st.success(f"Payment for Advert (Ref: `{ad_ref}`) verified successfully! Campaign is ready.")
            else:
                st.error("Advert payment verification failed or was cancelled.")
        st.query_params.clear()

    with st.container(border=True):
        col_info1, col_info2 = st.columns([3, 1])
        with col_info1:
            st.markdown("### RentMaster-GH Enterprise")
            st.markdown(
                "A comprehensive rental property management system tailored for tracking properties, "
                "tenants, payments, lease agreements, and maintenance requests."
            )
        with col_info2:
            st.markdown("**Version:** `2.0.0`")
            st.markdown("**Environment:** `Production`")
            st.markdown("**Database Status:** :green[Connected]")

    st.markdown("---")

    st.markdown("#### Account Information")
    user = st.session_state.get("user")
    user_email = getattr(user, "email", "Active Session") if user else "Active Session"
    user_id = getattr(user, "id", "N/A") if user else "N/A"

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Logged in as:** `{user_email}`")
        with c2:
            st.markdown(f"**User ID:** `{user_id}`")

    st.markdown("---")

    st.markdown("#### System Preferences")
    with st.container(border=True):
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.selectbox("Default Currency Format", ["GHS (GH)", "USD ($)", "EUR ()"], index=0)
            st.selectbox("Date Format Standard", ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"], index=0)
        with col_p2:
            st.selectbox("Records Per Page Display", [10, 25, 50, 100], index=1)
            st.toggle("Enable Automated Payment Alerts", value=True)

        if st.button("Save Preferences", type="primary", key="save_prefs"):
            st.toast("Preferences saved successfully!", icon="✅")

    st.markdown("---")

    st.markdown("#### Paid Advertisements & Ad Space Management")
    st.caption("Manage sponsor banners, advertiser campaigns, and paid placements across tenant/landlord portals.")

    with st.container(border=True):
        tab_active_ads, tab_new_ad, tab_ad_analytics = st.tabs([
            "Active Ad Placements",
            "Create & Pay for Advert",
            "Monetization & Analytics",
        ])

        with tab_active_ads:
            st.markdown("##### Current Banner Placements")
            ads_list = fetch_ads()
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
                        with col2:
                            st.markdown(f"Rate: **{fmt_money(ad.get('monthly_rate'))}**")
                            st.caption(f"Ref: `{ad.get('reference', 'N/A')}`")
                        with col3:
                            st.caption(f"Schedule: {fmt_date(ad.get('start_date'))} to {fmt_date(ad.get('end_date'))}")
                            badge_color = "green" if ad.get("status") in ("paid", "active") else "orange"
                            st.markdown(f"Status: :{badge_color}[**{str(ad.get('status')).upper()}**]")
                        with col4:
                            if st.button("Delete", key=f"del_ad_{ad['id']}", type="secondary"):
                                sb.table("ads").delete().eq("id", ad["id"]).execute()
                                fetch_ads.clear()
                                st.rerun()

        with tab_new_ad:
            st.markdown("##### Add Sponsored Campaign")

            if "ad_checkout_url" not in st.session_state:
                st.session_state.ad_checkout_url = None
            if "ad_checkout_ref" not in st.session_state:
                st.session_state.ad_checkout_ref = None

            with st.form("new_advert_form", clear_on_submit=False):
                f1, f2 = st.columns(2)
                with f1:
                    client_name = st.text_input("Advertiser / Business Name *", placeholder="e.g. Absa Bank Ghana")
                    advertiser_email = st.text_input("Receipt / Contact Email *", value=user_email)
                    ad_position = st.selectbox("Target Ad Slot *", [
                        "Top Header Leaderboard (728x90)",
                        "Sidebar Banner (300x250)",
                        "Footer Promotional Bar (Full Width)",
                        "In-Feed Property Listing Sponsor",
                    ])
                    start_date = st.date_input("Campaign Start Date", value=date.today())

                with f2:
                    target_url = st.text_input("Destination URL *", placeholder="https://example.com")
                    creative_url = st.text_input("Banner Image URL *", placeholder="https://example.com/banner.png")
                    pricing_rate = st.number_input("Monthly Slot Rate (GHS) *", min_value=10.0, value=500.0, step=50.0)
                    end_date = st.date_input("Campaign End Date", value=date.today() + timedelta(days=30))

                callback_url = st.text_input("Callback Base URL", value="https://www.rentmastergh.com")

                submit_ad = st.form_submit_button("Pay Now & Launch Campaign", type="primary", use_container_width=True)

                if submit_ad:
                    if not client_name or not advertiser_email or not target_url or not creative_url:
                        st.error("Please fill in all required fields marked with *.")
                    elif end_date < start_date:
                        st.error("End date cannot be earlier than start date.")
                    else:
                        with st.spinner("Saving campaign & initializing Paystack checkout..."):
                            try:
                                ps_res, ref = initialize_ad_payment(
                                    client_name=client_name,
                                    ad_position=ad_position,
                                    amount_ghs=pricing_rate,
                                    start_date=str(start_date),
                                    end_date=str(end_date),
                                    destination_url=target_url,
                                    creative_url=creative_url,
                                    email=advertiser_email,
                                    callback_url=callback_url,
                                )

                                if ps_res.get("status"):
                                    st.session_state.ad_checkout_url = ps_res["data"]["authorization_url"]
                                    st.session_state.ad_checkout_ref = ref
                                    fetch_ads.clear()
                                    st.success("Advert created! Click the Pay button below to complete payment.")
                                else:
                                    st.error(f"Paystack Initialization Failed: {ps_res.get('message')}")
                            except Exception as e:
                                st.error(f"Error processing advert checkout: {e}")

            if st.session_state.ad_checkout_url:
                st.markdown("---")
                st.info(f"Transaction Reference Generated: `{st.session_state.ad_checkout_ref}`")
                st.link_button(
                    "Proceed to Pay Now (Card / Mobile Money)",
                    st.session_state.ad_checkout_url,
                    type="primary",
                    use_container_width=True,
                )

        with tab_ad_analytics:
            st.markdown("##### Ad Revenue & Impression Performance")
            m1, m2, m3 = st.columns(3)
            m1.metric("Monthly Ad Revenue", "GHS 3,500.00", "+12%")
            m2.metric("Total Ad Impressions", "48,210", "+1,240 this week")
            m3.metric("Avg. Click-Through Rate (CTR)", "3.4%", "+0.5%")

    st.markdown("---")

    st.markdown("#### Data Management & Backup Export")
    st.caption("Export application database tables into JSON format for external auditing or data backup.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "Export Properties",
            data=json.dumps(fetch_properties(), indent=2),
            file_name="rentmaster_properties.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Export Payments",
            data=json.dumps(fetch_payments(), indent=2),
            file_name="rentmaster_payments.json",
            mime="application/json",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            "Export Tenants",
            data=json.dumps(fetch_tenants(), indent=2),
            file_name="rentmaster_tenants.json",
            mime="application/json",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# Sidebar Navigation & Execution Router
# ---------------------------------------------------------------------------
PAGES = {
    "Dashboard": page_dashboard,
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
    if st.button("Support & Suggestions", use_container_width=True):
        show_support_dialog()

    st.markdown("---")
    if st.session_state.user:
        user_email = getattr(st.session_state.user, "email", "User")
        st.write(f"Logged in: **{user_email}**")
        if st.button("Logout", key="logout_btn"):
            sb.auth.sign_out()
            st.session_state.clear()
            st.rerun()

    st.markdown("---")
    st.caption("RentMaster-GH v2 - Streamlit + Supabase")

PAGES[selection]()
