# services/alerts.py
import urllib.parse
import streamlit as st
from datetime import date
from services.helpers import fmt_money, compute_tenant_ledger, prop_label


def compute_overdue_alerts(tenants: list, payments: list):
    """
    Scans all active tenants, calculates overdue balances, and categorizes risk levels.
    """
    alerts = []
    today = date.today()

    for t in tenants:
        if not isinstance(t, dict) or not t.get("is_active", True):
            continue

        ledger = compute_tenant_ledger(t, payments)
        balance = ledger["balance"]

        if balance > 0:
            last_payment_date = None
            if ledger["tenant_payments"]:
                last_payment_date = ledger["tenant_payments"][-1].get("payment_date")

            days_overdue = 0
            if last_payment_date:
                try:
                    p_dt = date.fromisoformat(str(last_payment_date)[:10])
                    days_overdue = (today - p_dt).days
                except Exception:
                    days_overdue = 30
            else:
                lease_start = t.get("lease_start")
                if lease_start:
                    try:
                        s_dt = date.fromisoformat(str(lease_start)[:10])
                        days_overdue = (today - s_dt).days
                    except Exception:
                        days_overdue = 30

            risk = "critical" if days_overdue >= 30 or balance >= (ledger["monthly_rent"] * 2) else "moderate"

            alerts.append({
                "tenant_id": t.get("id"),
                "tenant_name": t.get("name", "Unnamed Tenant"),
                "tenant_phone": t.get("phone", "N/A"),
                "tenant_email": t.get("email", "N/A"),
                "property_name": prop_label(t.get("properties")),
                "monthly_rent": ledger["monthly_rent"],
                "balance_due": balance,
                "days_overdue": max(0, days_overdue),
                "risk": risk
            })

    alerts.sort(key=lambda x: x["balance_due"], reverse=True)
    return alerts


def generate_reminder_message(tenant_name: str, property_name: str, amount_due: float, currency_code: str = "GHS"):
    """
    Generates a polite, professional payment reminder message.
    """
    formatted_amount = fmt_money(amount_due, currency_code)
    return (
        f"Hello {tenant_name},\n\n"
        f"This is a friendly rent payment reminder regarding your tenancy at {property_name}.\n"
        f"Our records show an outstanding balance of {formatted_amount}.\n\n"
        f"Please submit your payment online at: https://www.rentmastergh.com\n\n"
        f"Thank you for your prompt attention!\n- RentMaster Management"
    )


def render_overdue_alerts_widget(tenants: list, payments: list):
    """
    Renders the interactive Overdue Alert Banner & Reminder Center.
    """
    alerts = compute_overdue_alerts(tenants, payments)

    if not alerts:
        st.success("🎉 **All Rent Collections Up to Date!** No overdue rent balances detected.")
        return

    total_overdue = sum(a["balance_due"] for a in alerts)
    critical_count = sum(1 for a in alerts if a["risk"] == "critical")

    st.markdown(
        f"""
        <div style="background-color: #fef2f2; border: 2px solid #fca5a5; border-radius: 10px; padding: 1.2rem; margin-bottom: 1.5rem;">
            <h4 style="color: #991b1b; margin: 0 0 0.4rem 0;">⚠️ Rent Overdue Alert Engine ({len(alerts)} Tenants Pending)</h4>
            <p style="color: #7f1d1d; margin: 0; font-size: 0.95rem;">
                Total Outstanding Overdue Rent: <b>{fmt_money(total_overdue)}</b> | Critical Overdue (30+ Days): <b>{critical_count} Tenants</b>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    for a in alerts:
        badge_color = "🔴" if a["risk"] == "critical" else "🟠"
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            with c1:
                st.markdown(f"**{badge_color} {a['tenant_name']}**")
                st.caption(f"Property: {a['property_name']}")
                st.caption(f"Phone: `{a['tenant_phone']}` | Email: `{a['tenant_email']}`")
            with c2:
                st.markdown(f"Outstanding: **{fmt_money(a['balance_due'])}**")
                st.caption(f"Monthly Rent: {fmt_money(a['monthly_rent'])}")
            with c3:
                st.markdown(f"Days Overdue: **{a['days_overdue']} Days**")
                risk_label = "CRITICAL (30+ Days)" if a["risk"] == "critical" else "MODERATE"
                st.caption(f"Risk: `{risk_label}`")
            with c4:
                with st.popover("📱 Send Reminder"):
                    reminder_text = generate_reminder_message(a["tenant_name"], a["property_name"], a["balance_due"])
                    st.text_area("Pre-formatted Reminder Message", value=reminder_text, height=140)
                    if a["tenant_phone"] and a["tenant_phone"] != "N/A":
                        phone_clean = "".join(filter(str.isdigit, a["tenant_phone"]))
                        encoded_msg = urllib.parse.quote(reminder_text)
                        wa_url = f"https://wa.me/{phone_clean}?text={encoded_msg}"
                        st.link_button("📲 Send via WhatsApp", wa_url, use_container_width=True)
                    st.caption("Copy message above for SMS or Email.")
