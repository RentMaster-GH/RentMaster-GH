import streamlit as st
import requests
import json
import os

PAYSTACK_SECRET_KEY = st.secrets["PAYSTACK_SECRET_KEY"] 
APP_URL = "https://rentmaster-gh.streamlit.app/" # We'll update this after deploy

st.title("🏠 RentMaster GH")

# Load payments
if os.path.exists("payments.json"):
    with open("payments.json", "r") as f:
        payments = json.load(f)
else:
    payments = []

# AUTO VERIFY - This will work on Streamlit Cloud!
if "reference" in st.query_params:
    reference = st.query_params["reference"]
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    r = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
    response = r.json()
    
    if response['status'] and response['data']['status'] == 'success':
        new_payment = {
            "email": response['data']['customer']['email'],
            "amount": response['data']['amount'] / 100,
            "ref": reference
        }
        payments.append(new_payment)
        with open("payments.json", "w") as f:
            json.dump(payments, f)
        st.success(f"✅ Payment of GHS {new_payment['amount']} received!")
    st.query_params.clear()

# Show payments
st.subheader("Recent Payments")
if payments:
    for p in payments:
        st.write(f"✅ GHS {p['amount']} from {p['email']}")
else:
    st.info("No payments yet")

# Pay form
st.subheader("Pay Rent")
with st.form("payment_form"):
    email = st.text_input("Tenant Email")
    amount = st.number_input("Amount GHS", min_value=1.0, value=500.0)
    submitted = st.form_submit_button("Pay Now")
    
    if submitted:
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        data = {
            "email": email,
            "amount": int(amount * 100),
            "callback_url": APP_URL
        }
        r = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, data=data)
        response = r.json()
        
        if response['status']:
            payment_url = response['data']['authorization_url']
            st.link_button("Click here to Pay with Paystack", payment_url, type="primary")
