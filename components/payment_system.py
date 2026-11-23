"""
RentMaster-GH - Comprehensive Rent Payment & Installments Module
Supports Full Rent, Flexible Installments, Progress Tracking, Paystack Split Payouts,
and Sequential Verification Gating (Manager KYC -> Landlord 2-Day Acceptance -> Agreement -> Condition).
"""
from urllib.parse import quote
import streamlit as st
from datetime import datetime
from services.database import sb, fetch_tenant_profile_by_email
from components.verification import check_tenant_kyc_payment_eligibility
from components.property_condition import render_tenant_condition_approval_widget
from components.agreements import render_tenant_agreement_acceptance_widget

_paystack_func = None

try:
    from services.paystack import initialize_paystack_payment as _paystack_func
except ImportError:
    try:
        from services.paystack import initialize_paystack_transaction as _paystack_func
    except ImportError:
        _paystack_func = None


def safe_initialize_paystack(email, amount_ghs, reference, callback_url="https://rentmastergh.com", metadata=None):
    """Safe wrapper function to handle parameter differences across Paystack helpers."""
    if not _paystack_func:
        return {"status": False, "message": "Paystack service unavailable."}

    try:
        return _paystack_func(
            email=email,
            amount_in_main_unit=amount_ghs,
            callback_url=callback_url,
            metadata=metadata or {"reference": reference}
        )
    except TypeError:
        try:
            return _paystack_func(
                email=email,
                amount_ghs=amount_ghs,
                reference=reference,
                callback_url=callback_url
            )
        except Exception as e:
            return {"status": False, "message": str(e)}


def get_lease_payment_summary(tenant_id):
    """Fetch active lease and payment history for a tenant (counting both 'paid' and 'success')."""
    default_summary = {
        "lease_id": "lease_demo_101",
        "property_name": "East Legon Executive Apartment #4B",
        "landlord_name": "Chief Kwame Appiah",
        "total_rent": 12000.00,
        "amount_paid": 4000.00,
        "currency": "GHS",
        "installment_plan_allowed": True,
        "min_installment": 500.00,
        "payments_history": [
            {"date": "2024-01-10", "amount": 2000.00, "type": "Installment", "ref": "PAY-8839201", "status": "paid"},
            {"date": "2024-02-15", "amount": 2000.00, "type": "Installment", "ref": "PAY-9921043", "status": "paid"}
        ]
    }

    if not sb:
        return st.session_state.get(f"lease_summary_{tenant_id}", default_summary)

    try:
        res = sb.table("leases").select("*, properties(title), landlords(name)").eq("tenant_id", tenant_id).execute()
        if res.data:
            lease = res.data[0]
            pay_res = sb.table("payments").select("*").eq("lease_id", lease["id"]).execute()
            history = pay_res.data or []
            total_paid = sum(
                float(p.get("amount", 0) or 0)
                for p in history
                if str(p.get("status", "")).lower() in ("paid", "success", "completed")
            )
            return {
                "lease_id": lease["id"],
                "property_name": (lease.get("properties") or {}).get("title", "Rental Unit"),
                "landlord_name": (lease.get("landlords") or {}).get("name", "Landlord"),
                "total_rent": float(lease.get("total_amount", 10000) or 10000),
                "amount_paid": float(total_paid),
                "currency": lease.get("currency", "GHS"),
                "installment_plan_allowed": lease.get("allow_installments", True),
                "min_installment": float(lease.get("min_installment", 500) or 500),
                "payments_history": history
            }
    except Exception:
        pass

    return st.session_state.get(f"lease_summary_{tenant_id}", default_summary)


def render_comprehensive_rent_payment_widget(user):
    """Renders the Full / Installment Payment UI for Tenants."""
    tenant_id = getattr(user, "id", "demo_tenant")
    tenant_email = getattr(user, "email", "tenant@example.com")

    tenant_record = None
    if sb and tenant_email:
        try:
            tenant_record = fetch_tenant_profile_by_email(tenant_email)
        except Exception:
            pass

    kyc_eligible, kyc_reason = check_tenant_kyc_payment_eligibility(tenant_record)
    if not kyc_eligible:
        st.warning(f"🔒 **Rent Payment Locked:** {kyc_reason}")
        st.info("Both **App Manager KYC Verification** and **Landlord Acceptance (within 2-day window)** are required before payments can be initialized.")
        return

    agreement_approved = render_tenant_agreement_acceptance_widget(user)
    st.divider()
    if not agreement_approved:
        st.info("🔒 **Rent Payments Locked:** Please review and accept the Tenancy Agreement above to unlock payments.")
        return

    condition_approved = render_tenant_condition_approval_widget(user)
    st.divider()
    if not condition_approved:
        st.info("🔒 **Rent Payments Locked:** Please inspect and accept the property condition photos above to unlock the payment checkout form.")
        return

    st.markdown("## 💳 Rent Payment & Installment Center")
    st.caption("Pay your rent safely via Mobile Money (MTN, Telecel, AT) or Bank Card.")

    summary = get_lease_payment_summary(tenant_id)
    total_rent = summary["total_rent"]
    amount_paid = summary["amount_paid"]
    remaining_balance = max(0.0, total_rent - amount_paid)
    currency = summary["currency"]
    paid_percentage = min(100.0, (amount_paid / total_rent) * 100) if total_rent > 0 else 100.0

    st.markdown(f"#### 🏠 Property: **{summary['property_name']}**")
    st.caption(f"Landlord: **{summary['landlord_name']}**")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Lease Rent", f"{currency} {total_rent:,.2f}")
    c2.metric("Total Amount Paid", f"{currency} {amount_paid:,.2f}", delta=f"{paid_percentage:.1f}% Paid")
    c3.metric("Remaining Balance", f"{currency} {remaining_balance:,.2f}", delta_color="inverse")

    st.markdown("**Overall Rent Payment Progress:**")
    st.progress(paid_percentage / 100.0)
    st.divider()

    if remaining_balance <= 0:
        st.balloons()
        st.success("🎉 **Congratulations! Your rent for this lease period is fully settled.**")
        _render_payment_history_table(summary["payments_history"], currency, summary["property_name"], tenant_email)
        return

    st.markdown("### 💸 Make a Payment")
    pay_tab1, pay_tab2 = st.tabs(["⚡ Pay Rent Now", "📜 Payment History & Receipts"])

    with pay_tab1:
        with st.container(border=True):
            pay_option = st.radio(
                "Select Payment Mode *",
                ["🟢 Pay Remaining Balance (Full Payment)", "🟡 Pay Custom Installment Amount"],
                horizontal=True
            )

            if "Full Payment" in pay_option:
                payment_amount = remaining_balance
                st.info(f"You are paying the **Full Remaining Balance** of **{currency} {payment_amount:,.2f}**.")
            else:
                min_inst = min(summary["min_installment"], remaining_balance)
                st.write(f"💡 *Minimum allowable installment:* **{currency} {min_inst:,.2f}**")
                payment_amount = st.number_input(
                    f"Enter Installment Amount ({currency})",
                    min_value=float(min_inst),
                    max_value=float(remaining_balance),
                    value=float(min(min_inst * 2, remaining_balance)),
                    step=100.0
                )

            st.radio("Select Payment Channel *", ["📱 Mobile Money (MTN / Telecel / AT)", "💳 Debit / Credit Card"], horizontal=True)

            if st.button(f"🚀 Proceed to Pay {currency} {payment_amount:,.2f}", type="primary", use_container_width=True):
                if payment_amount <= 0:
                    st.error("Payment amount must be greater than zero.")
                else:
                    ref_code = f"RENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    paystack_data = safe_initialize_paystack(
                        email=tenant_email,
                        amount_ghs=payment_amount,
                        reference=ref_code,
                        metadata={
                            "tenant_id": tenant_id,
                            "lease_id": summary["lease_id"],
                            "payment_type": "Installment" if "Installment" in pay_option else "Full",
                            "reference": ref_code,
                        }
                    )

                    auth_url = None
                    if paystack_data and isinstance(paystack_data, dict):
                        auth_url = (paystack_data.get("data") or {}).get("authorization_url") or paystack_data.get("authorization_url")

                    if auth_url:
                        st.success("✅ Paystack Checkout Ready! Complete payment below—your receipt will verify automatically upon return.")
                        st.link_button(
                            f"👉 Complete Payment of {currency} {payment_amount:,.2f} on Paystack",
                            auth_url,
                            type="primary",
                            use_container_width=True
                        )
                    else:
                        err_msg = (paystack_data or {}).get("message", "Could not initialize Paystack session. Check PAYSTACK_SECRET_KEY.")
                        st.error(f"❌ Paystack Checkout Unavailable: {err_msg}")

    with pay_tab2:
        _render_payment_history_table(summary["payments_history"], currency, summary["property_name"], tenant_email)


def _render_payment_history_table(history, currency, property_name="Rental Unit", tenant_email=""):
    """Renders past transactions with real downloadable text receipts and WhatsApp sharing."""
    st.markdown("#### 📜 Installment & Payment Audit Log")

    if not history:
        st.info("No payment records found for this lease yet.")
        return

    for idx, p in enumerate(reversed(history)):
        ref_id = p.get("reference") or p.get("ref") or f"PAY-{idx+1}"
        amt = float(p.get("amount", 0) or 0)
        p_date = p.get("payment_date") or p.get("date") or "N/A"
        p_type = p.get("payment_method") or p.get("type") or "Rent Payment"

        receipt_txt = (
            "========================================\n"
            "      RENTMASTER-GH OFFICIAL RECEIPT    \n"
            "========================================\n"
            f"Reference:   {ref_id}\n"
            f"Date:        {p_date}\n"
            f"Property:    {property_name}\n"
            f"Tenant:      {tenant_email}\n"
            f"Channel:     {p_type}\n"
            f"Amount Paid: {currency} {amt:,.2f}\n"
            "Status:      VERIFIED & PAID\n"
            "Verify URL:  https://rentmastergh.com\n"
            "========================================\n"
        )
        wa_msg = quote(
            f"✅ RentMaster-GH Official Receipt\n"
            f"• Property: {property_name}\n"
            f"• Amount: {currency} {amt:,.2f}\n"
            f"• Ref: {ref_id}\n"
            f"• Date: {p_date}\n"
            f"• Portal: https://rentmastergh.com"
        )

        with st.container(border=True):
            col_a, col_b, col_c = st.columns([2, 2, 1.4])
            with col_a:
                st.write(f"**Date:** {p_date}")
                st.write(f"**Channel:** {p_type}")
            with col_b:
                st.write(f"**Amount Paid:** {currency} {amt:,.2f}")
                st.caption(f"Ref: `{ref_id}`")
            with col_c:
                st.download_button(
                    "📄 Download Receipt",
                    data=receipt_txt.encode("utf-8"),
                    file_name=f"RentMaster_Receipt_{ref_id}.txt",
                    mime="text/plain",
                    key=f"dl_rcpt_{idx}_{ref_id}",
                    use_container_width=True
                )
                st.link_button("💬 WhatsApp", f"https://wa.me{wa_msg}", use_container_width=True)
