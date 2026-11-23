"""
RentMaster-GH - Property Expense & Net Income Financial Engine
Tracks Property Expenses, Cash Flow, Net Profit Margin, Receipt Attachments, and CSV/JSON P&L Statements.
"""
import base64
import csv
import io
import json
import streamlit as st
from datetime import datetime, date
from services.database import sb, fetch_properties, fetch_payments

EXPENSE_CATEGORIES = [
    "🛠️ Maintenance & Repairs",
    "💡 Utilities (Water/Electricity)",
    "🤝 Agent & Management Fees",
    "🏛️ Property Taxes & Legal Fees",
    "🛡️ Property Insurance",
    "📦 Miscellaneous / Other",
]


def fetch_property_expenses(user_id, user_email):
    """Fetch logged property expenses scoped strictly to the active landlord."""
    default_expenses = [
        {"id": "exp_101", "property_name": "East Legon Executive Apartment #4B", "category": "🛠️ Maintenance & Repairs", "amount": 800.00, "date": "2024-01-15", "description": "AC Servicing & Gas Refill"},
        {"id": "exp_102", "property_name": "East Legon Executive Apartment #4B", "category": "💡 Utilities (Water/Electricity)", "amount": 350.00, "date": "2024-02-01", "description": "ECG Meter Bill Payment"},
    ]

    if not sb:
        return st.session_state.get("property_expenses_list", default_expenses)

    try:
        q = sb.table("expenses").select("*, properties(name)")
        if user_id:
            q = q.eq("user_id", user_id)
        elif user_email:
            q = q.eq("user_email", user_email)
        res = q.order("created_at", desc=True).execute()
        if res.data is not None:
            return res.data
    except Exception:
        pass

    return st.session_state.get("property_expenses_list", default_expenses)


def record_property_expense(property_id, property_name, category, amount, description, expense_date, user_id, user_email, receipt_url=None, receipt_name=None):
    """Save new expense (with optional receipt attachment) to DB/State."""
    new_expense = {
        "property_id": property_id,
        "property_name": property_name,
        "category": category,
        "amount": float(amount),
        "description": description.strip(),
        "expense_date": str(expense_date),
        "receipt_url": receipt_url,
        "receipt_name": receipt_name,
        "created_at": datetime.now().isoformat(),
    }
    if user_id:
        new_expense["user_id"] = user_id
    if user_email:
        new_expense["user_email"] = user_email

    if sb:
        try:
            sb.table("expenses").insert(new_expense).execute()
        except Exception:
            pass

    if "property_expenses_list" not in st.session_state:
        st.session_state["property_expenses_list"] = []
    st.session_state["property_expenses_list"].append(new_expense)


def render_financial_net_income_engine(user):
    """Renders the Net Income, Expense Logger, and CSV/JSON Profit & Loss Dashboard."""
    user_id = getattr(user, "id", None)
    user_email = getattr(user, "email", None)
    currency = st.session_state.get("app_currency", "GHS")

    st.markdown("### 📊 Property Financial Engine & Net Profit Center")
    st.caption("Track gross rent, log property expenses with receipts, and monitor net cash flow per property.")

    properties = fetch_properties(user_id, user_email) if sb else []
    if not properties:
        properties = [{"id": "prop_1", "name": "East Legon Executive Apartment #4B"}]

    prop_map = {p["id"]: p.get("name") or p.get("title", "Property") for p in properties}

    expenses = fetch_property_expenses(user_id, user_email)
    payments = fetch_payments(user_id, user_email) if sb else []

    total_gross_collected = sum(
        float(p.get("amount", 0) or 0)
        for p in payments
        if str(p.get("status", "")).lower() in ("paid", "success", "completed")
    )
    if total_gross_collected == 0 and not sb:
        total_gross_collected = 16000.00

    total_expenses = sum(float(e.get("amount", 0) or 0) for e in expenses)
    net_profit = total_gross_collected - total_expenses
    profit_margin = (net_profit / total_gross_collected * 100) if total_gross_collected > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gross Rent Collected", f"{currency} {total_gross_collected:,.2f}")
    m2.metric("Total Expenses", f"{currency} {total_expenses:,.2f}", delta="-Costs", delta_color="inverse")
    m3.metric("Net Income / Profit", f"{currency} {net_profit:,.2f}", delta=f"{profit_margin:.1f}% Margin", delta_color="normal" if net_profit >= 0 else "inverse")
    m4.metric("Expense Ratio", f"{(total_expenses / total_gross_collected * 100):.1f}%" if total_gross_collected > 0 else "0%")

    st.divider()

    fin_tab1, fin_tab2, fin_tab3 = st.tabs([
        "➕ Log Property Expense",
        "📜 Expense Log & Categories",
        "📄 Export P&L Financial Statement",
    ])

    with fin_tab1:
        with st.form("add_expense_form", clear_on_submit=True):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                selected_prop_id = st.selectbox("Select Property *", list(prop_map.keys()), format_func=lambda x: prop_map[x])
                exp_category = st.selectbox("Expense Category *", EXPENSE_CATEGORIES)
                exp_amount = st.number_input(f"Expense Amount ({currency}) *", min_value=1.0, value=100.0, step=50.0)
            with col_e2:
                exp_date = st.date_input("Expense Date *", value=date.today())
                exp_desc = st.text_input("Expense Description *", placeholder="e.g., Replaced leaking bathroom tap")
                exp_receipt = st.file_uploader("Attach Receipt (Optional)", type=["png", "jpg", "jpeg", "pdf"])

            submit_exp = st.form_submit_button("💾 Save & Deduct Expense", type="primary", use_container_width=True)

            if submit_exp:
                if not exp_desc.strip() or exp_amount <= 0:
                    st.error("Please enter a valid description and amount.")
                else:
                    rcpt_url = None
                    rcpt_name = None
                    if exp_receipt is not None:
                        raw = exp_receipt.getvalue()
                        mime = getattr(exp_receipt, "type", None) or "application/pdf"
                        rcpt_name = getattr(exp_receipt, "name", "expense_receipt.pdf")
                        rcpt_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

                    prop_name = prop_map.get(selected_prop_id, "Property")
                    record_property_expense(selected_prop_id, prop_name, exp_category, exp_amount, exp_desc, exp_date, user_id, user_email, rcpt_url, rcpt_name)
                    st.success(f"✅ Expense of {currency} {exp_amount:,.2f} logged for {prop_name}!")
                    st.rerun()

    with fin_tab2:
        if expenses:
            st.markdown("#### 📜 Itemized Property Expenses")
            cat_totals = {}
            for e in expenses:
                c = e.get("category", "Other")
                cat_totals[c] = cat_totals.get(c, 0.0) + float(e.get("amount", 0) or 0)

            c_chart, c_table = st.columns([1, 1.5])
            with c_chart:
                st.markdown("**Expenses by Category**")
                st.bar_chart(cat_totals)

            with c_table:
                for idx, e in enumerate(reversed(expenses)):
                    with st.container(border=True):
                        st.write(f"**{e.get('category')}** — {currency} {float(e.get('amount', 0) or 0):,.2f}")
                        st.caption(f"📍 {e.get('property_name')} | Date: `{e.get('expense_date', e.get('date'))}`")
                        st.write(f"*{e.get('description')}*")
                        r_url = str(e.get("receipt_url") or "")
                        if r_url.startswith("data:") and ";base64," in r_url:
                            hdr, b64 = r_url.split(";base64,", 1)
                            st.download_button(
                                "📎 Download Receipt",
                                data=base64.b64decode(b64),
                                file_name=e.get("receipt_name") or f"expense_receipt_{idx+1}.pdf",
                                mime=hdr.replace("data:", ""),
                                key=f"dl_exp_rcpt_{idx}",
                            )
        else:
            st.info("No property expenses logged yet.")

    with fin_tab3:
        st.markdown("#### 📄 Profit & Loss Financial Statement")
        clean_items = [{k: v for k, v in e.items() if k != "receipt_url"} for e in expenses]
        statement_data = {
            "statement_period": f"{datetime.now().strftime('%Y')} YTD Financial Statement",
            "currency": currency,
            "gross_revenue": total_gross_collected,
            "operating_expenses": total_expenses,
            "net_operating_income": net_profit,
            "profit_margin_pct": round(profit_margin, 2),
            "itemized_expenses": clean_items,
        }

        st.json(statement_data)

        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["Date", "Property", "Category", "Description", f"Amount ({currency})"])
        for e in clean_items:
            writer.writerow([
                e.get("expense_date") or e.get("date") or "",
                e.get("property_name") or "",
                e.get("category") or "",
                e.get("description") or "",
                f"{float(e.get('amount', 0) or 0):.2f}",
            ])

        dl_c1, dl_c2 = st.columns(2)
        with dl_c1:
            st.download_button(
                "📊 Download P&L Spreadsheet (CSV)",
                data=csv_buf.getvalue().encode("utf-8"),
                file_name=f"RentMaster_Expenses_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )
        with dl_c2:
            st.download_button(
                "📥 Download Official P&L Statement (JSON)",
                data=json.dumps(statement_data, indent=2),
                file_name=f"RentMaster_P_and_L_Statement_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True,
            )
