"""
RentMaster-GH - Public Property Discovery & Paid Advert Marketplace Portal
Allows prospective tenants to search, filter, and inquire about paid property listings.
Includes Shared Facilities & Occupancy Disclosures, real photo uploads, and Paystack PROP- checkout.
"""
import base64
import uuid
from urllib.parse import quote
import streamlit as st
from services.database import sb

try:
    from services.paystack import initialize_paystack_payment
except ImportError:
    initialize_paystack_payment = None

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
        "image_url": "https://unsplash.com",
        "landlord_name": "Chief Kwame Appiah",
        "contact_phone": "+233200000001",
        "description": "Spacious fully furnished apartment with air conditioning, 24/7 security, standby generator, and swimming pool access.",
        "shared_washroom": False,
        "shared_electricity": False,
        "shared_water": False,
        "shared_compound": True,
        "landlord_resides_on_compound": False,
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
        "image_url": "https://unsplash.com",
        "landlord_name": "Madam Abena Osei",
        "contact_phone": "+2348000000002",
        "description": "Newly renovated residential home with fitted kitchen, prepaid meter, and clean running water.",
        "shared_washroom": False,
        "shared_electricity": False,
        "shared_water": True,
        "shared_compound": True,
        "landlord_resides_on_compound": True,
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
        "image_url": "https://unsplash.com",
        "landlord_name": "RentMaster Properties Ltd",
        "contact_phone": "+233240000003",
        "description": "High-visibility commercial building suitable for corporate headquarters, bank branch, or retail store.",
        "shared_washroom": True,
        "shared_electricity": False,
        "shared_water": False,
        "shared_compound": True,
        "landlord_resides_on_compound": False,
    },
]


def _build_whatsapp_link(phone: str, title: str, location: str = "") -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits.startswith("0") and len(digits) == 10:
        digits = "233" + digits[1:]
    msg = f"Hello, I am interested in '{title}'" + (f" in {location}" if location else "") + " listed on RentMaster-GH."
    return f"https://wa.me{digits}?text={quote(msg)}" if digits else f"https://wa.me?text={quote(msg)}"


def _render_listing_image(img_val: str):
    s = str(img_val or "").strip()
    if s.startswith("data:") and ";base64," in s:
        _, b64 = s.split(";base64,", 1)
        st.image(base64.b64decode(b64), use_container_width=True)
    else:
        st.image(s or "https://unsplash.com", use_container_width=True)


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


def render_public_featured_properties():
    """Renders the Paid Property Discovery Portal for prospective tenants."""
    st.markdown("### 🔍 Find Properties & Paid Listings Showcase")
    st.caption("Browse vacant properties advertised by property owners across Ghana and worldwide.")

    listings = fetch_paid_property_adverts()

    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    with f_col1:
        search_query = st.text_input("🔍 Search by Location or Keywords", placeholder="e.g. Accra, Kumasi, East Legon, 3-Bedroom...").lower()
    with f_col2:
        type_filter = st.selectbox("Property Type", ["All Types", "Apartment", "House", "Commercial"])
    with f_col3:
        max_price = st.number_input("Max Rent Price", min_value=0.0, value=10000.0, step=500.0)

    filtered_listings = []
    for item in listings:
        match_query = not search_query or (search_query in item.get("title", "").lower() or search_query in item.get("location", "").lower())
        match_type = type_filter == "All Types" or item.get("property_type", "").lower() == type_filter.lower()
        match_price = float(item.get("price", 0) or 0) <= max_price
        if match_query and match_type and match_price:
            filtered_listings.append(item)

    st.markdown("<br>", unsafe_allow_html=True)

    if not filtered_listings:
        st.info("ℹ️ No properties matched your search filter criteria. Try adjusting your search query.")
        return

    cols = st.columns(min(3, len(filtered_listings)))
    for idx, prop in enumerate(filtered_listings):
        with cols[idx % 3]:
            with st.container(border=True):
                _render_listing_image(prop.get("image_url"))
                st.markdown(f"#### {prop.get('title')}")
                st.markdown(f"💰 Rent: **{prop.get('currency', 'GHS')} {float(prop.get('price', 0) or 0):,.2f}** / Month")
                st.caption(f"📍 {prop.get('location')}")
                st.caption(f"🏠 {prop.get('property_type')} · 🛏️ {prop.get('bedrooms', 0)} Beds · 🚿 {prop.get('bathrooms', 0)} Baths")

                if prop.get("description"):
                    desc = str(prop["description"])
                    st.write(desc[:110] + ("..." if len(desc) > 110 else ""))

                with st.expander("🏘️ Shared Facilities & Compound Disclosures", expanded=True):
                    st.write(f"• **Washroom:** {'⚠️ Shared with occupants' if prop.get('shared_washroom') else '✅ Private / En-Suite'}")
                    st.write(f"• **Electricity Meter:** {'⚠️ Shared Meter' if prop.get('shared_electricity') else '✅ Separate Private Meter'}")
                    st.write(f"• **Water Supply:** {'⚠️ Shared Water Supply' if prop.get('shared_water') else '✅ Private Water Tank / Meter'}")
                    st.write(f"• **Compound & Yard:** {'⚠️ Shared Compound' if prop.get('shared_compound', True) else '✅ Private Compound'}")
                    st.write(f"• **Landlord Presence:** {'🏠 Landlord resides on same compound' if prop.get('landlord_resides_on_compound') else '🌿 Landlord resides off-site'}")

                st.divider()

                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    wa_url = _build_whatsapp_link(prop.get("contact_phone"), prop.get("title", "Property"), prop.get("location", ""))
                    st.link_button("💬 WhatsApp", wa_url, type="primary", use_container_width=True)
                with btn_col2:
                    if st.button("📞 Details", key=f"details_btn_{prop.get('id', idx)}", use_container_width=True):
                        st.toast(f"Contact {prop.get('landlord_name', 'Landlord')}: {prop.get('contact_phone', 'N/A')}")


@st.dialog("🏠 List Vacant Property for Rent (GH₵ 50 / $5)", width="large")
def show_public_property_listing_dialog():
    st.write("Advertise your vacant rental property to prospective tenants across Ghana and worldwide!")
    user = st.session_state.get("user")
    default_email = getattr(user, "email", "") if user else ""

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
            p_phone = st.text_input("WhatsApp / Contact Phone *", placeholder="+233240000000")

        lister_email = st.text_input("Receipt Email *", value=default_email, placeholder="landlord@example.com")
        p_desc = st.text_area("Property Features & Description")

        st.markdown("---")
        st.markdown("##### 🏘️ Disclose Shared Facilities to Tenants")
        c_dis1, c_dis2 = st.columns(2)
        with c_dis1:
            p_washroom = st.checkbox("Shared Washroom/Toilet", value=False)
            p_elec = st.checkbox("Shared Electricity Meter", value=False)
        with c_dis2:
            p_water = st.checkbox("Shared Water Supply", value=False)
            p_landlord = st.checkbox("Landlord Resides on Same Compound", value=False)

        p_photo_file = st.file_uploader("Upload Property Photo (PNG / JPG / WEBP)", type=["png", "jpg", "jpeg", "webp"])
        p_img_url = st.text_input("Or Paste Property Photo URL", value="https://unsplash.com")

        st.info("💳 Listing Fee: **GH₵ 50 ($5 USD)** for 30 Days Global Showcase.")

        if st.form_submit_button("💳 Pay GH₵ 50 & Publish Advert Live", type="primary", use_container_width=True):
            if not p_title.strip() or not p_location.strip() or not p_phone.strip() or not lister_email.strip():
                st.error("Please fill in title, location, WhatsApp phone, and receipt email.")
            else:
                final_img = p_img_url.strip()
                if p_photo_file is not None:
                    raw = p_photo_file.getvalue()
                    mime = getattr(p_photo_file, "type", None) or "image/jpeg"
                    final_img = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

                ref_code = f"PROP-{uuid.uuid4().hex[:10].upper()}"
                listing_record = {
                    "id": f"ad_prop_{uuid.uuid4().hex[:8]}",
                    "reference": ref_code,
                    "title": p_title.strip(),
                    "location": p_location.strip(),
                    "price": float(p_price),
                    "currency": p_curr,
                    "property_type": p_type,
                    "bedrooms": int(p_beds),
                    "bathrooms": int(p_baths),
                    "image_url": final_img,
                    "contact_phone": p_phone.strip(),
                    "whatsapp_link": _build_whatsapp_link(p_phone, p_title.strip(), p_location.strip()),
                    "description": p_desc.strip(),
                    "shared_washroom": p_washroom,
                    "shared_electricity": p_elec,
                    "shared_water": p_water,
                    "shared_compound": True,
                    "landlord_resides_on_compound": p_landlord,
                    "status": "pending_payment",
                }

                if sb:
                    try:
                        sb.table("public_listings").insert(listing_record).execute()
                    except Exception:
                        pass

                if initialize_paystack_payment:
                    fee_amt = 50.0 if p_curr == "GHS" else 5.0
                    ps_res = initialize_paystack_payment(
                        email=lister_email.strip(),
                        amount_in_main_unit=fee_amt,
                        callback_url="https://rentmastergh.com",
                        metadata={"type": "property_listing", "reference": ref_code, "title": p_title.strip()},
                        currency=p_curr if p_curr in ("GHS", "USD", "NGN") else "GHS",
                    )
                    auth_url = (ps_res.get("data") or {}).get("authorization_url") if isinstance(ps_res, dict) else None
                    if auth_url:
                        st.success(f"✅ Listing reserved (`{ref_code}`). Complete payment below to publish live immediately!")
                        st.link_button("👉 Complete Payment on Paystack", auth_url, type="primary", use_container_width=True)
                    else:
                        st.error(f"❌ Paystack Checkout Unavailable: {(ps_res or {}).get('message', 'Check PAYSTACK_SECRET_KEY')}")
