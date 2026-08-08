"""
RentMaster-GH - Property Expense & Net Income Financial Engine
Tracks Property Expenses, Cash Flow, Net Profit Margin, and Generates P&L Statements.
"""
import streamlit as st
import json
from datetime import datetime, date
from services.database import sb, fetch_properties, fetch_payments

EXPENSE_CATEGORIES = [
    "🛠️ Maintenance & Repairs",
    "💡 Utilities (Water/Electricity)",
    "🤝 Agent & Management Fees",
    "🏛️ Property Taxes & Legal Fees",
    "🛡️ Property Insurance",
    "📦 Miscellaneous / Other"
]


def fetch_property_expenses(user_id, user_email):
    """Fetch all logged property expenses."""
    default_expenses = [
        {"id": "exp_101", "property_name": "East Legon Executive Apartment #4B", "category": "🛠️ Maintenance & Repairs", "amount": 800.00, "date": "2024-01-15", "description": "AC Servicing & Gas Refill"},
        {"id": "exp_102", "property_name": "East Legon Executive Apartment #4B", "category": "💡 Utilities (Water/Electricity)", "amount": 350.00, "date": "2024-02-01", "description": "ECG Meter Bill Payment"}
    ]

    if not sb:
        return st.session_state.get("property_expenses_list", default_expenses)

    try:
        res = sb.table("expenses").select("*, properties(name)").execute()
        if res.data:
            return res.data
    except Exception:
        pass

    return st.session_state.get("property_expenses_list", default_expenses)


def record_property_expense(property_id, property_name, category, amount, description, expense_date, user_id, user_email):
    """Save new expense to DB/State."""
    new_expense = {
        "property_id": property_id,
        "property_name": property_name,
        "category": category,
        "amount": float(amount),
        "description": description,
        "expense_date": str(expense_date),
        "created_at": datetime.now().isoformat()
    }
    if user_id: new_expense["user_id"] = user_id
    if user_email: new_expense["user_email"] = user_email

    if sb:
        try:
            sb.table("expenses").insert(new_expense).execute()
        except Exception:
            pass

    if "property_expenses_list" not in st.session_state:
        st.session_state["property_expenses_list"] = []
    st.session_state["property_expenses_list"].append(new_expense)


# ---------------------------------------------------------------------------
# MAIN FINANCIAL WIDGET EXPORT
# ---------------------------------------------------------------------------
def render_financial_net_income_engine(user):
    """Renders the Net Income, Expense Logger, and Profit & Loss Dashboard."""
    user_id = getattr(user, "id", None)
    user_email = getattr(user, "email", None)
    currency = st.session_state.get("app_currency", "GHS")

    st.markdown("### 📊 Property Financial Engine & Net Profit Center")
    st.caption("Track gross rent, log property expenses, and monitor net cash flow per property.")

    properties = fetch_properties(user_id, user_email) if 'fetch_properties' in globals() or sb else []
    if not properties:
        properties = [{"id": "prop_1", "name": "East Legon Executive Apartment #4B"}]

    prop_map = {p["id"]: p.get("name") or p.get("title", "Property") for p in properties}

    # Fetch Financials
    expenses = fetch_property_expenses(user_id, user_email)
    payments = fetch_payments(user_id, user_email) if sb else []

    total_gross_collected = sum(float(p.get("amount", 0)) for p in payments if p.get("status") == "paid")
    if total_gross_collected == 0:
        total_gross_collected = 16000.00  # Demo default

    total_expenses = sum(float(e.get("amount", 0)) for e in expenses)
    net_profit = total_gross_collected - total_expenses
    profit_margin = (net_profit / total_gross_collected * 100) if total_gross_collected > 0 else 0.0

    # 1. NET PROFIT METRIC CARDS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Gross Rent Collected", f"{currency} {total_gross_collected:,.2f}")
    m2.metric("Total Expenses", f"{currency} {total_expenses:,.2f}", delta="-Costs", delta_color="inverse")
    
    profit_color = "normal" if net_profit >= 0 else "inverse"
    m3.metric("Net Income / Profit", f"{currency} {net_profit:,.2f}", delta=f"{profit_margin:.1f}% Margin", delta_color=profit_color)
    m4.metric("Expense Ratio", f"{(total_expenses / total_gross_collected * 100):.1f}%" if total_gross_collected > 0 else "0%")

    st.divider()

    fin_tab1, fin_tab2, fin_tab3 = st.tabs([
        "➕ Log Property Expense",
        "📜 Expense Log & Categories",
        "📄 Export P&L Financial Statement"
    ])

    # TAB 1: LOG EXPENSE FORM
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
                exp_receipt = st.file_uploader("Attach Receipt (Optional)", type=["png", "jpg", "pdf"])

            submit_exp = st.form_submit_button("💾 Save & Deduct Expense", type="primary", use_container_width=True)

            if submit_exp:
                if not exp_desc or exp_amount <= 0:
                    st.error("Please enter a valid description and amount.")
                else:
                    prop_name = prop_map.get(selected_prop_id, "Property")
                    record_property_expense(selected_prop_id, prop_name, exp_category, exp_amount, exp_desc, exp_date, user_id, user_email)
                    st.success(f"✅ Expense of {currency} {exp_amount:,.2f} logged for {prop_name}!")
                    st.rerun()

    # TAB 2: EXPENSE AUDIT LOG
    with fin_tab2:
        if expenses:
            st.markdown("#### 📜 Itemized Property Expenses")
            
            # Category Breakdown Chart
            cat_totals = {}
            for e in expenses:
                c = e.get("category", "Other")
                cat_totals[c] = cat_totals.get(c, 0.0) + float(e.get("amount", 0))

            c_chart, c_table = st.columns([1, 1.5])
            with c_chart:
                st.markdown("**Expenses by Category**")
                st.bar_chart(cat_totals)

            with c_table:
                for idx, e in enumerate(reversed(expenses)):
                    with st.container(border=True):
                        st.write(f"**{e.get('category')}** — {currency} {float(e.get('amount', 0)):,.2f}")
                        st.caption(f"📍 {e.get('property_name')} | Date: `{e.get('expense_date', e.get('date'))}`")
                        st.write(f"*{e.get('description')}*")
        else:
            st.info("No property expenses logged yet.")

    # TAB 3: P&L FINANCIAL STATEMENT EXPORT
    with fin_tab3:
        st.markdown("#### 📄 Profit & Loss Financial Statement")
        
        statement_data = {
            "statement_period": f"{datetime.now().strftime('%Y')} YTD Financial Statement",
            "currency": currency,
            "gross_revenue": total_gross_collected,
            "operating_expenses": total_expenses,
            "net_operating_income": net_profit,
            "profit_margin_pct": profit_margin,
            "itemized_expenses": expenses
        }

        st.json(statement_data)
        
        st.download_button(
            "📥 Download Official P&L Statement (JSON)",
            data=json.dumps(statement_data, indent=2),
            file_name=f"RentMaster_P_and_L_Statement_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            type="primary",
            use_container_width=True
        )
