import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os

# --- CONFIG ---
SUPABASE_URL = "https://weaijarwinxurmbriqi.supabase.co"  # Get this from Supabase > Project Settings > API
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndlYWpqYXJ3bG54dXJibWJyaXFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQxMDYxNDMsImV4cCI6MjA5OTY4MjE0M30.pY0BCVOkRkeAmXTg3RdWfP1s9d7vLCLmUvZSnpnOMRU" # Get this from Supabase > Project Settings > API
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- AUTH FUNCTIONS ---
def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.rerun()
    except Exception as e:
        st.error("Login failed: " + str(e))

def signup(email, password):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        st.success("Account created! Check your email to confirm.")
    except Exception as e:
        st.error("Signup failed: " + str(e))

def logout():
    supabase.auth.sign_out()
    st.session_state.pop("user", None)
    st.rerun()

# --- MAIN APP ---
def main_app():
    user = st.session_state.user
    st.sidebar.button("Logout", on_click=logout)
    st.sidebar.write(f"Logged in as: {user.email}")
    
    st.title("RentMaster GH")
    st.subheader("Property & Tenant Management for Ghana Landlords")

    # Load data for THIS user only
    properties = supabase.table("properties").select("*").eq("user_id", user.id).execute().data
    tenants = supabase.table("tenants").select("*").eq("user_id", user.id).execute().data

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Properties", len(properties))
    col2.metric("Occupied", len([p for p in properties if p['status']=='Occupied']))
    col3.metric("Vacant", len([p for p in properties if p['status']=='Vacant']))

    st.write("---")
    st.subheader("Your Properties")
    if properties:
        st.dataframe(pd.DataFrame(properties)[['name','location','status']])
    else:
        st.info("No properties yet. Add one below!")
        
    st.subheader("Your Tenants")
    if tenants:
        st.dataframe(pd.DataFrame(tenants)[['name','rent_amount']])
    else:
        st.info("No tenants yet.")

# --- LOGIN PAGE ---
def login_page():
    st.title("🔒 RentMaster GH Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            login(email, password)
    
    with tab2:
        email = st.text_input("New Email")
        password = st.text_input("New Password", type="password")
        if st.button("Create Account"):
            signup(email, password)

# --- ROUTER ---
if "user" not in st.session_state:
    login_page()
else:
    main_app()
