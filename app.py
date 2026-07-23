import streamlit as st
import requests
import json
import os

<<<<<<< HEAD
PAYSTACK_SECRET_KEY = st.secrets["PAYSTACK_SECRET_KEY"] 
APP_URL = "https://rentmaster-gh.streamlit.app/" # We'll update this after deploy

st.title("🏠 RentMaster GH")

# Load payments
=======
APP_URL = "https://rentmaster-gh-3j3u3aqkevcgxkfja5razj.streamlit.app/"

PAYSTACK_SECRET_KEY = st.secrets["PAYSTACK_SECRET_KEY"]

st.title("🏠 RentMaster GH")

# 1. LOAD PAYMENTS FROM FILE FIRST
>>>>>>> 1b0256b (fix: add target blank to paystack link)
if os.path.exists("payments.json"):
    with open("payments.json", "r") as f:
        payments = json.load(f)
else:
    payments = []

<<<<<<< HEAD
# AUTO VERIFY - This will work on Streamlit Cloud!
if "reference" in st.query_params:
    reference = st.query_params["reference"]
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    r = requests.get(f'https://api.paystack.co/transaction/verify/{reference}', headers=headers)
=======
# 2. MANUAL VERIFY BOX
st.subheader("Verify Payment Manually")
manual_ref = st.text_input("7rqa828r2v", value="")
if st.button("Verify & Save Payment"):
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    r = requests.get(f'https://api.paystack.co/transaction/verify/{manual_ref}', headers=headers)
>>>>>>> 1b0256b (fix: add target blank to paystack link)
    response = r.json()
    
    if response['status'] and response['data']['status'] == 'success':
        new_payment = {
            "email": response['data']['customer']['email'],
            "amount": response['data']['amount'] / 100,
<<<<<<< HEAD
            "ref": reference
=======
            "ref": manual_ref
>>>>>>> 1b0256b (fix: add target blank to paystack link)
        }
        payments.append(new_payment)
        with open("payments.json", "w") as f:
            json.dump(payments, f)
<<<<<<< HEAD
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
=======
        st.success(f"✅ Payment of GHS {new_payment['amount']} saved!")
        st.rerun()
    else:
        st.error("Payment not found or failed")

# 3. MANUAL VERIFY - after payment
st.subheader("3. Complete Payment")
reference_input = st.text_input("Paste Reference from Paystack URL here", key="ref_input")

if st.button("Verify Payment"):
    if reference_input:
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        r = requests.get(f"https://api.paystack.co/transaction/verify/{reference_input}", headers=headers)
        response = r.json()
        
        if response['status'] and response['data']['status'] == 'success':
            amount = response['data']['amount'] / 100
            email = response['data']['customer']['email']
            
            new_payment = {"email": email, "amount": amount, "ref": reference_input}
            payments.append(new_payment)
            with open("payments.json", "w") as f:
                json.dump(payments, f)
            
            st.success(f"✅ Payment of GHS {amount} received!")
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
>>>>>>> 1b0256b (fix: add target blank to paystack link)
    submitted = st.form_submit_button("Pay Now")
    
    if submitted:
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        data = {
            "email": email,
            "amount": int(amount * 100),
<<<<<<< HEAD
            "callback_url": APP_URL
        }
        r = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, data=data)
        response = r.json()
        
        if response['status']:
            payment_url = response['data']['authorization_url']
            st.link_button("Click here to Pay with Paystack", payment_url, type="primary")
=======
            "callback_url": "https://stunning-parakeet-vpp977gwx6pw55-8501.app.github.dev/"
        }
        r = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, data=data)
response = r.json()

if response['status']:
    payment_url = response['data']['authorization_url']
    st.link_button("Click here to Pay with Paystack", payment_url, type="primary", target="_blank")
else:
    st.error("Could not initialize payment: " + response['message'])
>>>>>>> 1b0256b (fix: add target blank to paystack link)
