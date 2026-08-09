"""
RentMaster-GH - Public Property Discovery & Paid Advert Marketplace Portal
Allows prospective tenants to search, filter, and inquire about paid property listings.
"""
import streamlit as st
import json
from services.database import sb

# Demo Featured Property Adverts
DEFAULT_PAID_ADVERTS = [
    {
        "id": "ad_prop_1",
        "title": "Luxury 3-Bedroom Executive Apartment",
        "location": "East Legon, Accra, Ghana 🇬🇭",
        "price": 2500.00,
        "currency": "GHS",
        "property_type": "Apartment",
        "bedrooms": 3,
        "bathrooms": 2,
        "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800",
        "landlord_name": "Chief Kwame Appiah",
        "contact_phone": "+233200000001",
        "whatsapp_link": "https://wa.me/233200000001?text=Hi%2C%20I%20am%20interested%20in%20your%20East%20Legon%20Apartment%20advertised%20on%20RentMaster-GH.",
        "description": "Spacious fully furnished apartment with air conditioning, 24/7 security, standby generator, and swimming pool access."
    },
    {
        "id": "ad_prop_2",
        "title": "Modern 2-Bedroom Gated House",
        "location": "Lekki Phase 1, Lagos, Nigeria 🇳🇬",
        "price": 1800.00,
        "currency": "USD",
        "property_type": "House",
        "bedrooms": 2,
        "bathrooms": 2,
        "image_url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800",
        "landlord_name": "Madam Abena Osei",
        "contact_phone": "+2348000000002",
        "whatsapp_link": "https://wa.me/2348000000002?text=Hello%2C%20I%20saw%20your%20Lagos%20property%20listing%20on%20RentMaster-GH.",
        "description": "Newly renovated residential home with fitted kitchen, prepaid meter, and clean running water."
    },
    {
        "id": "ad_prop_3",
        "title": "Prime Commercial Office / Retail Space",
        "location": "Airport Residential Area, Accra, Ghana 🇬🇭",
        "price": 4000.00,
        "currency": "GHS",
        "property_type": "Commercial",
        "bedrooms": 0,
        "bathrooms": 2,
        "image_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?w=800",
        "landlord_name": "RentMaster Properties Ltd",
        "contact_phone": "+233240000003",
        "whatsapp_link": "https://wa.me/233240000003?text=Inquiry%20regarding%20Commercial%20Office%20Space.",
        "description": "High-visibility commercial building suitable for corporate headquarters, bank branch, or retail store."
    }
]


def fetch_paid_property_adverts():
    """Fetch active paid property listings from Supabase or fallback data."""
    if not sb:
        return st.session_state.get("paid_property_adverts", DEFAULT_PAID_ADVERTS)

    try:
        res = sb.table("public_listings").select("*").eq("status", "paid").execute()
        if res.data:
            return res.data
    except Exception:
        pass

    return st.session_state.get("paid_property_adverts", DEFAULT_PAID_ADVERTS)


# ---------------------------------------------------------------------------
# PUBLIC PROPERTY MARKETPLACE PORTAL
# ---------------------------------------------------------------------------
def render_public_featured_properties():
    """Renders the Paid Property Discovery Portal for prospective tenants."""
    st.markdown("### 🔍 Find Properties & Paid Listings Showcase")
    st.caption("Browse vacant properties advertised by property owners across Ghana and worldwide.")

    listings = fetch_paid_property_adverts()

    # Search & Filter Bar
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_query = st.text_input("🔍 Search by Location or Keywords", placeholder="e.g. Accra, Lagos, East Legon, 3-Bedroom...").lower()
    with f_col2:
        type_filter = st.selectbox("Property Type", ["All Types", "Apartment", "House", "Commercial"])
    with f_col3:
        max_price = st.number_input("Max Rent Price", min_value=0.0, value=10000.0, step=500.0)

    # Filter Logic
    filtered_listings = []
    for item in listings:
        match_query = not search_query or (search_query in item.get("title", "").lower() or search_query in item.get("location", "").lower())
        match_type = type_filter == "All Types" or item.get("property_type", "").lower() == type_filter.lower()
        match_price = float(item.get("price", 0)) <= max_price

        if match_query and match_type and match_price:
            filtered_listings.append(item)

    st.markdown("<br>", unsafe_allow_html=True)

    if not filtered_listings:
        st.info("ℹ️ No properties matched your search filter criteria. Try adjusting your search query.")
        return

    # Render Grid of Paid Property Cards
    cols = st.columns(min(3, len(filtered_listings)))
    for idx, prop in enumerate(filtered_listings):
        with cols[idx % 3]:
            with st.container(border=True):
                # Image
                img_url = prop.get("image_url") or "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800"
                st.image(img_url, use_container_width=True)
                
                # Title & Price Badge
                st.markdown(f"#### {prop.get('title')}")
                st.markdown(f"💰 Rent: **{prop.get('currency', 'GHS')} {float(prop.get('price', 0)):,.2f}** / Month")
                st.caption(f"📍 {prop.get('location')}")
                st.caption(f"🏠 {prop.get('property_type')} &middot; 🛏️ {prop.get('bedrooms', 0)} Beds &middot; 🚿 {prop.get('bathrooms', 0)} Baths")
                
                if prop.get("description"):
                    st.write(prop["description"][:110] + "...")

                st.divider()

                # Tenant Inquiry Action Buttons
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    wa_url = prop.get("whatsapp_link") or f"https://wa.me/{str(prop.get('contact_phone')).replace('+', '')}"
                    st.link_button("💬 WhatsApp", wa_url, type="primary", use_container_width=True)
                with btn_col2:
                    if st.button("📞 Details", key=f"details_btn_{prop.get('id', idx)}", use_container_width=True):
                        st.toast(f"Contact Landlord {prop.get('landlord_name')}: {prop.get('contact_phone')}")


# ---------------------------------------------------------------------------
# PUBLIC LISTING CREATION DIALOG (FOR LANDLORDS TO PAY GH₵ 50 / $5)
# ---------------------------------------------------------------------------
@st.dialog("🏠 List Vacant Property for Rent (GH₵ 50 / $5)", width="large")
def show_public_property_listing_dialog():
    st.write("Advertise your vacant rental property to prospective tenants across the world!")
    
    with st.form("public_property_ad_form"):
        p_title = st.text_input("Property Title *", placeholder="e.g., Executive 2-Bedroom Apartment")
        p_location = st.text_input("Location / City & Country *", placeholder="e.g., East Legon, Accra, Ghana")
        
        c1, c2 = st.columns(2)
        with c1:
            p_price = st.number_input("Monthly Rent Price *", min_value=1.0, value=1500.0, step=100.0)
            p_curr = st.selectbox("Currency", ["GHS", "USD", "EUR", "NGN", "GBP"])
            p_type = st.selectbox("Type", ["Apartment", "House", "Commercial"])
        with c2:
            p_beds = st.number_input("Bedrooms", min_value=0, value=2)
            p_baths = st.number_input("Bathrooms", min_value=1, value=2)
            p_phone = st.text_input("WhatsApp / Contact Phone *", placeholder="+233200000000")

        p_desc = st.text_area("Property Features & Description")
        p_img = st.text_input("Property Photo URL", value="https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800")

        st.info("💳 Listing Fee: **GH₵ 50 ($5 USD)** for 30 Days Global Showcase.")

        if st.form_submit_button("💳 Pay GH₵ 50 & Publish Advert Live", type="primary", use_container_width=True):
            if not p_title or not p_location or not p_phone:
                st.error("Please fill in all required fields.")
            else:
                new_ad = {
                    "id": f"ad_prop_{json.dumps(p_title).__hash__()}",
                    "title": p_title,
                    "location": p_location,
                    "price": p_price,
                    "currency": p_curr,
                    "property_type": p_type,
                    "bedrooms": p_beds,
                    "bathrooms": p_baths,
                    "image_url": p_img,
                    "contact_phone": p_phone,
                    "whatsapp_link": f"https://wa.me/{p_phone.replace('+', '')}?text=Inquiry%20regarding%20{p_title}",
                    "description": p_desc,
                    "status": "paid"
                }

                if "paid_property_adverts" not in st.session_state:
                    st.session_state["paid_property_adverts"] = DEFAULT_PAID_ADVERTS
                st.session_state["paid_property_adverts"].append(new_ad)

                st.success("🎉 Property Advert Published! Prospective tenants can now discover your property.")
                st.rerun()
