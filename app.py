"""
RentMaster-GH v2 - Rental Management Streamlit Web App
Full interactive UI backed by Supabase. Manages properties, tenants,
payments, leases, and maintenance requests with a dashboard overview.
"""

import os
from datetime import datetime, date, timedelta
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# ====== GOOGLE LOGIN + SIGNUP CODE ======
SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

if "user" not in st.session_state:
    st.session_state.user = None

def auth_page():
    st.title("Welcome to RentMaster-GH")
    tab1, tab2 = st.tabs(["Login", "Sign Up"]) # <-- THIS LINE WAS MISSING

    with tab1:
        st.subheader("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pw")
        
        if st.button("Login with Email", use_container_width=True, key="login_btn"):
            try:
                res = sb.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success("Logged in!")
                st.rerun()
            except Exception as e:
                st.error("Invalid email or password")
        
        st.divider()
        redirect_url = "https://www.rentmastergh.com" 
        res = sb.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {"redirect_to": redirect_url}
        })
        if res.url:
            st.link_button("Continue with Google", res.url, use_container_width=True)

    with tab2:
        st.subheader("Create Account")
        new_email = st.text_input("Email Address", key="signup_email")
        confirm_email = st.text_input("Confirm Email Address", key="confirm_email")
        new_password = st.text_input("Password", type="password", key="signup_pw")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pw")

        if st.button("Sign Up", use_container_width=True, key="signup_btn"):
            if new_email != confirm_email:
                st.error("Emails do not match")
            elif new_password != confirm_password:
                st.error("Passwords do not match")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                try:
                    res = sb.auth.sign_up({"email": new_email, "password": new_password})
                    st.success("Account created! Check your email to confirm.")
                except Exception as e:
                    st.error(f"Error: {e}")

if st.session_state.user is None:
    auth_page()
    st.stop() 

# Logout button in sidebar
with st.sidebar:
    st.write(f"👤 {st.session_state.user.email}")
    if st.button("Logout"):
        sb.auth.sign_out()
        st.session_state.user = None
        st.rerun()
# ====== END AUTH CODE ======


@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# rest of your app.py continues here...

sb = get_client() # <-- Now use the real sb for the rest of the app

# Add logout to sidebar
with st.sidebar:
    st.write(f"Logged in: {st.session_state.user.email}")
    if st.button("Logout"):
        sb.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# Page config & theme
st.set_page_config(
    page_title="RentMaster-GH",
    page_icon=":house:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a polished look
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
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        text-align: center;
    }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f4c75;
    }
    .metric-card .label {
        font-size: 0.85rem;
        color: #666;
        margin-top: 0.3rem;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
    }
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    .dataframe th {
        background-color: #0f4c75 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)


def header():
    st.markdown("""
    <div class="main-header">
        <h1>RentMaster-GH</h1>
        <p>Rental Property Management System &middot; Version 2</p>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=5)
def fetch_properties():
    r = sb.table("properties").select("*").order("created_at", desc=True).execute()
    return r.data or []


@st.cache_data(ttl=5)
def fetch_tenants():
    r = sb.table("tenants").select("*, properties(*)").order("created_at", desc=True).execute()
    return r.data or []


@st.cache_data(ttl=5)
def fetch_payments():
    r = sb.table("payments").select("*, tenants(*)").order("paid_at", desc=True).execute()
    return r.data or []


@st.cache_data(ttl=5)
def fetch_leases():
    """
    Robust lease fetch:
    1) Try embedded relations + created_at order
    2) Fallback to embedded relations + start_date order
    3) Fallback to plain leases table
    Never raises to UI; returns [] on total failure.
    """
    # Attempt 1: original query
    try:
        r = (
            sb.table("leases")
            .select("*, properties(*), tenants(*)")
            .order("created_at", desc=True)
            .execute()
        )
        return r.data or []
    except Exception as e1:
        st.warning(f"Leases query fallback #1 triggered: {e1}")

    # Attempt 2: if created_at does not exist
    try:
        r = (
            sb.table("leases")
            .select("*, properties(*), tenants(*)")
            .order("start_date", desc=True)
            .execute()
        )
        return r.data or []
    except Exception as e2:
        st.warning(f"Leases query fallback #2 triggered: {e2}")

    # Attempt 3: no relationship embedding (FK/embed issues)
    try:
        r = sb.table("leases").select("*").order("start_date", desc=True).execute()
        data = r.data or []

        # Normalize shape so UI code using l.get('properties') / l.get('tenants') won't break
        for row in data:
            row.setdefault("properties", None)
            row.setdefault("tenants", None)
        return data
    except Exception as e3:
        st.error(f"Failed to fetch leases after all fallbacks: {e3}")
        return []


@st.cache_data(ttl=5)
def fetch_maintenance():
    r = sb.table("maintenance_requests").select("*, properties(*), tenants(*)").order("created_at", desc=True).execute()
    return r.data or []


def clear_cache():
    fetch_properties.clear()
    fetch_tenants.clear()
    fetch_payments.clear()
    fetch_leases.clear()
    fetch_maintenance.clear()


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
    return f"{p.get('name', 'Unnamed')} - {p.get('address', '')}"


def tenant_label(t):
    if not t:
        return "-"
    return t.get("name", "Unnamed")


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

    expected = sum(float(p.get("rent_amount", 0) or 0) for p in props)
    collected = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("status") == "paid")
    pending = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("status") == "pending")
    overdue = sum(float(p.get("amount", 0) or 0) for p in payments if p.get("status") == "overdue")
    occupied = sum(1 for p in props if p.get("is_occupied"))

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

    # Occupancy breakdown
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
                beds = st.number_input("Bedrooms", min_value=0, value=1)
                baths = st.number_input("Bathrooms", min_value=0, value=1)
            desc = st.text_area("Description")
            occupied = st.checkbox("Currently Occupied")
            submitted = st.form_submit_button("Add Property")
            if submitted:
                if not name or not address:
                    st.error("Property name and address are required.")
                else:
                    sb.table("properties").insert({
                        "name": name, "address": address, "rent_amount": rent,
                        "description": desc, "property_type": ptype,
                        "bedrooms": int(beds), "bathrooms": int(baths),
                        "is_occupied": occupied,
                    }).execute()
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
                st.markdown(f"**{p.get('name', 'Unnamed')}**")
                st.caption(p.get("address", ""))
                if p.get("description"):
                    st.caption(p.get("description"))
            with col2:
                st.markdown(f"Rent: {fmt_money(p.get('rent_amount'))}")
                st.caption(f"{p.get('bedrooms', 0)} bed / {p.get('bathrooms', 0)} bath")
            with col3:
                badge = "Occupied" if p.get("is_occupied") else "Vacant"
                st.markdown(f"Status: **{badge}**")
                st.caption(f"Type: {p.get('property_type', '-')}")
            with col4:
                if st.button("Delete", key=f"del_prop_{p['id']}", type="secondary"):
                    sb.table("properties").delete().eq("id", p["id"]).execute()
                    clear_cache()
                    st.rerun()


def page_tenants():
    header()
    st.subheader("Tenants")

    props = fetch_properties()
    prop_options = {p["id"]: prop_label(p) for p in props}

    with st.expander("Add New Tenant", expanded=False):
        with st.form("add_tenant"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Tenant Name *")
                email = st.text_input("Email")
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
                    sb.table("tenants").insert({
                        "name": name, "email": email, "phone": phone,
                        "property_id": prop_id if prop_id else None,
                        "lease_start": str(lease_start),
                        "lease_end": str(lease_end),
                        "is_active": active,
                    }).execute()
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
    st.subheader("Payments")

    tenants = fetch_tenants()
    tenant_options = {t["id"]: tenant_label(t) for t in tenants}

    with st.expander("Record New Payment", expanded=False):
        with st.form("add_payment"):
            col1, col2 = st.columns(2)
            with col1:
                tid = st.selectbox("Tenant *", list(tenant_options.keys()),
                                   format_func=lambda x: tenant_options.get(x, "-"))
                amount = st.number_input("Amount (GHs) *", min_value=0.0, value=0.0, step=10.0)
            with col2:
                pdate = st.date_input("Payment Date", value=date.today())
                status = st.selectbox("Status", ["paid", "pending", "overdue"])
            method = st.selectbox("Payment Method", ["cash", "card", "bank_transfer", "check", "other"])
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Record Payment")
            if submitted:
                if not tid or amount <= 0:
                    st.error("Select a tenant and enter a valid amount.")
                else:
                    sb.table("payments").insert({
                        "tenant_id": tid,
                        "amount": amount,
                        "payment_date": str(pdate),
                        "status": status,
                        "payment_method": method,
                        "notes": notes,
                    }).execute()
                    clear_cache()
                    st.success("Payment recorded.")
                    st.rerun()

    payments = fetch_payments()
    if not payments:
        st.info("No payments recorded yet.")
        return

    st.markdown("---")
    st.markdown(f"**{len(payments)} Payments**")

    for p in payments:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            with col1:
                tenant = p.get("tenants")
                st.markdown(f"**{tenant_label(tenant)}**")
            with col2:
                st.markdown(f"Amount: {fmt_money(p.get('amount'))}")
            with col3:
                st.markdown(f"Date: {fmt_date(p.get('payment_date'))}")
            with col4:
                st.markdown(f"Status: **{p.get('status', '-')}**")
                st.caption(f"Method: {p.get('payment_method', '-')}")
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
    prop_options = {p["id"]: prop_label(p) for p in props}
    tenant_options = {t["id"]: tenant_label(t) for t in tenants}

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
    prop_options = {p["id"]: prop_label(p) for p in props}
    tenant_options = {t["id"]: tenant_label(t) for t in tenants}

    with st.expander("File New Request", expanded=False):
        with st.form("add_maintenance"):
            col1, col2 = st.columns(2)
            with col1:
                pid = st.selectbox("Property *", list(prop_options.keys()),
                                   format_func=lambda x: prop_options.get(x, "-"))
                title = st.text_input("Title *")
            with col2:
                tid = st.selectbox("Tenant (optional)", [""] + list(tenant_options.keys()),
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
                        "tenant_id": tid if tid else None,
                        "title": title, "description": desc,
                        "priority": priority, "status": status,
                    }).execute()
                    clear_cache()
                    st.success("Maintenance request filed.")
                    st.rerun()

    requests = fetch_maintenance()
    if not requests:
        st.info("No maintenance requests yet.")
        return

    st.markdown("---")
    st.markdown(f"**{len(requests)} Maintenance Requests**")

    for m in requests:
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
    st.subheader("Settings & About")
    st.markdown("""
    **RentMaster-GH v2** is a rental property management system built with
    Streamlit and Supabase. It manages properties, tenants, payments,
    leases, and maintenance requests.

    **Tech Stack:**
    - Python 3.11 + Streamlit
    - Supabase (PostgreSQL database)
    - python-dotenv for environment variables

    **Features:**
    - Dashboard with portfolio analytics
    - Full CRUD for properties, tenants, payments, leases, and maintenance
    - File upload support (up to 200 MB)
    - WebSocket-enabled for real-time updates
    - Custom domain ready

    **Data:** All data is stored in your Supabase project. The app uses
    the anon key with RLS policies allowing public read/write access
    (single-tenant, no-auth mode).
    """)

    st.markdown("---")
    st.markdown("#### Environment Configuration")
    st.code(f"SUPABASE_URL: {SUPABASE_URL[:30]}..." if SUPABASE_URL else "SUPABASE_URL: not set")
    st.code(f"ANON_KEY: {'set' if SUPABASE_KEY else 'not set'}")

    st.markdown("---")
    st.markdown("#### Data Export")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export Properties (JSON)"):
            st.download_button("Download", str(fetch_properties()), "properties.json", "application/json")
    with col2:
        if st.button("Export Payments (JSON)"):
            st.download_button("Download", str(fetch_payments()), "payments.json", "application/json")


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

PAGES = {
    "Dashboard": page_dashboard,
    "Properties": page_properties,
    "Tenants": page_tenants,
    "Payments": page_payments,
    "Leases": page_leases,
    "Maintenance": page_maintenance,
    "Settings": page_settings,
}

st.sidebar.markdown("### Navigation")
selection = st.sidebar.radio("Go to", list(PAGES.keys()))
st.sidebar.markdown("---")
st.sidebar.markdown("RentMaster-GH v2")
st.sidebar.caption("Streamlit + Supabase")

PAGES[selection]()
