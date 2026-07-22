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
    st.session_state.properties = []if 'tenants' not in st.session_state:
    st.session_state.tenants = []
    page = st.sidebar.selectbox("Navigation", ["📊 Dashboard", "🏠 Properties", "👥 Tenants"])

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

        elif page == "👥 Tenants":
    st.title("👥 Tenants")
    st.write("Manage tenants for your properties")
    
    # Add new tenant form
    with st.form("add_tenant_form"):
        st.subheader("Add New Tenant")
        
        # Dropdown to pick which property
        property_names = [p['name'] for p in st.session_state.properties]
        if property_names:
            prop_choice = st.selectbox("Select Property", property_names)
        else:
            st.warning("Add a property first!")
            prop_choice = ""
            
        tenant_name = st.text_input("Tenant Name", placeholder="e.g. Kofi Mensah")
        phone = st.text_input("Phone Number", placeholder="e.g. 0241234567")
        move_in = st.date_input("Move-in Date")
        submitted_tenant = st.form_submit_button("Save Tenant")
        
        if submitted_tenant and tenant_name and prop_choice:
            st.session_state.tenants.append({
                "name": tenant_name, 
                "phone": phone, 
                "property": prop_choice,
                "move_in": str(move_in)
            })
            st.success(f"Tenant '{tenant_name}' added to {prop_choice}!")
            st.rerun()
elif page == "👥 Tenants":  # Line 144 - GOOD
    st.title("👥 Tenants")
    st.write("Manage tenants for your properties")
    
    # ... your form code above ...

    # Show all tenants
    st.subheader("Your Tenants")
    if st.session_state.tenants:
        for tenant in st.session_state.tenants:
            st.write(f"**{tenant['name']}** - {tenant['property']} - 📞 {tenant['phone']}") # <-- FIX LINE 147
    else:
        st.info("No tenants yet. Add one above!") # <-- DELETE LINE 156