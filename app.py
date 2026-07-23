import streamlit as st
import requests
import json
import os

APP_URL = "https://rentmaster-gh-3j3u3aqkevcgxkfja5razj.streamlit.app/"

# Safe way to get key
if "PAYSTACK_SECRET_KEY" not in st.secrets:
    st.error("Add PAYSTACK_SECRET_KEY in Settings > Secrets")
    st.stop()
PAYSTACK_SECRET_KEY = st.secrets["PAYSTACK_SECRET_KEY"]

st.title("RentMaster GH")

# 1. LOAD PAYMENTS FROM FILE FIRST
# Load payments
payments = []
>>>>>>> b167939 (Udated 1)
if os.path.exists("payments.json"):
    with open("payments.json", "r") as f:
        payments = json.load(f)

# 2. MANUAL VERIFY BOX
st.subheader("Verify Payment Manually")
manual_ref = st.text_input("7rqa828r2v", value="")
if st.button("Verify & Save Payment"):
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    r = requests.get(f'https://api.paystack.co/transaction/verify/{manual_ref}', headers=headers)
    response = r.json()
    
    if response['status'] and response['data']['status'] == 'success':
        new_payment = {
            "email": response['data']['customer']['email'],
            "amount": response['data']['amount'],
            "ref": manual_ref
        }
        payments.append(new_payment)
        with open("payments.json", "w") as f:
            json.dump(payments, f)

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
    if st.form_submit_button("Pay Now"):
        st.success(f"✅ Payment of GHS {new_payment['amount']} saved!")
        st.rerun()
    else:
        st.error("Payment not found or failed")
st.subheader("Recent Payments")
if payments:
    st.dataframe(payments)
else:
    st.info("No payments yet")

st.subheader("Pay Rent")
email = st.text_input("Tenant Email", "papastickle@gmail.com")
amount = st.number_input("Amount GHS", min_value=1.0, value=1.00)

if st.button("Pay Now", type="primary"):
    with st.spinner("Creating payment..."):
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        data = {
            "email": email, 
            "amount": int(amount * 100),
            "callback_url": st.get_option("browser.serverAddress")
        }
        r = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, data=data)
        response = r.json()
    
    if response['status']:
        payment_url = response['data']['authorization_url']
        ref = response['data']['reference']
        st.session_state['last_ref'] = ref
        st.success("Payment link created!")
        st.link_button("👉 Click here to Pay with Paystack", payment_url, type="primary")
        st.code(f"Reference: {ref}")
    else:
        st.error("Error: " + response.get('message',''))

st.subheader("Verify Payment")
reference_input = st.text_input("Paste Reference from Paystack URL here", value=st.session_state.get('last_ref', ''))

if st.button("Verify Payment"):
    if reference_input:
        with st.spinner("Verifying..."):
            headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
            r = requests.get(f"https://api.paystack.co/transaction/verify/{reference_input}", headers=headers)
            response = r.json()
        
        if response['status'] and response['data']['status'] == 'success':
            amount_paid = response['data']['amount'] / 100
            email_paid = response['data']['customer']['email']
            if not any(p['ref'] == reference_input for p in payments):
                payments.append({"email": email_paid, "amount": amount_paid, "ref": reference_input})
                with open("payments.json", "w") as f:
                    json.dump(payments, f)
            st.success(f"✅ Payment of GHS {amount_paid} received!")
            st.rerun()
        else:
            st.error("Payment not successful yet")
# 4. SHOW PAYMENTS
st.subheader("Recent Payments")
if payments:
    for p in payments:
        st.write(f"✅ GHS {p['amount']} from {p['email']}")
else:
    st.info("No payments yet")

# 5. PAY FORM
st.subheader("Pay Rent")
with st.form("payment_form"):
    email = st.text_input("Tenant Email")
    amount = st.number_input("Amount GHS", min_value=1.0, value=1.0)
    submitted = st.form_submit_button("Pay Now")
    
    if submitted:
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        data = {
            "email": email,
            "amount": int(amount * 100),
            "callback_url": "https://stunning-parakeet-vpp977gwx6pw55-8501.app.github.dev/"
        }
        r = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, data=data)
response = r.json()

if response['status']:
    payment_url = response['data']['authorization_url']
    st.link_button("Click here to Pay with Paystack", payment_url, type="primary", target="_blank")
else:
    st.error("Could not initialize payment: " + response['message'])