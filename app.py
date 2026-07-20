import streamlit as st
import pandas as pd

st.set_page_config(page_title="RentMaster GH", page_icon="🏠", layout="wide")
st.title("🏠 RentMaster GH")
st.subheader("Property & Tenant Management for Ghana Landlords")

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Properties", "Tenants", "Payments", "Settings"])

if "properties" not in st.session_state:
    st.session_state.properties = pd.DataFrame({
        "Property": ["2 Bedroom Flat - East Legon", "Chamber & Hall - Madina"],
        "Rent": [2500, 800],
        "Status": ["Occupied", "Vacant"]
    })

if "tenants" not in st.session_state:
    st.session_state.tenants = pd.DataFrame({
        "Name": ["Kwame Mensah", "Ama Boateng"],
        "Property": ["2 Bedroom Flat - East Legon", "Chamber & Hall - Madina"],
        "Due Date": ["2026-05-01", "2026-05-15"]
    })

if page == "Dashboard":
    st.header("📊 Dashboard")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Properties", len(st.session_state.properties))
    col2.metric("Occupied", len(st.session_state.properties[st.session_state.properties.Status == "Occupied"]))
    col3.metric("Vacant", len(st.session_state.properties[st.session_state.properties.Status == "Vacant"]))
    st.subheader("Upcoming Rent Due")
    st.dataframe(st.session_state.tenants)
else:
    st.header(f"{page}")
    st.write("Page content goes here")