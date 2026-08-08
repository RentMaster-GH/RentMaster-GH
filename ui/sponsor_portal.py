# ui/sponsor_portal.py
import uuid
import streamlit as st
from datetime import date, timedelta
from services.helpers import get_current_currency, fmt_money, fmt_date, convert_and_fmt_money
from services.database import sb, upload_id_to_supabase
from services.paystack import initialize_paystack_payment
from ui.pages_core import header


@st.dialog("💬 Contact App Manager & Customer Service")
def show_sponsor_support_dialog():
    st.write("Have a custom advertising request, billing question, or special sponsorship inquiry? Fill out the form below to connect directly with the App Manager.")
    
    with st.form("sponsor_support_form", clear_on_submit=True):
        s_name = st.text_input("Your Name / Business Name *")
        s_email = st.text_input("Email Address *")
        s_phone = st.text_input("Phone Number")
        s_subject = st.selectbox("Inquiry Subject", [
            "Custom Advertising Package",
            "Payment / Invoice Assistance",
            "Banner Design Help",
            "General Manager Inquiry"
        ])
        s_message = st.text_area("Details / Message *", placeholder="Describe your concern or inquiry...")

        if st.form_submit_button("Submit to App Manager", type="primary", use_container_width=True):
            if not s_name or not s_email or not s_message:
                st.error("Please fill in all required fields marked with *.")
            elif sb:
                try:
                    sb.table("support_requests").insert({
                        "category": f"Sponsor Inquiry: {s_subject}",
                        "subject": f"Sponsor [{s_name}]: {s_subject}",
                        "message": f"From: {s_name} ({s_email}, {s_phone})\n\n{s_message}",
                        "user_email": s_email,
                        "created_at": str(date.today()),
                    }).execute()
                    st.success("✅ Your message has been sent directly to the App Manager. We will respond within 2-4 hours!")
                except Exception as e:
                    st.error(f"Failed to submit message: {e}")


def render_sponsor_portal():
    header()
    
    st.markdown(
        """
        <div style="background: linear-gradient(135deg, #0f4c75 0%, #1b262c 100%); padding: 1.8rem; border-radius: 12px; color: white; margin-bottom: 1.5rem;">
            <h2 style="color: white; margin: 0 0 0.4rem 0;">📢 Self-Service Sponsor & Advertiser Portal</h2>
            <p style="color: #bbdefb; margin: 0; font-size: 0.95rem;">
                Launch your automated promotional campaign in under 2 minutes. Reach property owners, landlords, and tenants across Ghana & West Africa.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    curr_code = get_current_currency()

    # Manager Support Header Bar
    m_col1, m_col2 = st.columns([3, 1])
    with m_col1:
        st.caption("⚡ 100% Automated Campaign Setup & Instant Paystack Activation.")
    with m_col2:
        if st.button("💬 Contact Manager & Support", use_container_width=True, type="secondary"):
            show_sponsor_support_dialog()

    tab_launch, tab_track = st.tabs([
        "💳 Launch Campaign & Pay Online",
        "📊 Track Existing Campaign"
    ])

    # TAB 1: SELF-SERVICE CAMPAIGN LAUNCH & PAYSTACK CHECKOUT
    with tab_launch:
        st.markdown("#### Step 1: Campaign Details & Placement Selection")
        
        with st.form("sponsor_self_service_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                business_name = st.text_input("Business / Brand Name *", placeholder="e.g. Absa Bank Ghana")
                contact_email = st.text_input("Receipt / Contact Email *", placeholder="marketing@business.com")
                contact_phone = st.text_input("Phone Number *", placeholder="e.g. 024XXXXXXX or +233XXXXXXX")
                target_url = st.text_input("Website Destination Link *", placeholder="https://www.yourbusiness.com")

            with col2:
                slot_prices = {
                    "Login Page Sidebar Banner": 500.0,
                    "Top Header Leaderboard (728x90)": 750.0,
                    "In-Feed Property Listing Sponsor": 450.0,
                    "Footer Promotional Bar (Full Width)": 350.0
                }
                ad_slot = st.selectbox(
                    "Target Ad Slot Placement *",
                    options=list(slot_prices.keys()),
                    help="Select where your promotional banner will be displayed on the platform."
                )
                monthly_rate = slot_prices[ad_slot]
                st.info(f"Standard Monthly Slot Rate: **{convert_and_fmt_money(monthly_rate, curr_code)} / Month**")

            st.markdown("#### Step 2: Schedule Duration & Dynamic Price Calculator")
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                start_date = st.date_input("Campaign Start Date *", value=date.today())
            with c_d2:
                end_date = st.date_input("Campaign End Date *", value=date.today() + timedelta(days=30))

            # Calculate Prorated Price based on duration
            campaign_days = (end_date - start_date).days
            daily_rate = monthly_rate / 30.0
            total_cost = max(daily_rate, daily_rate * max(1, campaign_days))

            # Multi-Currency Dual Display
            formatted_checkout_text = convert_and_fmt_money(total_cost, curr_code)

            st.markdown(
                f"""
                <div style="background-color: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 1rem; margin-top: 0.5rem; margin-bottom: 1rem;">
                    <span style="color: #166534; font-weight: 600; font-size: 0.9rem;">Calculated Duration: <b>{max(1, campaign_days)} Days</b></span><br/>
                    <span style="color: #15803d; font-weight: 800; font-size: 1.25rem;">Total Checkout Amount: {formatted_checkout_text}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("#### Step 3: Upload Advert Banner Creative")
            banner_file = st.file_uploader("Upload Creative Image Banner (PNG, JPG, JPEG) *", type=["png", "jpg", "jpeg"])
            banner_url_fallback = st.text_input("OR Enter Image Web URL", placeholder="https://example.com/banner.png")

            callback_domain = st.text_input("Callback Base URL", value="https://www.rentmastergh.com")

            if st.form_submit_button("💳 Proceed to Instant Paystack Payment", type="primary", use_container_width=True):
                if not business_name or not contact_email or not target_url:
                    st.error("Please fill in all required business fields marked with *.")
                elif not banner_file and not banner_url_fallback:
                    st.error("Please upload an image banner file or enter a banner URL.")
                elif end_date <= start_date:
                    st.error("End date must be after start date.")
                else:
                    with st.spinner("Processing banner upload & initializing Paystack Checkout..."):
                        try:
                            creative_url = banner_url_fallback
                            if banner_file:
                                creative_url = upload_id_to_supabase(banner_file, business_name, folder="ads")

                            reference = f"AD-{uuid.uuid4().hex[:10].upper()}"

                            if sb:
                                sb.table("ads").insert({
                                    "business_name": business_name,
                                    "ad_slot": ad_slot,
                                    "monthly_rate": float(total_cost),
                                    "start_date": str(start_date),
                                    "end_date": str(end_date),
                                    "destination_url": target_url,
                                    "creative_url": creative_url,
                                    "status": "pending_payment",
                                    "reference": reference,
                                }).execute()

                            paystack_res = initialize_paystack_payment(
                                email=contact_email,
                                amount_in_main_unit=total_cost,
                                callback_url=callback_domain,
                                metadata={
                                    "type": "advert_placement",
                                    "business_name": business_name,
                                    "ad_slot": ad_slot,
                                    "reference": reference
                                },
                                currency=curr_code
                            )

                            if paystack_res.get("status"):
                                st.success("✅ Campaign registered! Click the payment link below to launch your ad instantly.")
                                st.link_button("👉 Complete Paystack Checkout (Card / Mobile Money)", paystack_res["data"]["authorization_url"], type="primary", use_container_width=True)
                            else:
                                st.error(f"Paystack initialization failed: {paystack_res.get('message')}")
                        except Exception as e:
                            st.error(f"Error launching campaign: {e}")

    # TAB 2: TRACK EXISTING CAMPAIGN
    with tab_track:
        st.markdown("#### 📊 Track Your Advertising Campaign")
        lookup_ref = st.text_input("Enter your Campaign Reference or Contact Email", placeholder="e.g. AD-XXXXX or marketing@business.com")
        
        if st.button("Search Campaign Status", type="secondary"):
            if lookup_ref and sb:
                try:
                    res = sb.table("ads").select("*").or_(f"reference.eq.{lookup_ref},business_name.ilike.%{lookup_ref}%").execute()
                    ads = res.data or []
                    if ads:
                        for ad in ads:
                            with st.container(border=True):
                                c1, c2, c3 = st.columns(3)
                                c1.markdown(f"**{ad.get('business_name')}**")
                                c1.caption(f"Slot: {ad.get('ad_slot')}")
                                c2.markdown(f"Rate Paid: **{convert_and_fmt_money(ad.get('monthly_rate'), curr_code)}**")
                                c2.caption(f"Ref: `{ad.get('reference')}`")
                                status_color = "green" if ad.get("status") in ("paid", "active") else "orange"
                                c3.markdown(f"Status: :{status_color}[**{str(ad.get('status')).upper()}**]")
                                c3.caption(f"Active: {fmt_date(ad.get('start_date'))} to {fmt_date(ad.get('end_date'))}")
                    else:
                        st.info("No matching campaign found for that reference.")
                except Exception as e:
                    st.error(f"Error looking up campaign: {e}")
