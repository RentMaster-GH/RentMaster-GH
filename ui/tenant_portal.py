# ui/tenant_portal.py
import streamlit as st
from services.helpers import fmt_money, fmt_date, compute_tenant_ledger, prop_label, get_active_user_info
from services.database import sb, fetch_tenant_profile_by_email, fetch_payments, fetch_maintenance, clear_cache
from services.paystack import initialize_paystack_payment
from ui.pages_core import header


def render_tenant_portal():
    header()
    st.subheader("🏠 Tenant Self-Service Portal")

    user_id, user_email = get_active_user_info()
    tenant = fetch_tenant_profile_by_email(user_email)

    if not tenant:
        st.warning(f"⚠️ **Tenant Profile Unlinked:** Your account email (`{user_email}`) is not currently linked to an active tenant record.")
        st.info("Please ask your property manager or landlord to assign your email address (`" + str(user_email) + "`) to your tenant profile.")
        return

    prop_obj = tenant.get("properties") or {}
    landlord_obj = prop_obj.get("landlords") if isinstance(prop_obj, dict) else {}
    all_payments = fetch_payments(user_id, user_email)

    # Compute tenant ledger
    ledger = compute_tenant_ledger(tenant, all_payments)

    # Tenant Overview Card
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"**Welcome, {tenant.get('name')}**")
            st.caption(f"Property: {prop_label(prop_obj)}")
        with col2:
            st.metric("Agreed Monthly Rent", fmt_money(ledger["monthly_rent"]))
        with col3:
            st.metric("Lease Period", f"{fmt_date(tenant.get('lease_start'))} to {fmt_date(tenant.get('lease_end'))}")
        with col4:
            bal_color = "red" if ledger["balance"] > 0 else "green"
            bal_label = "Outstanding Due" if ledger["balance"] > 0 else "Up to Date"
            st.metric("Ledger Balance", fmt_money(abs(ledger["balance"])), delta=f":{bal_color}[{bal_label}]")

    # Portal Tabs
    tab_pay, tab_docs, tab_maint = st.tabs([
        "💳 Rent Ledger & Pay Online",
        "📋 Official Rent Documents & Rent Card",
        "🛠️ Repair & Maintenance Requests"
    ])

    # TAB 1: RENT LEDGER & ONLINE CHECKOUT
    with tab_pay:
        st.markdown("#### 💳 Online Rent Checkout (Card / Mobile Money)")
        curr_code = st.session_state.get("app_currency", "GHS")
        subaccount_code = landlord_obj.get("paystack_subaccount_code") if isinstance(landlord_obj, dict) else None

        with st.form("tenant_checkout_form"):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                default_pay_amt = max(ledger["balance"], ledger["monthly_rent"])
                pay_amt = st.number_input(f"Payment Amount ({curr_code}) *", min_value=1.0, value=float(default_pay_amt) if default_pay_amt > 0 else 100.0, step=50.0)
            with col_c2:
                receipt_email = st.text_input("Receipt Email *", value=user_email)

            callback_url = st.text_input("Callback URL", value="https://www.rentmastergh.com")

            if st.form_submit_button("💳 Proceed to Pay Rent", type="primary", use_container_width=True):
                res = initialize_paystack_payment(
                    email=receipt_email,
                    amount_in_main_unit=pay_amt,
                    callback_url=callback_url,
                    metadata={
                        "type": "rent_payment",
                        "tenant_id": tenant.get("id"),
                        "tenant_name": tenant.get("name"),
                        "user_id": user_id
                    },
                    subaccount=subaccount_code,
                    currency=curr_code
                )

                if res.get("status"):
                    st.success("Checkout initialized!")
                    st.link_button("👉 Click Here to Pay Now (Mobile Money / Card)", res["data"]["authorization_url"], type="primary", use_container_width=True)
                else:
                    st.error(f"Payment initialization failed: {res.get('message')}")

        st.markdown("---")
        st.markdown("#### 📋 Itemized Rent Ledger Statement")
        if ledger["statement"]:
            formatted_statement = []
            for idx, row in enumerate(ledger["statement"], 1):
                formatted_statement.append({
                    "#": idx,
                    "Date": row["date"],
                    "Type": row["type"],
                    "Description": row["description"],
                    f"Charge ({curr_code})": f"{row['charge']:,.2f}" if row['charge'] > 0 else "-",
                    f"Credit ({curr_code})": f"{row['credit']:,.2f}" if row['credit'] > 0 else "-",
                    f"Balance ({curr_code})": f"{row['balance']:,.2f}",
                    "Reference": row["ref"]
                })
            st.dataframe(formatted_statement, use_container_width=True, hide_index=True)
        else:
            st.info("No transaction history recorded on your ledger yet.")

    # TAB 2: DOCUMENTS & GHANA RENT CARD
    with tab_docs:
        st.markdown("#### 📋 Official Rent Documents")
        if tenant.get("rent_card_url"):
            st.success("✅ **Official Ghana Rent Card Issued:** Your landlord has published your official Rent Card.")
            st.link_button("📥 View / Download Official Ghana Rent Card", tenant["rent_card_url"], type="primary")
        else:
            st.info("ℹ️ No Ghana Rent Card published yet by your landlord.")

        if tenant.get("id_card_url"):
            st.markdown("---")
            st.markdown(f"🆔 [View Verified Tenant ID Document]({tenant['id_card_url']})")

    # TAB 3: MAINTENANCE REQUESTS
    with tab_maint:
        st.markdown("#### 🛠️ Request Repairs or Maintenance")
        with st.form("tenant_maint_form", clear_on_submit=True):
            m_title = st.text_input("Issue Title *", placeholder="e.g. Leaking bathroom pipe")
            m_priority = st.selectbox("Urgency Level", ["low", "medium", "high", "urgent"])
            m_desc = st.text_area("Detailed Description *", placeholder="Describe the maintenance issue...")

            if st.form_submit_button("Submit Maintenance Request", type="primary"):
                if not m_title or not m_desc:
                    st.error("Please fill in title and description.")
                elif sb:
                    try:
                        sb.table("maintenance_requests").insert({
                            "property_id": prop_obj.get("id"),
                            "tenant_id": tenant.get("id"),
                            "title": m_title,
                            "description": m_desc,
                            "priority": m_priority,
                            "status": "open",
                            "user_id": user_id,
                            "user_email": user_email
                        }).execute()
                        clear_cache()
                        st.success("✅ Maintenance request submitted to landlord!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to submit request: {e}")

        st.markdown("---")
        st.markdown("##### Your Maintenance Requests")
        maint_list = fetch_maintenance(user_id, user_email)
        tenant_maint = [m for m in maint_list if isinstance(m, dict) and m.get("tenant_id") == tenant.get("id")]

        if tenant_maint:
            for m in tenant_maint:
                with st.container(border=True):
                    st.markdown(f"**{m.get('title')}** — Priority: `{m.get('priority', 'medium').upper()}`")
                    st.caption(f"Status: **{m.get('status', 'open').upper()}** | Filed: {fmt_date(m.get('created_at'))}")
                    if m.get("description"):
                        st.write(m["description"])
        else:
            st.info("No active maintenance requests filed for your unit.")
