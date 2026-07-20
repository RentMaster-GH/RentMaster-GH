import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="RentMaster GH", layout="centered")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🔒 RentMaster GH")

tab1, tab2 = st.tabs(["Login", "Sign Up"])

with tab1:
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            st.success(f"Logged in as {res.user.email}")
        else:
            st.error("Login failed")

with tab2:
    new_email = st.text_input("New Email", key="signup_email")
    new_password = st.text_input("New Password", type="password", key="signup_pass")
    if st.button("Create Account"):
        res = supabase.auth.sign_up({"email": new_email, "password": new_password})
        if res.user:
            st.success("Account created! Check your email to confirm.")
        else:
            st.error("Signup failed")
