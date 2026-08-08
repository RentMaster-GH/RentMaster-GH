# components/public_showcase.py
import uuid
import urllib.parse
import streamlit as st
from services.helpers import fmt_money, get_current_currency
from services.database import sb, upload_id_to_supabase
from services.paystack import initialize_paystack_payment


@st.dialog("🏠 List Your Property on Public Showcase (GH₵ 50 / $5)", width="large")
def show_public_property_listing_dialog():
    st.write("Promote your vacant apartment, house, or commercial property to thousands of active tenant visitors. Your listing goes live instantly after payment!")
    
    curr_code = get_current_currency()
    fee_amount = 50.0 if curr_code == "GHS" else 5.0

    with st.form("public_property_listing_form"):
        col1, col2 = st.columns(2)
        with col1:
            prop_title = st.text_input("Property / Apartment Title *", placeholder="e.g. Luxury 2-Bedroom Apartment in East Legon")
            location = st.text_input("Location / Address *", placeholder="e.g. East Legon, Accra")
            rent_amount = st.number_input(f"Monthly Rent ({curr_code}) *", min_value=1.0, value=2500.0, step=100.0)
            owner_phone = st.text_input("Landlord WhatsApp Number *", placeholder="e.g. 024XXXXXXX or +233XXXXXXX")

        with col2:
            owner_email = st.text_input("Landlord Email Address *", placeholder="landlord@example.com")
            beds = st.number_input("Bedrooms", min_value=0, value=2)
            baths = st.number_input("Bathrooms", min_value=1, value=2)
            prop_type = st.selectbox("Property Category", ["apartment", "house", "commercial", "studio", "room"])

        description = st.text_area("Property Highlights & Amenities", placeholder="Describe amenities (e.g. AC, 24/7 security, backup generator, water heater)...")
        
        st.markdown("##### Upload Property Photo")
        prop_image_file = st.file_uploader("Upload Image File (PNG, JPG, JPEG) *", type=["png", "jpg", "jpeg"])
        image_url_fallback = st.text_input("OR Enter Image Web Link URL", placeholder="https://example.com/property.jpg")

        callback_domain = st.text_input("Callback Base URL", value="https://www.rentmastergh.com")

        st.info(f"💳 **Listing Fee:** {fmt_money(fee_amount, curr_code)} for 30 Days Public Showcase Promotion.")

        if st.form_submit_button("💳 Pay GH₵ 50 via Paystack & Publish Listing", type="primary", use_container_width=True):
            if not prop_title or not location or not owner_phone or not owner_email:
                st.error("Please fill in all required fields marked with *.")
            elif not prop_image_file and not image_url_fallback:
                st.error("Please upload a property photo or enter an image URL.")
            else:
                with st.spinner("Processing photo & initializing Paystack Checkout..."):
                    try:
                        img_url = image_url_fallback
                        if prop_image_file:
                            img_url = upload_id_to_supabase(prop_image_file, prop_title[:10], folder="public_listings")

                        reference = f"PROP-{uuid.uuid4().hex[:10].upper()}"

                        if sb:
                            sb.table("public_listings").insert({
                                "property_name": prop_title,
                                "location": location,
                                "monthly_rent": float(rent_amount),
                                "currency": curr_code,
                                "bedrooms": int(beds),
                                "bathrooms": int(baths),
                                "contact_phone": owner_phone,
                                "contact_email": owner_email,
                                "image_url": img_url,
                                "description": description,
                                "status": "pending_payment",
                                "reference": reference,
                            }).execute()

                        paystack_res = initialize_paystack_payment(
                            email=owner_email,
                            amount_in_main_unit=fee_amount,
                            callback_url=callback_domain,
                            metadata={
                                "type": "public_property_listing",
                                "property_name": prop_title,
                                "reference": reference
                            },
                            currency=curr_code
                        )

                        if paystack_res.get("status"):
                            st.success("✅ Listing registered! Complete payment below to publish your property live.")
                            st.link_button("👉 Complete Paystack Checkout (Card / Mobile Money)", paystack_res["data"]["authorization_url"], type="primary", use_container_width=True)
                        else:
                            st.error(f"Paystack initialization failed: {paystack_res.get('message')}")
                    except Exception as e:
                        st.error(f"Error initializing listing: {e}")


def render_public_featured_properties():
    """
    Renders paid featured property listings on the public auth screen for visitors.
    """
    try:
        if not sb: return
        res = sb.table("public_listings").select("*").in_("status", ["paid", "active"]).order("created_at", desc=True).execute()
        listings = res.data or []
    except Exception:
        listings = []

    if not listings:
        return

    st.markdown(
        """
        <div style="margin-top: 2.5rem; margin-bottom: 1.2rem; text-align: center;">
            <h3 style="color: #0f4c75; font-weight: 800; margin-bottom: 0.2rem;">🏘️ Featured Properties Available for Rent</h3>
            <p style="color: #64748b; font-size: 0.9rem;">Browse verified properties listed by landlords and property managers across Ghana.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    cols = st.columns(min(3, len(listings)))
    for idx, listing in enumerate(listings):
        with cols[idx % len(cols)]:
            with st.container(border=True):
                if listing.get("image_url"):
                    st.image(listing.get("image_url"), use_container_width=True)
                
                st.markdown(f"#### {listing.get('property_name')}")
                st.caption(f"📍 {listing.get('location')}")
                
                beds_str = f"🛏️ {listing.get('bedrooms')} Beds" if listing.get("bedrooms") else ""
                baths_str = f"🚿 {listing.get('bathrooms')} Baths" if listing.get("bathrooms") else ""
                st.caption(f"{beds_str}  |  {baths_str}")
                
                rent_formatted = fmt_money(listing.get("monthly_rent"), listing.get("currency", "GHS"))
                st.markdown(f"Rent: :green[**{rent_formatted} / Mo**]")

                if listing.get("description"):
                    st.write(listing.get("description")[:110] + "...")

                phone = listing.get("contact_phone", "")
                if phone:
                    phone_clean = "".join(filter(str.isdigit, phone))
                    msg = f"Hello, I am interested in your property listing '{listing.get('property_name')}' on RentMaster-GH."
                    wa_url = f"https://wa.me/{phone_clean}?text={urllib.parse.quote(msg)}"
                    st.link_button("📲 Contact Landlord (WhatsApp)", wa_url, use_container_width=True)
