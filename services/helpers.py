# services/helpers.py
import os
import streamlit as st
import streamlit.components.v1 as components
from datetime import date
from streamlit.errors import StreamlitSecretNotFoundError


# ---------------------------------------------------------------------------
# Google Analytics & Site Verification Injectors
# ---------------------------------------------------------------------------
def inject_google_analytics(measurement_id="G-EFD2P6FKM5"):
    """
    Injects Google Analytics 4 tracking snippet.
    """
    ga_html = f"""
    <!-- Global site tag (gtag.js) - Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={measurement_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{measurement_id}');
    </script>
    """
    components.html(ga_html, height=0, width=0)


def inject_google_site_verification(verification_code="SXu9dztavBBjKgrko60Tx2CjufX2KvyRhW42SOczZrc"):
    """
    Injects Google Site Verification meta tag into the main browser document head.
    """
    verification_js = f"""
    <script>
      (function() {{
        const parentHead = window.parent.document.head;
        if (!parentHead.querySelector('meta[name="google-site-verification"]')) {{
          const meta = window.parent.document.createElement('meta');
          meta.name = 'google-site-verification';
          meta.content = '{verification_code}';
          parentHead.appendChild(meta);
        }}
      }})();
    </script>
    """
    components.html(verification_js, height=0, width=0)


# ---------------------------------------------------------------------------
# Currency & Payout Data Structures
# ---------------------------------------------------------------------------
SUPPORTED_CURRENCIES = {
    "GHS": {"symbol": "GHs", "name": "Ghanaian Cedi (GHs / GH₵)"},
    "USD": {"symbol": "$", "name": "US Dollar ($)"},
    "EUR": {"symbol": "€", "name": "Euro (€)"},
    "GBP": {"symbol": "£", "name": "British Pound (£)"},
    "NGN": {"symbol": "₦", "name": "Nigerian Naira (₦)"},
    "KES": {"symbol": "KSh", "name": "Kenyan Shilling (KSh)"},
    "ZAR": {"symbol": "R", "name": "South African Rand (R)"},
    "CAD": {"symbol": "$", "name": "Canadian Dollar ($)"},
    "AUD": {"symbol": "$", "name": "Australian Dollar ($)"},
    "XOF": {"symbol": "CFA", "name": "West African CFA (CFA)"},
    "INR": {"symbol": "₹", "name": "Indian Rupee (₹)"},
    "AED": {"symbol": "AED", "name": "UAE Dirham (AED)"},
}

GLOBAL_PAYOUT_BANKS = {
    "Ghana": {
        "MTN Mobile Money": "MTN",
        "Vodafone Cash / Telecel Cash": "VOD",
        "AirtelTigo Money": "ATL",
        "GCB Bank": "040100",
        "Ecobank Ghana": "090100",
        "Absa Bank Ghana": "030100",
        "Fidelity Bank Ghana": "240100",
        "Stanbic Bank Ghana": "190100",
        "CalBank": "140100",
        "Zenith Bank Ghana": "120100",
    },
    "Nigeria": {
        "Access Bank": "044",
        "Guaranty Trust Bank (GTB)": "058",
        "First Bank of Nigeria": "011",
        "Zenith Bank": "057",
        "Kuda Microfinance Bank": "50211",
        "OPay Digital Services": "999992",
    },
    "Kenya": {
        "M-Pesa": "MPESA",
        "Equity Bank": "068",
        "KCB Bank": "001",
        "Absa Bank Kenya": "003",
    },
    "South Africa": {
        "Capitec Bank": "470010",
        "FirstNational Bank (FNB)": "250655",
        "Standard Bank": "051001",
        "Nedbank": "198765",
        "Absa Bank SA": "632005",
    },
    "International / Other": {
        "International SWIFT / IBAN Wire": "SWIFT_GLOBAL",
        "Direct Card Payout": "CARD_GLOBAL",
    }
}


def get_secret(key: str, default: str = "") -> str:
    env_val = os.environ.get(key)
    if env_val:
        return env_val
    try:
        if key in st.secrets:
            return st.secrets[key]
    except StreamlitSecretNotFoundError:
        pass
    return default


def get_current_currency():
    return st.session_state.get("app_currency", "GHS")


def fmt_money(v, currency_code=None):
    code = currency_code or get_current_currency()
    symbol = SUPPORTED_CURRENCIES.get(code, {}).get("symbol", "GHs")
    try:
        return f"{symbol} {float(v):,.2f}"
    except (TypeError, ValueError):
        return "-"


def fmt_date(v):
    if not v:
        return "-"
    try:
        return str(v)[:10]
    except Exception:
        return str(v)


def get_active_user_info():
    user = st.session_state.get("user")
    if not user:
        return None, None
    return getattr(user, "id", None), getattr(user, "email", None)


def prop_label(p):
    if not isinstance(p, dict): return "-"
    p_name = p.get('name') or p.get('property_name', 'Unnamed')
    return f"{p_name} - {p.get('address', '')}"


def tenant_label(t):
    if not isinstance(t, dict): return "-"
    return t.get("name", "Unnamed")


def compute_tenant_ledger(tenant: dict, all_payments: list):
    if not isinstance(tenant, dict):
        return {"monthly_rent": 0.0, "total_charged": 0.0, "total_paid": 0.0, "balance": 0.0, "statement": [], "tenant_payments": []}

    monthly_rent = float(tenant.get("rent_amount") or 0.0)
    lease_start_str = tenant.get("lease_start")

    statement = []
    total_charged = 0.0

    if lease_start_str:
        try:
            start_dt = date.fromisoformat(str(lease_start_str)[:10])
            today_dt = date.today()

            months_count = (today_dt.year - start_dt.year) * 12 + (today_dt.month - start_dt.month) + 1
            months_count = max(1, months_count)

            curr_dt = start_dt
            for _ in range(months_count):
                due_date_str = curr_dt.strftime("%Y-%m-01")
                charge_amt = monthly_rent
                total_charged += charge_amt
                statement.append({
                    "date": due_date_str,
                    "type": "Rent Charge",
                    "description": f"Monthly Rent ({curr_dt.strftime('%B %Y')})",
                    "charge": charge_amt,
                    "credit": 0.0,
                    "ref": "-"
                })
                y = curr_dt.year + (curr_dt.month // 12)
                m = (curr_dt.month % 12) + 1
                curr_dt = date(y, m, 1)
        except Exception:
            total_charged = monthly_rent
    else:
        total_charged = monthly_rent

    tenant_id = tenant.get("id")
    tenant_payments = [p for p in all_payments if isinstance(p, dict) and p.get("tenant_id") == tenant_id and p.get("status") == "paid"]
    total_paid = sum(float(p.get("amount") or 0.0) for p in tenant_payments)

    for p in tenant_payments:
        statement.append({
            "date": fmt_date(p.get("payment_date")),
            "type": "Rent Payment",
            "description": f"Payment ({str(p.get('payment_method', 'online')).replace('_', ' ').title()})",
            "charge": 0.0,
            "credit": float(p.get("amount") or 0.0),
            "ref": p.get("notes", "-")
        })

    statement.sort(key=lambda x: str(x["date"]))

    running_balance = 0.0
    for item in statement:
        running_balance += (item["charge"] - item["credit"])
        item["balance"] = running_balance

    balance = total_charged - total_paid

    return {
        "monthly_rent": monthly_rent,
        "total_charged": total_charged,
        "total_paid": total_paid,
        "balance": balance,
        "statement": statement,
        "tenant_payments": tenant_payments
    }
