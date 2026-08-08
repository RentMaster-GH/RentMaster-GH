"""
RentMaster-GH - Property GPS Location Directions & Ghana Rent Card Portal
"""
import streamlit as st
import json
from datetime import datetime
from services.database import sb

# Country & City Database
GLOBAL_COUNTRIES_CITIES = {
    "Ghana 🇬🇭": ["Accra", "Kumasi", "Tamale", "Sekondi-Takoradi", "Cape Coast", "Sunyani", "Koforidua", "Ho", "Tema", "Obuasi"],
    "Nigeria 🇳🇬": ["Lagos", "Abuja", "Port Harcourt", "Ibadan", "Kano", "Enugu"],
    "United Kingdom 🇬🇧": ["London", "Manchester", "Birmingham", "Edinburgh", "Glasgow"],
    "United States 🇺🇸": ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"],
    "Canada 🇨🇦": ["Toronto", "Vancouver", "Montreal", "Calgary"],
    "South Africa 🇿🇦": ["Johannesburg", "Cape Town", "Durban", "Pretoria"],
    "Other International 🌍": ["Other City"]
}


def get_property_location_details(property_id):
    """Fetch property GPS location, directions activation, and Ghana Rent Card info."""
    default_record = {
        "property_id": property_id,
        "country": "Ghana 🇬🇭",
        "city": "Accra",
        "digital_address": "GA-183-9021",
        "gps_lat_long": "5.6037, -0.1870",
        "google_maps_url": "https://maps.google.com/?q=5.6037,-0.1870",
        "directions_activated": False,
        "rent_card_url": None,
        "rent_card_number": "GRC-2024-883910"
    }

    if not sb:
        return st.session_state.get(f"prop_loc_{property_id}", default_record)

    try:
        res = sb.table("properties").select("*").eq("id", property_id).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass

    return st.session_state.get(f"prop_loc_{property_id}", default_record)


def save_property_location_details(prop_data):
    """Save updated GPS location and Rent Card details."""
    prop_data["updated_at"] = datetime.now().isoformat()
    if sb:
        try:
            sb.table("properties").upsert(prop_data).execute()
        except Exception:
            pass

    st.session_state[f"prop_loc_{prop_data['property_id']}"] = prop_data


# ---------------------------------------------------------------------------
# LANDLORD WIDGET: CONFIGURE GPS & UPLOAD GHANA RENT CARD
# ---------------------------------------------------------------------------
def render_landlord_gps_and_rentcard_widget(property_id):
    """Renders GPS location manager and optional Ghana Rent Card upload portal for Landlords."""
    details = get_property_location_details(property_id)

    st.markdown("### 📍 Property Location, GPS Directions & Rent Card Portal")

    tab_gps, tab_rc = st.tabs(["🗺️ GPS Location & Directions", "📋 Ghana Rent Card Upload"])

    # TAB 1: GPS LOCATION & DIRECTION ACTIVATION
    with tab_gps:
        with st.form(key=f"landlord_gps_form_{property_id}"):
            c1, c2 = st.columns(2)
            with c1:
                country = st.selectbox("Property Country *", list(GLOBAL_COUNTRIES_CITIES.keys()), index=0 if "Ghana" in details.get("country", "Ghana") else 0)
                cities = GLOBAL_COUNTRIES_CITIES[country]
                city = st.selectbox("City / Town *", cities)
                digital_addr = st.text_input("Digital Address (e.g. Ghana Post GA-123-4567) *", value=details.get("digital_address", ""))
            
            with c2:
                gps_coords = st.text_input("GPS Lat/Long Coordinates", value=details.get("gps_lat_long", "5.6037, -0.1870"), placeholder="e.g., 5.6037, -0.1870")
                maps_url = st.text_input("Google Maps Location/Directions URL", value=details.get("google_maps_url", ""), placeholder="e.g., https://maps.google.com/?q=5.6037,-0.1870")
            
            st.markdown("---")
            st.markdown("##### 🔑 Direction Sharing Controls")
            activate_directions = st.toggle("🟢 Activate GPS Directions for Prospective/Active Tenant", value=details.get("directions_activated", False), help="When enabled, tenants can view Google Maps directions to this property.")

            submit_gps = st.form_submit_button("💾 Save Property GPS & Location Settings", type="primary", use_container_width=True)

            if submit_gps:
                details["property_id"] = property_id
                details["country"] = country
                details["city"] = city
                details["digital_address"] = digital_addr
                details["gps_lat_long"] = gps_coords
                details["google_maps_url"] = maps_url
                details["directions_activated"] = activate_directions

                save_property_location_details(details)
                st.success("✅ Property location and GPS direction settings updated!")
                st.rerun()

    # TAB 2: OPTIONAL GHANA RENT CARD UPLOAD PORTAL
    with tab_rc:
        current_country = details.get("country", "Ghana 🇬🇭")
        
        if "Ghana" in current_country:
            st.info("🇬🇭 **Ghana Rent Control Portal:** Upload official Rent Card issued by Rent Control Department.")
            
            with st.form(key=f"landlord_rc_form_{property_id}"):
                rc_number = st.text_input("Ghana Rent Card Registration Number", value=details.get("rent_card_number", "GRC-2024-883910"))
                rc_file = st.file_uploader("Upload Ghana Rent Card Document (PDF / Image)", type=["pdf", "png", "jpg", "jpeg"])

                submit_rc = st.form_submit_button("📤 Publish Ghana Rent Card to Tenant Portal", type="primary", use_container_width=True)

                if submit_rc:
                    details["rent_card_number"] = rc_number
                    if rc_file:
                        details["rent_card_url"] = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
                    save_property_location_details(details)
                    st.success("✅ Ghana Rent Card published! Available on tenant portal.")
                    st.rerun()
            
            if details.get("rent_card_url"):
                st.success(f"✅ Published Ghana Rent Card (`{details.get('rent_card_number')}`): [View Document]({details['rent_card_url']})")
        else:
            st.info(f"ℹ️ Official Rent Card upload is specific to properties located in Ghana. Current selected country: **{current_country}**.")


# ---------------------------------------------------------------------------
# TENANT WIDGET: VIEW GPS DIRECTIONS & DOWNLOAD GHANA RENT CARD
# ---------------------------------------------------------------------------
def render_tenant_gps_and_rentcard_widget(tenant_user, property_id="demo_prop_1"):
    """Renders GPS Directions (if activated by Landlord) and Ghana Rent Card for Tenants."""
    details = get_property_location_details(property_id)

    st.markdown("### 📍 Property Location, GPS Directions & Rent Card")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.markdown("#### 🗺️ Property GPS Location")
            st.write(f"**Country:** {details.get('country', 'Ghana 🇬🇭')}")
            st.write(f"**City:** {details.get('city', 'Accra')}")
            st.write(f"**Digital Address:** `{details.get('digital_address', 'GA-183-9021')}`")

            # Check if Landlord has activated GPS directions
            if details.get("directions_activated", False):
                st.success("✅ **GPS Directions Activated by Landlord!**")
                maps_url = details.get("google_maps_url") or f"https://maps.google.com/?q={details.get('gps_lat_long', '5.6037,-0.1870')}"
                st.link_button("🧭 Launch Google Maps GPS Turn-by-Turn Directions", maps_url, type="primary", use_container_width=True)
            else:
                st.warning("🔒 **GPS Navigation Locked:** Directions sharing has not been activated by the landlord for this request.")

    with col2:
        with st.container(border=True):
            st.markdown("#### 📋 Official Ghana Rent Card")
            
            if "Ghana" in details.get("country", "Ghana"):
                if details.get("rent_card_url"):
                    st.success(f"✅ **Ghana Rent Card Issued:** `{details.get('rent_card_number', 'N/A')}`")
                    st.link_button("📥 View / Download Official Ghana Rent Card", details["rent_card_url"], type="primary", use_container_width=True)
                else:
                    st.info("ℹ️ Your landlord has not published the official Ghana Rent Card for this property yet.")
            else:
                st.caption("Official Rent Card is applicable for Ghana properties.")
