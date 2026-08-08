# ui/tenant_portal.py
import streamlit as st
from datetime import datetime, timedelta
from services.helpers import fmt_money, fmt_date, compute_tenant_ledger, prop_label, get_active_user_info
from services.database import sb, fetch_tenant_profile_by_email, fetch_payments, fetch_maintenance, clear_cache, upload_id_to_supabase
from services.pdf_generator import generate_receipt_pdf
from components.chat import render_chat_interface
from components.verification import render_id_verification_widget
from components.payment_system import render_comprehensive_rent_payment_widget
from components.tenancy_lifecycle import render_tenant_lease_lifecycle_widget
from ui.pages_core import header


def render_tenant_portal():
    header()
    st.subheader("🏠 Tenant Self-Service Portal")

    user_id, user_email = get_active_user_info()
    user = st.session_state.get("user")
    tenant = fetch_tenant_profile_by_email(user_email)

    # 1. 90-DAY RENEWAL / TERMINATION REQUEST & 3-MONTH GRACE PERIOD TRACKER
    if tenant and tenant.get("leases"):
        lease_data = tenant["leases"][0] if isinstance(tenant["leases"], list) else tenant["leases"]
        render_tenant_lease_lifecycle_widget(user, lease_data)
        st.divider()
    elif tenant:
        # Construct fallback lease details from tenant record
        fallback_lease = {
            "id": f"lease_{tenant.get('id', '101')}",
            "end_date": str(tenant.get("lease_end") or (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")),
            "tenant_intent": tenant.get("tenant_intent"),
            "landlord_intent_decision": tenant.get("landlord_intent_decision"),
            "tenant_intent_requested_at": tenant.get("tenant_intent_requested_at")
        }
        render_tenant_lease_lifecycle_widget(user, fallback_lease)
        st.divider()

    # UNIFIED PORTAL TABS (Always visible)
    tab_pay, tab_docs, tab_maint, tab_chat, tab_kyc = st.tabs([
        "💳 Rent & Installment Payment Portal",
        "📋 Official Rent Documents & Rent Card",
        "🛠️ Repair & Maintenance Requests",
        "💬 Chat & Video Call Landlord",
        "🆔 Verification & Mutual Agreement"
    ])

    # -----------------------------------------------------------------------
    # TAB 1: COMPREHENSIVE RENT & INSTALLMENT PAYMENT PORTAL (ALWAYS VISIBLE)
    # -----------------------------------------------------------------------
    with tab_pay:
        # RENT & INSTALLMENT PAYMENT WIDGET
        render_comprehensive_rent_payment_widget(user)

        st.markdown("---")
        st.markdown("#### 📋 Itemized Rent Ledger & PDF Receipts")
        
        if tenant:
            all_payments = fetch_payments(user_id, user_email)
            ledger = compute_tenant_ledger(tenant, all_payments)
            curr_code = st.session_state.get("app_currency", "GHS")
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
                                prop_obj = tenant.get("properties") or {}
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
            else:
                st.info("No completed payments logged under this account yet.")
        else:
            st.info("ℹ️ Once your landlord links your email address (`" + str(user_email) + "`) to your property lease, your official ledger history will automatically appear here.")

    # -----------------------------------------------------------------------
    # TAB 2: DOCUMENTS & GHANA RENT CARD
    # -----------------------------------------------------------------------
    with tab_docs:
        st.markdown("#### 📋 Official Rent Documents")
        if tenant and tenant.get("rent_card_url"):
            st.success("✅ **Official Ghana Rent Card Issued:** Your landlord has published your official Rent Card.")
            st.link_button("📥 View / Download Official Ghana Rent Card", tenant["rent_card_url"], type="primary")
        else:
            st.info("ℹ️ No Ghana Rent Card published yet by your landlord.")

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
                        prop_obj = (tenant.get("properties") or {}) if tenant else {}
                        sb.table("maintenance_requests").insert({
                            "property_id": prop_obj.get("id"),
                            "tenant_id": tenant.get("id") if tenant else None,
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

    # -----------------------------------------------------------------------
    # TAB 4: CHAT & VIDEO CALL LANDLORD
    # -----------------------------------------------------------------------
    with tab_chat:
        landlord_obj = (tenant.get("properties") or {}).get("landlords") if tenant and isinstance(tenant.get("properties"), dict) else {}
        landlord_name = landlord_obj.get("name", "Landlord") if isinstance(landlord_obj, dict) else "Landlord"
        
        render_chat_interface(
            tenant_id=tenant.get("id") if tenant else "demo_tenant",
            current_user_id=user_id,
            current_user_role="tenant",
            current_user_email=user_email,
            recipient_name=landlord_name
        )

    # -----------------------------------------------------------------------
    # TAB 5: TENANT VERIFICATION PORTAL & MUTUAL LANDLORD ACCEPTANCE
    # -----------------------------------------------------------------------
    with tab_kyc:
        render_id_verification_widget(user, role="tenant")
