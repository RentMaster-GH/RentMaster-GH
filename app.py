import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="RentMaster GH", layout="centered")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check if user is already logged in
if "user" not in st.session_state:
    st.session_state.user = None

st.title("🔒 RentMaster GH")

# If logged in, show dashboard
if st.session_state.user:
    st.success(f"Welcome back, {st.session_state.user.email}!")
    st.subheader("📊 Dashboard")
    st.write("This is where your tenants and rent will show up.")
    
    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()
        
# If NOT logged in, show Login/SignUp
else:
    tab1, tab2 = st.tabs(["Login", "Sign Up"])

    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if res.user:
                st.session_state.user = res.user
                st.rerun()
            else:
                st.error("Login failed")

    with tab2:
        new_email = st.text_input("New Email", key="signup_email")
        new_password = st.text_input("New Password", type="password", key="signup_pass")
        if st.button("Create Account"):
            res = supabase.auth.sign_up({"email": new_email, "password": new_password})
            if res.user:
                st.success("Account created! Check your email to confirm, then Login.")
            else:
                st.error("Signup failed")
