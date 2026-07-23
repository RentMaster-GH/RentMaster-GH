import streamlit as st
import requests
import pandas as pd

<<<<<<< HEAD
APP_URL = "https://rentmaster-gh-3j3u3aqkevcgxkfja5razj.streamlit.app/"
=======
st.set_page_config(page_title="RentMaster GH", page_icon="🏠", layout="wide")
st.title("🏠 RentMaster GH")
>>>>>>> b216abc (Update 2)

# 1. DATA STRUCTURE: Use session_state instead of files. Files reset on Streamlit Cloud
if 'payments' not in st.session_state:
    st.session_state.payments = []
if 'last_ref' not in st.session_state:
    st.session_state.last_ref = ""

# 2. GET SECRET SAFELY
try:
    PAYSTACK_SECRET_KEY = st.secrets["PAYSTACK_SECRET_KEY"]
except KeyError:
    st.error("🚨 Add PAYSTACK_SECRET_KEY in Settings > Secrets")
    st.stop()

<<<<<<< HEAD
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
=======
# 3. GET APP URL DYNAMICALLY for callback
APP_URL = st.get_option("browser.serverAddress")
if not APP_URL:
    APP_URL = "https://rentmaster-gh-3j3u3aqkevcgkfja5raz.streamlit.app"

col1, col2 = st.columns(2)
>>>>>>> b216abc (Update 2)

with col1:
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
