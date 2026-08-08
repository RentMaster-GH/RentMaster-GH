# components/ads.py
import streamlit as st
from datetime import date, timedelta
from services.helpers import get_current_currency, fmt_money, fmt_date
from services.database import fetch_ads, sb, clear_cache
from services.paystack import initialize_ad_payment


def render_public_ad_banners(ad_slot: str = None):
    """
    Renders active, paid sponsor banners subtly for visitors and logged-in users.
    Only displays banners with 'paid' or 'active' payment status.
    """
    try:
        ads = fetch_ads()
        active_ads = [
            a for a in ads
            if isinstance(a, dict)
            and a.get("status") in ("paid", "active")
            and (ad_slot is None or a.get("ad_slot") == ad_slot or "Login" in str(a.get("ad_slot")))
        ]
    except Exception:
        active_ads = []

    if not active_ads:
        # Default placeholder when no paid ads exist
        with st.container(border=True):
            st.markdown("##### 🤝 Become a RentMaster Sponsor")
            st.caption("Reach thousands of property owners, landlords, and tenants in Ghana and across West Africa.")
            st.markdown(
                """
                * 📍 High-visibility sidebar & header slots
                * 💳 Instant Paystack activation
                * 📊 Real-time impression tracking
                """
            )
        return

    st.markdown(
        """
        <div style="margin-top: 0.5rem; margin-bottom: 0.8rem;">
            <span style="font-size: 0.75rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;">Verified Platform Sponsors</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    for ad in active_ads:
        with st.container(border=True):
            if ad.get("creative_url"):
                st.image(ad.get("creative_url"), use_container_width=True)
            
            st.markdown(f"**{ad.get('business_name', 'Featured Partner')}**")
            st.caption("Official RentMaster Partner")
            
            if ad.get("destination_url"):
                st.link_button("🌐 Visit Sponsor Website", ad.get("destination_url"), use_container_width=True)


def render_ad_space_management(key_prefix: str = "ad"):
    st.markdown("#### Paid Advertisements & Ad Space Management")
    st.caption("Manage sponsor banners, advertiser campaigns, and paid placements across tenant/landlord portals.")

    curr_code = get_current_currency()
    user = st.session_state.get("user")
    user_email = getattr(user, "email", "") if user else ""
    user_id = getattr(user, "id", None) if user else None

    with st.container(border=True):
        tab_active_ads, tab_new_ad = st.tabs([
            "📢 Active Ad Placements",
            "💳 Create & Pay for Advert"
        ])

        with tab_active_ads:
            st.markdown("##### Current Banner Placements")
            try:
                ads_list = fetch_ads()
            except Exception:
                ads_list = []

            if not ads_list:
                st.info("No advertisement campaigns found in database.")
            else:
                for ad in ads_list:
                    with st.container(border=True):
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        with col1:
                            st.markdown(f"**{ad.get('business_name', 'Unnamed Business')}**")
                            st.caption(f"Slot: {ad.get('ad_slot')}")
                            if ad.get("destination_url"):
                                st.caption(f"URL: [{ad.get('destination_url')}]({ad.get('destination_url')})")
                            if ad.get("creative_url"):
                                st.image(ad.get("creative_url"), width=160)
                        with col2:
                            st.markdown(f"Rate: **{fmt_money(ad.get('monthly_rate'))}**")
                            st.caption(f"Ref: `{ad.get('reference', 'N/A')}`")
                        with col3:
                            st.caption(f"Schedule: {fmt_date(ad.get('start_date'))} to {fmt_date(ad.get('end_date'))}")
                            badge_color = "green" if ad.get('status') in ('paid', 'active') else "orange"
                            st.markdown(f"Status: :{badge_color}[**{str(ad.get('status')).upper()}**]")
                        with col4:
                            if st.button("Delete", key=f"{key_prefix}_del_ad_{ad['id']}", type="secondary"):
                                if sb:
                                    sb.table("ads").delete().eq("id", ad["id"]).execute()
                                    clear_cache()
                                    st.rerun()

        with tab_new_ad:
            st.markdown("##### Add Sponsored Campaign")

            checkout_url_key = f"{key_prefix}_ad_checkout_url"
            checkout_ref_key = f"{key_prefix}_ad_checkout_ref"

            if checkout_url_key not in st.session_state:
                st.session_state[checkout_url_key] = None
            if checkout_ref_key not in st.session_state:
                st.session_state[checkout_ref_key] = None

            with st.form(f"{key_prefix}_new_advert_form", clear_on_submit=False):
                f1, f2 = st.columns(2)
                with f1:
                    client_name = st.text_input("Advertiser / Business Name *", placeholder="e.g. Absa Bank", key=f"{key_prefix}_client_name")
                    advertiser_email = st.text_input("Receipt / Contact Email *", value=user_email, key=f"{key_prefix}_email")
                    ad_position = st.selectbox("Target Ad Slot *", [
                        "Login Page Sidebar Banner",
                        "Top Header Leaderboard (728x90)",
                        "Footer Promotional Bar (Full Width)",
                        "In-Feed Property Listing Sponsor"
                    ], key=f"{key_prefix}_slot")
                    start_date = st.date_input("Campaign Start Date", value=date.today(), key=f"{key_prefix}_start")

                with f2:
                    target_url = st.text_input("Destination URL *", placeholder="https://example.com", key=f"{key_prefix}_target_url")
                    creative_url = st.text_input("Banner Image URL *", placeholder="https://example.com/banner.png", key=f"{key_prefix}_creative_url")
                    pricing_rate = st.number_input(f"Monthly Slot Rate ({curr_code}) *", min_value=10.0, value=500.0, step=50.0, key=f"{key_prefix}_rate")
                    end_date = st.date_input("Campaign End Date", value=date.today() + timedelta(days=30), key=f"{key_prefix}_end")

                callback_url = st.text_input("Callback Base URL", value="https://www.rentmastergh.com", key=f"{key_prefix}_callback")

                campaign_days = (end_date - start_date).days
                daily_rate = pricing_rate / 30.0
                total_campaign_cost = daily_rate * max(1, campaign_days)

                st.info(f"📅 **Duration:** {max(1, campaign_days)} days | **Prorated Total Charge:** {fmt_money(total_campaign_cost)}")

                submit_ad = st.form_submit_button("💳 Pay Now & Launch Campaign", type="primary", use_container_width=True)

                if submit_ad:
                    if not client_name or not advertiser_email or not target_url or not creative_url:
                        st.error("Please fill in all required fields marked with *.")
                    elif end_date < start_date:
                        st.error("End date cannot be earlier than start date.")
                    else:
                        with st.spinner("Saving campaign & initializing checkout..."):
                            try:
                                ps_res, ref = initialize_ad_payment(
                                    client_name=client_name,
                                    ad_position=ad_position,
                                    amount_ghs=total_campaign_cost,
                                    start_date=str(start_date),
                                    end_date=str(end_date),
                                    destination_url=target_url,
                                    creative_url=creative_url,
                                    email=advertiser_email,
                                    callback_url=callback_url,
                                    user_id=user_id
                                )

                                if ps_res.get("status"):
                                    st.session_state[checkout_url_key] = ps_res["data"]["authorization_url"]
                                    st.session_state[checkout_ref_key] = ref
                                    clear_cache()
                                    st.success("Advert created! Click the Pay button below to complete payment.")
                                else:
                                    st.error(f"Paystack Initialization Failed: {ps_res.get('message')}")
                            except Exception as e:
                                st.error(f"Error processing advert checkout: {e}")

            if st.session_state[checkout_url_key]:
                st.markdown("---")
                st.info(f"Transaction Reference Generated: `{st.session_state[checkout_ref_key]}`")
                st.link_button(
                    "👉 Proceed to Pay Now (Card / Mobile Money)",
                    st.session_state[checkout_url_key],
                    type="primary",
                    use_container_width=True
                )
