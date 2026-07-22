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
# --- Show Dashboard after login ---
if st.session_state.user:
    st.sidebar.success(f"Logged in as {st.session_state.user}")
    st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"user": None}))
# Create empty list if it doesn't exist yet
if 'properties' not in st.session_state:
    st.session_state.properties = []
    page = st.sidebar.selectbox("Navigate", ["📊 Dashboard", "🏠 Properties"])

    if page == "📊 Dashboard":
        st.title("📊 Dashboard")
        st.write("Welcome to RentMaster GH!")
        st.metric("Total Properties", "0")
        st.metric("Total Tenants", "0")
    
    elif page == "🏠 Properties":
        st.title("🏠 Properties")
        st.write("Add and manage your rental properties")
        
    # Add new property form
    with st.form("add_property"):
        st.subheader("Add New Property")
        name = st.text_input("Property Name", placeholder="e.g. East Legon 2 Bedroom")
        location = st.text_input("Location", placeholder="e.g. Accra, Ghana")
        rent = st.number_input("Monthly Rent (GHS)", min_value=0)
        submitted = st.form_submit_button("Save Property")
        
        if submitted and name:
            st.session_state.properties.append({"name": name, "location": location, "rent": rent})
            st.success(f"Property '{name}' added!")
            st.rerun()

    # Show all properties
    st.subheader("Your Properties")
    if st.session_state.properties:
        for prop in st.session_state.properties:
            st.write(f"**{prop['name']}** - {prop['location']} - GHS {prop['rent']}/month")
    else:
        st.info("No properties yet. Add one above!")
    # Simple version without file save for now
    if 'properties' not in st.session_state:
        st.session_state.properties = []

    # Add new property form
    with st.form("add_property_form"):
        st.subheader("Add New Property")
        name = st.text_input("Property Name", placeholder="e.g. East Legon 2 Bedroom")
        location = st.text_input("Location", placeholder="e.g. Accra, Ghana")
        rent = st.number_input("Monthly Rent (GHS)", min_value=0)
        submitted = st.form_submit_button("Save Property")
        
        if submitted and name:
            st.session_state.properties.append({"name": name, "location": location, "rent": rent})
            st.success(f"Property '{name}' added!")
            st.rerun()

    # Show all properties
    st.subheader("Your Properties")
    if st.session_state.properties:
        for prop in st.session_state.properties:
            st.write(f"**{prop['name']}** - {prop['location']} - GHS {prop['rent']}/month")
    else:
        st.info("No properties yet. Add one above!")