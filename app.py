import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, date
import calendar

# --- PAGE CONFIG ---
st.set_page_config(page_title="RentMaster GH", page_icon="🏠", layout="wide")

# --- CONNECT TO SUPABASE ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- LOGIN / SIGNUP ---
def auth_page():
    st.title("🏠 RentMaster GH")
    st.subheader("Tenant & Rent Management for Landlords")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except:
                st.error("Invalid email or password")
    
    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! Check your email to confirm, then login.")
            except:
                st.error("Error creating account")

# --- MAIN DASHBOARD ---
def dashboard(user):
    st.sidebar.title(f"Welcome 👋")
    st.sidebar.write(user.email)
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.session_state.clear()
        st.rerun()
    
    st.title("📊 RentMaster GH Dashboard")
    
    menu = st.sidebar.selectbox("Menu", ["Overview", "Tenants", "Payments", "Subscription"])
    
    if menu == "Overview":
        show_overview(user)
    elif menu == "Tenants":
        show_tenants(user)
    elif menu == "Payments":
        show_payments(user)
    elif menu == "Subscription":
        show_subscription(user)

# --- OVERVIEW ---
def show_overview(user):
    tenants = supabase.table("tenants").select("*").eq("user_id", user.id).execute().data
    payments = supabase.table("payments").select("*").eq("user_id", user.id).execute().data
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tenants", len(tenants))
    with col2:
        this_month = sum([p['amount'] for p in payments if p['month'] == datetime.now().strftime("%B %Y")])
        st.metric("Collected This Month", f"GHS {this_month}")
    with col3:
        due = [t for t in tenants if t['due_date'] and t['due_date'] <= str(date.today())]
        st.metric("Due for Payment", len(due))
    
    st.subheader("Tenants Due Soon")
    if due:
        st.dataframe(pd.DataFrame(due)[['name', 'room', 'rent', 'due_date']])
    else:
        st.info("No tenants due right now")

# --- TENANTS ---
def show_tenants(user):
    st.subheader("Manage Tenants")
    
    with st.expander("➕ Add New Tenant"):
        with st.form("new_tenant"):
            name = st.text_input("Tenant Name")
            room = st.text_input("Room/House No")
            rent = st.number_input("Monthly Rent GHS", min_value=0)
            phone = st.text_input("Phone")
            due_date = st.date_input("Due Date")
            if st.form_submit_button("Save Tenant"):
                supabase.table("tenants").insert({
                    "user_id": user.id, "name": name, "room": room, 
                    "rent": rent, "phone": phone, "due_date": str(due_date)
                }).execute()
                st.success("Tenant Added!")
                st.rerun()
    
    tenants = supabase.table("tenants").select("*").eq("user_id", user.id).execute().data
    if tenants:
        st.dataframe(pd.DataFrame(tenants))
    else:
        st.info("No tenants yet. Add one above.")

# --- PAYMENTS ---
def show_payments(user):
    st.subheader("Record Payment")
    tenants = supabase.table("tenants").select("*").eq("user_id", user.id).execute().data
    
    if tenants:
        tenant_names = {t['name']: t['id'] for t in tenants}
        tenant = st.selectbox("Select Tenant", list(tenant_names.keys()))
        amount = st.number_input("Amount Paid GHS", min_value=0)
        month = st.selectbox("For Month", [f"{calendar.month_name[i]} {datetime.now().year}" for i in range(1,13)])
        
        if st.button("Record Payment"):
            supabase.table("payments").insert({
                "user_id": user.id,
                "tenant_id": tenant_names[tenant],
                "amount": amount,
                "month": month
            }).execute()
            st.success("Payment Recorded!")
        
        st.subheader("Payment History")
        payments = supabase.table("payments").select("*").eq("user_id", user.id).execute().data
        st.dataframe(pd.DataFrame(payments))
    else:
        st.warning("Add tenants first")

# --- SUBSCRIPTION ---
def show_subscription(user):
    st.subheader("Subscription Plan")
    st.info("Free Plan: 5 Tenants Max")
    st.info("Pro Plan: GHS 50/month - Unlimited Tenants + SMS Reminders")
    st.button("Upgrade to Pro - Coming Soon")

# --- MAIN RUN ---
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    auth_page()
else:
    dashboard(st.session_state.user)