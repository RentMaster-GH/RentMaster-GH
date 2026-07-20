import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- SUPABASE LOGIN ---
SUPABASE_URL = "https://weajjarwlnxurbmbriqi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndlYWpqYXJ3bG54dXJibWJyaXFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQxMDYxNDMsImV4cCI6MjA5OTY4MjE0M30.pY0BCVOkRkeAmXTg3RdWfP1s9d7vLCLmUvZSnpnOMRU"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def auth_page():
    st.title("🔒 RentMaster GH Login")
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.rerun()
            except Exception as e:
                st.error("Login failed: " + str(e))
    
    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account"):
            try:
                res = supabase.auth.sign_up({"email": email, "password": password})
                st.success("Account created! Check your email to confirm, then login.")
            except Exception as e:
                st.error("Signup failed: " + str(e))

def main_app():
    st.sidebar.button("Logout", on_click=lambda: [st.session_state.pop("user", None), st.rerun()])
    
    st.title("RentMaster GH")
    st.subheader("Property & Tenant Management for Ghana Landlords")
    
    # --- YOUR EXISTING DASHBOARD CODE GOES HERE ---
    st.metric("Total Properties", 2)
    st.metric("Occupied", 1)
    st.metric("Vacant", 1)
    st.write("Tenants: Kwame Mensah, Ama Boateng")
    st.write("Properties: East Legon, Madina")

# --- ROUTING ---
if "user" not in st.session_state:
    auth_page()
else:
    st.sidebar.write(f"Logged in as: {st.session_state.user.email}")
    main_app()
