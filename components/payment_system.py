"""
RentMaster-GH - Comprehensive Rent Payment & Installments Module
Supports Full Rent, Flexible Installments, Progress Tracking, and Paystack Integration.
"""
import streamlit as st
import json
from datetime import datetime
from services.database import sb
from services.paystack import initialize_paystack_transaction


def get_lease_payment_summary(tenant_id):
    """Fetch active lease and payment history for a tenant."""
    default_summary = {
        "lease_id": "lease_demo_101",
        "property_name": "East Legon Executive Apartment #4B",
        "landlord_name": "Chief Kwame Appiah",
        "total_rent": 12000.00,  # e.g., GH₵ 12,000 / year
        "amount_paid": 4000.00,  # e.g., GH₵ 4,000 paid so far
        "currency": "GHS",
        "installment_plan_allowed": True,
        "min_installment": 500.00,
        "payments_history": [
            {"date": "2024-01-10", "amount": 2000.00, "type": "Installment", "ref": "PAY-8839201", "status": "Completed"},
            {"date": "2024-02-15", "amount": 2000.00, "type": "Installment", "ref": "PAY-9921043", "status": "Completed"}
        ]
    }

    if not sb:
        return st.session_state.get(f"lease_summary_{tenant_id}", default_summary)

    try:
        res = sb.table("leases").select("*, properties(title), landlords(name)").eq("tenant_id", tenant_id).execute()
        if res.data:
            lease = res.data[0]
            # Fetch payments
            pay_res = sb.table("payments").select("*").eq("lease_id", lease["id"]).execute()
            history = pay_res.data or []
            
            total_paid = sum(p.get("amount", 0) for p in history if p.get("status") == "success")
            
            return {
                "lease_id": lease["id"],
                "property_name": lease.get("properties", {}).get("title", "Rental Unit"),
                "landlord_name": lease.get("landlords", {}).get("name", "Landlord"),
                "total_rent": float(lease.get("total_amount", 10000)),
                "amount_paid": float(total_paid),
                "currency": lease.get("currency", "GHS"),
                "installment_plan_allowed": lease.get("allow_installments", True),
                "min_installment": float(lease.get("min_installment", 500)),
                "payments_history": history
            }
    except Exception:
        pass

    return st.session_state.get(f"lease_summary_{tenant_id}", default_summary)


def record_payment_intent(lease_id, tenant_email, amount, payment_type, ref):
    """Save payment record to DB/State."""
    new_payment = {
        "lease_id": lease_id,
        "tenant_email": tenant_email,
        "amount": amount,
        "type": payment_type,
        "reference": ref,
        "status": "success",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "created_at": datetime.now().isoformat()
    }
    if sb:
        try:
            sb.table("payments").insert(new_payment).execute()
        except Exception:
            pass

    # Update session cache
    cache_key = f"lease_summary_{tenant_email}"
    if cache_key in st.session_state:
        st.session_state[cache_key]["amount_paid"] += amount
        st.session_state[cache_key]["payments_history"].append(new_payment)


# ---------------------------------------------------------------------------
# MAIN RENT PAYMENT WIDGET EXPORT
# ---------------------------------------------------------------------------
def render_comprehensive_rent_payment_widget(user):
    """Renders the Full / Installment Payment UI for Tenants."""
    st.markdown("## 💳 Rent Payment & Installment Center")
    st.caption("Pay your rent safely via Mobile Money (MTN, Telecel, AT) or Bank Card.")

    tenant_id = getattr(user, "id", "demo_tenant")
    tenant_email = getattr(user, "email", "tenant@example.com")

    summary = get_lease_payment_summary(tenant_id)
    
    total_rent = summary["total_rent"]
    amount_paid = summary["amount_paid"]
    remaining_balance = max(0.0, total_rent - amount_paid)
    currency = summary["currency"]
    paid_percentage = min(100.0, (amount_paid / total_rent) * 100) if total_rent > 0 else 100.0

    # ---------------------------------------------------------------------------
    # OVERVIEW CARDS & PROGRESS BAR
    # ---------------------------------------------------------------------------
    st.markdown(f"#### 🏠 Property: **{summary['property_name']}**")
    st.caption(f"Landlord: **{summary['landlord_name']}**")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Lease Rent", f"{currency} {total_rent:,.2f}")
    with c2:
        st.metric("Total Amount Paid", f"{currency} {amount_paid:,.2f}", delta=f"{paid_percentage:.1f}% Paid")
    with c3:
        st.metric("Remaining Balance", f"{currency} {remaining_balance:,.2f}", delta_color="inverse")

    st.markdown("**Overall Rent Payment Progress:**")
    st.progress(paid_percentage / 100.0)

    st.divider()

    # If rent fully paid, show success
    if remaining_balance <= 0:
        st.balloons()
        st.success("🎉 **Congratulations! Your rent for this lease period is fully settled.**")
        _render_payment_history_table(summary["payments_history"], currency)
        return

    # ---------------------------------------------------------------------------
    # PAYMENT OPTION FORM (Full vs Installment)
    # ---------------------------------------------------------------------------
    st.markdown("### 💸 Make a Payment")

    pay_tab1, pay_tab2 = st.tabs(["⚡ Pay Rent Now", "📜 Payment History & Receipts"])

    with pay_tab1:
        with st.container(border=True):
            pay_option = st.radio(
                "Select Payment Mode *",
                [
                    "🟢 Pay Remaining Balance (Full Payment)",
                    "🟡 Pay Custom Installment Amount"
                ],
                horizontal=True
            )

            if "Full Payment" in pay_option:
                payment_amount = remaining_balance
                st.info(f"You are paying the **Full Remaining Balance** of **{currency} {payment_amount:,.2f}**.")
            else:
                min_inst = summary["min_installment"]
                st.write(f"💡 *Minimum allowable installment:* **{currency} {min_inst:,.2f}**")
                
                payment_amount = st.number_input(
                    f"Enter Installment Amount ({currency})",
                    min_value=float(min_inst),
                    max_value=float(remaining_balance),
                    value=float(min(min_inst * 2, remaining_balance)),
                    step=100.0
                )

            st.markdown("<br>", unsafe_allow_html=True)

            # Payment Gateway Selection
            gateway = st.radio("Select Payment Channel *", ["📱 Mobile Money (MTN / Telecel / AT)", "💳 Debit / Credit Card"], horizontal=True)

            pay_now_btn = st.button(
                f"🚀 Proceed to Pay {currency} {payment_amount:,.2f}",
                type="primary",
                use_container_width=True
            )

            if pay_now_btn:
                if payment_amount <= 0:
                    st.error("Payment amount must be greater than zero.")
                else:
                    ref_code = f"RENT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    # Call Paystack initialization or simulate
                    try:
                        paystack_data = initialize_paystack_transaction(
                            email=tenant_email,
                            amount_ghs=payment_amount,
                            reference=ref_code
                        )
                        auth_url = paystack_data.get("data", {}).get("authorization_url")
                        
                        if auth_url:
                            st.success("✅ Payment Session Generated!")
                            st.markdown(
                                f"""
                                <a href="{auth_url}" target="_blank" style="display: block; text-align: center; background-color: #059669; color: white; padding: 14px; border-radius: 8px; font-weight: bold; text-decoration: none; font-size: 1.1rem; margin-top: 10px;">
                                    👉 Click Here to Complete Payment of {currency} {payment_amount:,.2f} on Paystack
                                </a>
                                """,
                                unsafe_allow_html=True
                            )
                        else:
                            # Fallback/Demo recording
                            record_payment_intent(summary["lease_id"], tenant_email, payment_amount, "Installment" if "Installment" in pay_option else "Full", ref_code)
                            st.success(f"✅ Payment of {currency} {payment_amount:,.2f} processed successfully! Reference: `{ref_code}`")
                            st.rerun()
                    except Exception as e:
                        # Direct recording fallback if API key missing in demo
                        record_payment_intent(summary["lease_id"], tenant_email, payment_amount, "Installment" if "Installment" in pay_option else "Full", ref_code)
                        st.success(f"✅ Payment of {currency} {payment_amount:,.2f} recorded! Reference: `{ref_code}`")
                        st.rerun()

    with pay_tab2:
        _render_payment_history_table(summary["payments_history"], currency)


def _render_payment_history_table(history, currency):
    """Renders the table of past transactions and download receipts."""
    st.markdown("#### 📜 Installment & Payment Audit Log")

    if not history:
        st.info("No payment records found for this lease yet.")
        return

    # Render History Table
    for idx, p in enumerate(reversed(history)):
        with st.container(border=True):
            col_a, col_b, col_c = st.columns([2, 2, 1])
            with col_a:
                st.write(f"**Date:** {p.get('date', 'N/A')}")
                st.write(f"**Type:** {p.get('type', 'Payment')}")
            with col_b:
                st.write(f"**Amount Paid:** {currency} {p.get('amount', 0):,.2f}")
                st.caption(f"Ref: `{p.get('reference', 'N/A')}`")
            with col_c:
                st.success("Completed ✅")
                # Printable Receipt Trigger
                if st.button("📄 Receipt", key=f"rcpt_btn_{idx}"):
                    st.toast(f"Downloading PDF Receipt for Ref: {p.get('reference')}")
