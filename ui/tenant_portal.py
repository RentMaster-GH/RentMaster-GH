# ui/tenant_portal.py
import streamlit as st
from services.helpers import fmt_money, fmt_date, compute_tenant_ledger, prop_label, get_active_user_info, get_current_currency
from services.database import sb, fetch_tenant_profile_by_email, fetch_payments, fetch_maintenance, clear_cache
from services.paystack import initialize_paystack_payment
from services.pdf_generator import generate_receipt_pdf
from components.chat import render_chat_interface
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
    curr_code = st.session_state.get("app_currency", "GHS")

    # Maintenance Hold / Security Reserve Amount
    maint_hold = float(tenant.get("maintenance_hold") or tenant.get("deposit_amount") or prop_obj.get("deposit_amount") or 0.0)

    # TENANT FINANCIAL TRANSPARENCY OVERVIEW CARD
    with st.container(border=True):
        st.markdown(f"### Welcome back, **{tenant.get('name')}** 👋")
        st.caption(f"📍 Property: **{prop_label(prop_obj)}** | Lease: {fmt_date(tenant.get('lease_start'))} to {fmt_date(tenant.get('lease_end'))}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Agreed Monthly Rent", fmt_money(ledger["monthly_rent"], curr_code))
        
        # CLEARLY DISPLAY MAINTENANCE HOLD / SECURITY RESERVE
        m2.metric("🛡️ Maintenance Hold / Reserve", fmt_money(maint_hold, curr_code), help="Security deposit or maintenance reserve held by landlord for repairs and unit upkeep.")
        
        m3.metric("Total Rent Paid to Date", fmt_money(ledger["total_paid"], curr_code))
        
        bal_color = "red" if ledger["balance"] > 0 else "green"
        bal_label = "Outstanding Balance Due" if ledger["balance"] > 0 else "Account Up to Date"
        m4.metric("Ledger Balance", fmt_money(abs(ledger["balance"]), curr_code), delta=f":{bal_color}[{bal_label}]")

    st.markdown("<br>", unsafe_allow_html=True)

    # PORTAL TABS
    tab_pay, tab_docs, tab_maint, tab_chat = st.tabs([
        "💳 Rent & Installment Payment Portal",
        "📋 Official Rent Documents & Rent Card",
        "🛠️ Repair & Maintenance Requests",
        "💬 Chat & Video Call Landlord"
    ])

    # -----------------------------------------------------------------------
    # TAB 1: COMPREHENSIVE RENT & INSTALLMENT PAYMENT PORTAL
    # -----------------------------------------------------------------------
    with tab_pay:
        st.markdown("#### 💳 Comprehensive Rent & Installment Checkout")
        
        # Maintenance Hold Transparency Box
        st.markdown(
            f"""
            <div style="background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 10px; padding: 1rem; margin-bottom: 1.2rem;">
                <h6 style="color: #0369a1; margin: 0 0 0.3rem 0; font-weight: 700;">🛡️ Maintenance Reserve & Rent Disclosure</h6>
                <p style="color: #0c4a6e; margin: 0; font-size: 0.88rem;">
                    • <b>Maintenance Hold Amount:</b> {fmt_money(maint_hold, curr_code)}<br/>
                    • <b>Current Outstanding Due:</b> {fmt_money(ledger['balance'], curr_code)}<br/>
                    • You may pay the full balance, standard monthly rent, or pay in <b>flexible installments</b>.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        subaccount_code = landlord_obj.get("paystack_subaccount_code") if isinstance(landlord_obj, dict) else None
        landlord_name = landlord_obj.get("name", "Property Landlord") if isinstance(landlord_obj, dict) else "Property Landlord"

        if subaccount_code:
            st.info(f"⚡ **Direct Landlord Payout:** Your payment will be deposited directly to Landlord **{landlord_name}** (`{subaccount_code}`).")

        # INSTALLMENT PAYMENT FORM
        with st.form("tenant_installment_checkout_form"):
            st.markdown("##### Select Payment Type / Option")
            
            pay_mode = st.radio(
                "Choose How Much to Pay Today",
                [
                    f"Full Outstanding Balance ({fmt_money(max(0, ledger['balance']), curr_code)})",
                    f"Standard 1-Month Rent ({fmt_money(ledger['monthly_rent'], curr_code)})",
                    "Custom Installment / Partial Payment"
                ],
                key="tenant_pay_mode_radio"
            )

            if "Full Outstanding" in pay_mode:
                calc_pay_amt = max(1.0, float(ledger["balance"]))
            elif "Standard 1-Month" in pay_mode:
                calc_pay_amt = max(1.0, float(ledger["monthly_rent"]))
            else:
                calc_pay_amt = 100.0

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                final_pay_amount = st.number_input(
                    f"Payment Amount ({curr_code}) *",
                    min_value=1.0,
                    value=float(calc_pay_amt),
                    step=50.0,
                    help="Enter your custom installment amount or keep the selected preset."
                )
            with col_p2:
                receipt_email = st.text_input("Receipt Email *", value=user_email)

            callback_url = st.text_input("Callback URL", value="https://www.rentmastergh.com")

            # Checkout Summary Pill
            st.markdown(
                f"""
                <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.8rem; margin-top: 0.5rem; margin-bottom: 0.8rem;">
                    <b>Checkout Summary:</b> Paying <b>{fmt_money(final_pay_amount, curr_code)}</b> &middot; Maintenance Hold Reference: {fmt_money(maint_hold, curr_code)}
                </div>
                """,
                unsafe_allow_html=True
            )

            submit_checkout = st.form_submit_button("💳 Pay Rent Now (Card / Mobile Money / Bank)", type="primary", use_container_width=True)

            if submit_checkout:
                if not receipt_email:
                    st.error("Please enter a valid email address for receipt delivery.")
                else:
                    with st.spinner("Initializing secure Paystack checkout..."):
                        res = initialize_paystack_payment(
                            email=receipt_email,
                            amount_in_main_unit=final_pay_amount,
                            callback_url=callback_url,
                            metadata={
                                "type": "rent_installment_payment",
                                "tenant_id": tenant.get("id"),
                                "tenant_name": tenant.get("name"),
                                "user_id": user_id,
                                "maintenance_hold": maint_hold
                            },
                            subaccount=subaccount_code,
                            currency=curr_code
                        )

                        if res.get("status"):
                            st.success("✅ Payment link generated! Click the button below to complete checkout.")
                            st.link_button(
                                "👉 Proceed to Paystack Checkout (Card / Mobile Money)",
                                res["data"]["authorization_url"],
                                type="primary",
                                use_container_width=True
                            )
                        else:
                            st.error(f"Payment initialization failed: {res.get('message')}")

        st.markdown("---")
        st.markdown("#### 📋 Itemized Rent Ledger & PDF Receipts")
        
        tenant_payments = ledger.get("tenant_payments", [])
        if tenant_payments:
            st.markdown("##### Recent Verified Payments & Downloadable PDF Receipts")
            for p in tenant_payments:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                    c1.markdown(f"**Rent Payment ({fmt_money(p.get('amount'), curr_code)})**")
                    c1.caption(f"Ref: `{p.get('notes', 'N/A')}`")
                    c2.markdown(f"Date: **{fmt_date(p.get('payment_date'))}**")
                    c3.markdown(f"Method: **{str(p.get('payment_method', 'Paystack')).replace('_', ' ').title()}**")
                    with c4:
                        try:
                            pdf_bytes = generate_receipt_pdf(tenant, p, prop_obj)
                            st.download_button(
                                "📄 PDF Receipt",
                                data=pdf_bytes,
                                file_name=f"RentReceipt_{fmt_date(p.get('payment_date'))}_{p.get('id')[:6]}.pdf",
                                mime="application/pdf",
                                key=f"tenant_rec_btn_{p['id']}"
                            )
                        except Exception:
                            st.caption("PDF N/A")

        st.markdown("---")
        st.markdown("##### Full Ledger Statement History")
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

    # -----------------------------------------------------------------------
    # TAB 2: DOCUMENTS & GHANA RENT CARD
    # -----------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # TAB 3: MAINTENANCE REQUESTS
    # -----------------------------------------------------------------------
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
        st.markdown("##### Your Active Maintenance Tickets")
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

    # -----------------------------------------------------------------------
    # TAB 4: CHAT & VIDEO CALL LANDLORD
    # -----------------------------------------------------------------------
    with tab_chat:
        landlord_name = landlord_obj.get("name", "Landlord") if isinstance(landlord_obj, dict) else "Landlord"
        render_chat_interface(
            tenant_id=tenant.get("id"),
            current_user_id=user_id,
            current_user_role="tenant",
            current_user_email=user_email,
            recipient_name=landlord_name
        )
