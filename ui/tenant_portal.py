# ui/tenant_portal.py
import streamlit as st
from services.helpers import fmt_money, fmt_date, compute_tenant_ledger, prop_label, get_active_user_info
from services.database import sb, fetch_tenant_profile_by_email, fetch_payments, fetch_maintenance, clear_cache, upload_id_to_supabase
from services.pdf_generator import generate_receipt_pdf
from components.chat import render_chat_interface
from components.verification import render_id_verification_widget
from components.payment_system import render_comprehensive_rent_payment_widget
from ui.pages_core import header


def render_tenant_portal():
    header()
    st.subheader("🏠 Tenant Self-Service Portal")

    user_id, user_email = get_active_user_info()
    user = st.session_state.get("user")
    tenant = fetch_tenant_profile_by_email(user_email)

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
        # 1. RENT & INSTALLMENT PAYMENT WIDGET
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
                    st.er
