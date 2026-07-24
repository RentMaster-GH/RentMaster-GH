import os
import json
import requests
import pandas as pd
import streamlit as st
import requests

def create_payment(email, amount):
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {st.secrets['PAYSTACK_SECRET_KEY']}",
        "Content-Type": "application/json"
    }
    data = {
        "email": email,
        "amount": int(amount * 100), # Paystack uses kobo/pesewas
        "currency": "GHS"
    }
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    if result['status']:
        payment_url = result['data']['authorization_url']
        st.link_button("Click to Pay on Paystack", payment_url)
    else:
        st.error("Failed to create payment link")

APP_URL = "https://rentmaster-gh-3j3u3xk..."
st.set_page_config(page_title="RentMaster GH")
st.title("RentMaster GH")

# MEMORY STORAGE
if "payments" not in st.session_state: st.session_state.payments = []
if "last_url" not in st.session_state: st.session_state.last_url = ""
if "last_ref" not in st.session_state: st.session_state.last_ref = ""

# SECRET CHECK
try: KEY = st.secrets["PAYSTACK_SECRET_KEY"]
except: st.error("Add PAYSTACK_SECRET_KEY in Settings > Secrets"); st.stop()

st.title("RentMaster GH")

# 1. LOAD PAYMENTS FROM FILE FIRST
# Load payments
payments = []

if os.path.exists("payments.json"):
    with open("payments.json", "r") as f:
        payments = json.load(f)

# 2. MANUAL VERIFY BOX
st.subheader("Verify Payment Manually")
manual_ref = st.text_input("7rqa828r2v", value="")
if st.button("Verify & Save Payment"):
    headers = {"Authorization": "Bearer sk_test_32276d254647ec901b058f5a96d6a8d64bfc67ae"}
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
    submitted = st.form_submit_button("Pay Now")
    
if submitted:
    # Call Paystack to create payment link
    create_payment(email, amount)
    st.success(f"Redirecting to Paystack to pay GHS {amount}")
    st.rerun()
else:
    st.error("Please fill email and amount")
st.subheader("Recent Payments")
if payments:
    st.dataframe(payments)
else:
    st.info("No payments yet")

# 3. GET APP URL DYNAMICALLY for callback
APP_URL = st.get_option("browser.serverAddress")
if not APP_URL:
    APP_URL = "https://rentmaster-gh-3j3u3aqkevcgkfja5raz.streamlit.app"

col1, col2 = st.columns(2)

# LAYOUT
tab1, tab2 = st.tabs(["Pay Rent", "Payment History"])

st.subheader("Pay Rent")
email = st.text_input("Tenant Email", "test@gmail.com")
amount = st.number_input("Amount GHS", 1.0, 10000.0, 1.0)

# 2. PAYMENT SECTION
st.subheader("1. Create Payment Link")
email = st.text_input("Tenant Email", placeholder="tenant@gmail.com")
amount = st.number_input("Amount GHS", min_value=1.0, value=100.0, step=10.0)

# COLUMNS
col1, col2 = st.columns(2)

with col1:
    st.subheader("Step 1: Pay")
    email = st.text_input("Tenant Email")
    amount = st.number_input("Amount GHS", 1.0, 50000.0, 100.0)
    
    if st.button("1. Generate Payment Link", type="primary"):
        r = requests.post("https://api.paystack.co/transaction/initialize", 
            headers={"Authorization": f"Bearer {KEY}"}, 
            json={"email": email, "amount": int(amount*100)})
        res = r.json()
        if res["status"]:
            st.session_state.last_url = res["data"]["authorization_url"]
            st.session_state.last_ref = res["data"]["reference"]
            st.success("Link Ready")
        else: st.error(res["message"])

    if st.session_state.last_url:
        st.link_button("2. CLICK TO PAY ON PAYSTACK", st.session_state.last_url, type="primary")
        st.code(f"Save Ref: {st.session_state.last_ref}")

with col2:
    st.subheader("Step 2: Verify")
    st.write("After paying, come back here")
    ref = st.text_input("Paste Reference", st.session_state.last_ref)
    
    if st.button("3. Verify Payment"):
        r = requests.get(f"https://api.paystack.co/transaction/verify/{ref}", headers={"Authorization": f"Bearer {KEY}"})
        res = r.json()
        if res["status"] and res["data"]["status"] == "success":
            p = {"Email": res["data"]["customer"]["email"], "Amount GHS": res["data"]["amount"]/100, "Ref": ref}
            if p["Ref"] not in [x["Ref"] for x in st.session_state.payments]:
                st.session_state.payments.append(p)
            st.success(f"✅ GHS {p['Amount GHS']} Verified")
            st.rerun()
        else: st.error("Not Successful")

st.divider()

# 3. VERIFY SECTION - THIS BYPASSES THE BROKEN REDIRECT
st.subheader("2. Verify Payment")
st.write("After paying, copy `reference=` from the URL and paste here")
ref_input = st.text_input("Paste Reference Here", st.session_state.get("last_ref", ""))

if st.button("Verify & Save Payment", use_container_width=True):
    headers = {"Authorization": f"Bearer {KEY}"}
    r = requests.get(f"https://api.paystack.co/transaction/verify/{ref_input}", headers=headers)
    res = r.json()
    
    if res["status"] and res["data"]["status"] == "success":
        payment = {
            "Email": res["data"]["customer"]["email"],
            "Amount GHS": res["data"]["amount"] / 100,
            "Reference": res["data"]["reference"],
        }
        if payment["Reference"] not in [p["Reference"] for p in st.session_state.payments]:
            st.session_state.payments.append(payment)
        st.success(f"✅ Verified! GHS {payment['Amount GHS']} received")
        st.balloons()
        st.rerun()
    else:
        st.error("❌ Payment not found or failed")

with tab2:
    st.subheader("Recent Payments")
    if st.session_state.payments:
        st.dataframe(pd.DataFrame(st.session_state.payments), use_container_width=True)
    else:
        st.info("No payments yet")

with col2:
    st.subheader("Pay Rent")
    email = st.text_input("Tenant Email", "papastickle@gmail.com")
    amount = st.number_input("Amount GHS", min_value=1.0, value=1.00, step=1.0)

    if st.button("Pay Now", type="primary", use_container_width=True):
        with st.spinner("Creating payment link..."):
            headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}", "Content-Type": "application/json"}
            data = {
                "email": email, 
                "amount": int(amount * 100), # to pesewas
                "callback_url": APP_URL # This will still fail, so we have manual verify
            }
            try:
                r = requests.post('https://api.paystack.co/transaction/initialize', headers=headers, json=data, timeout=10)
                response = r.json()
            except Exception as e:
                st.error(f"API Error: {e}")
                st.stop()
        
        if response.get('status'):
            payment_url = response['data']['authorization_url']
            ref = response['data']['reference']
            st.session_state.last_ref = ref
            st.success("Link Created!")
            st.link_button("👉 CLICK TO PAY WITH PAYSTACK", payment_url, type="primary", use_container_width=True)
            st.code(f"Save this Reference: {ref}")
        else:
            st.error(f"Error: {response.get('message','Unknown error')}")

st.divider()
st.subheader("Verify Payment Manually")
st.write("After paying on Paystack, copy the `reference=` from the URL and paste here")

reference_input = st.text_input("Paste Reference Here", value=st.session_state.last_ref)

if st.button("Verify Payment", type="secondary", use_container_width=True):
    if not reference_input:
        st.warning("Please paste a reference")
    else:
        with st.spinner("Verifying with Paystack..."):
            headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
            r = requests.get(f"https://api.paystack.co/transaction/verify/{reference_input}", headers=headers, timeout=10)
            response = r.json()
        
        if response.get('status') and response['data']['status'] == 'success':
            amount_paid = response['data']['amount'] / 100
            email_paid = response['data']['customer']['email']
            ref_paid = response['data']['reference']
            
            # Prevent duplicates
            if not any(p['reference'] == ref_paid for p in st.session_state.payments):
                st.session_state.payments.append({
                    "email": email_paid, 
                    "amount_ghs": amount_paid, 
                    "reference": ref_paid,
                    "date": response['data']['paid_at'][:10]
                })
            st.success(f"✅ Payment of GHS {amount_paid} Verified!")
            st.balloons()
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

st.dataframe(pd.DataFrame(st.session_state.payments))

st.dataframe(pd.DataFrame(st.session_state.payments))
