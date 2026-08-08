# services/paystack.py
import requests
import uuid
import logging
import streamlit as st
from datetime import date
from services.helpers import get_secret, get_current_currency, get_active_user_info, fmt_money
from services.database import sb, clear_cache

logger = logging.getLogger("RentMaster")
PAYSTACK_SECRET_KEY = get_secret("PAYSTACK_SECRET_KEY")


def create_paystack_subaccount(business_name: str, bank_code: str, account_number: str, percentage_charge: float = 0.0, email: str = None, phone: str = None):
    if not PAYSTACK_SECRET_KEY:
        return {"status": False, "message": "PAYSTACK_SECRET_KEY is missing."}

    url = "https://api.paystack.co/subaccount"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "business_name": business_name,
        "settlement_bank": bank_code,
        "account_number": account_number,
        "percentage_charge": percentage_charge,
        "primary_contact_email": email or "",
        "primary_contact_phone": phone or "",
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}


def initialize_paystack_payment(email: str, amount_in_main_unit: float, callback_url: str, metadata: dict = None, subaccount: str = None, currency: str = None):
    if not PAYSTACK_SECRET_KEY:
        return {"status": False, "message": "PAYSTACK_SECRET_KEY is not configured."}

    curr = currency or get_current_currency()
    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "email": email,
        "amount": int(round(amount_in_main_unit * 100)),
        "currency": curr,
        "callback_url": callback_url,
        "channels": ["card", "mobile_money", "bank_transfer", "bank"],
        "metadata": metadata or {}
    }
    if subaccount:
        payload["subaccount"] = subaccount

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}


def verify_paystack_payment(reference: str):
    if not PAYSTACK_SECRET_KEY:
        return {"status": False, "message": "PAYSTACK_SECRET_KEY is missing."}

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        return {"status": False, "message": str(e)}


def save_landlord_bank_details(landlord_id: str, name: str, email: str, phone: str, bank_name: str, account_number: str, bank_code: str, platform_fee_pct: float = 0.0, id_card_url: str = None, user_id: str = None, user_email: str = None):
    if not sb:
        raise Exception("Database client not initialized.")

    ps_res = create_paystack_subaccount(
        business_name=name,
        bank_code=bank_code,
        account_number=account_number,
        percentage_charge=platform_fee_pct,
        email=email,
        phone=phone
    )

    if not ps_res.get("status"):
        raise Exception(f"Paystack Registration Failed: {ps_res.get('message', 'Unknown Error')}")

    subaccount_code = ps_res["data"]["subaccount_code"]

    payload = {
        "name": name,
        "email": email if email else None,
        "phone": phone if phone else None,
        "bank_name": bank_name,
        "account_number": account_number,
        "bank_code": bank_code,
        "paystack_subaccount_code": subaccount_code,
    }
    if user_id: payload["user_id"] = user_id
    if user_email: payload["user_email"] = user_email
    if id_card_url: payload["id_card_url"] = id_card_url

    if landlord_id:
        res = sb.table("landlords").update(payload).eq("id", landlord_id).execute()
    else:
        res = sb.table("landlords").insert(payload).execute()

    return res.data, subaccount_code


def initialize_ad_payment(client_name: str, ad_position: str, amount_ghs: float, start_date: str, end_date: str, destination_url: str, creative_url: str, email: str, callback_url: str, user_id: str = None):
    reference = f"AD-{uuid.uuid4().hex[:10].upper()}"

    ad_payload = {
        "business_name": client_name,
        "ad_slot": ad_position,
        "monthly_rate": float(amount_ghs),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "destination_url": destination_url,
        "creative_url": creative_url,
        "status": "pending_payment",
        "reference": reference,
    }
    if user_id: ad_payload["user_id"] = user_id
    if sb: sb.table("ads").insert(ad_payload).execute()

    paystack_res = initialize_paystack_payment(
        email=email,
        amount_in_main_unit=amount_ghs,
        callback_url=callback_url,
        metadata={
            "type": "advert_placement",
            "business_name": client_name,
            "ad_slot": ad_position,
            "reference": reference,
            "user_id": user_id
        }
    )
    return paystack_res, reference


def handle_paystack_callbacks():
    query_params = st.query_params
    ref_param = query_params.get("reference") or query_params.get("trxref")

    if not ref_param or not sb:
        return

    reference = str(ref_param).strip()
    processed_key = f"processed_paystack_ref_{reference}"

    if st.session_state.get(processed_key):
        try: st.query_params.clear()
        except Exception: pass
        return

    st.session_state[processed_key] = True
    user_id, user_email = get_active_user_info()

    # 1. ADVERT PAYMENT VERIFICATION
    if reference.startswith("AD-"):
        with st.spinner("Verifying Advert Payment with Paystack..."):
            verification = verify_paystack_payment(reference)
            if verification.get("status") and verification.get("data", {}).get("status") == "success":
                try:
                    sb.table("ads").update({"status": "paid"}).eq("reference", reference).execute()
                    clear_cache()
                    st.toast(f"✅ Advert Payment Verified! Ref: {reference}", icon="🎉")
                    st.success(f"✅ Payment for Advert (Ref: `{reference}`) verified successfully! Campaign activated.")
                except Exception as e:
                    logger.error(f"Error updating advert status: {e}")
                    st.error(f"Error updating advert status: {e}")
            else:
                st.error("❌ Advert payment verification failed or was cancelled.")

    # 2. PUBLIC PROPERTY LISTING PAYMENT VERIFICATION (GH₵ 50 / $5)
    elif reference.startswith("PROP-"):
        with st.spinner("Verifying Property Listing Payment with Paystack..."):
            verification = verify_paystack_payment(reference)
            if verification.get("status") and verification.get("data", {}).get("status") == "success":
                try:
                    sb.table("public_listings").update({"status": "paid"}).eq("reference", reference).execute()
                    clear_cache()
                    st.toast(f"✅ Property Listing Published Live! Ref: {reference}", icon="🏠")
                    st.success(f"✅ Payment for Property Listing (Ref: `{reference}`) verified! Listing is live on the public showcase.")
                except Exception as e:
                    logger.error(f"Error updating listing status: {e}")
                    st.error(f"Error updating listing status: {e}")
            else:
                st.error("❌ Property listing payment verification failed or was cancelled.")

    # 3. RENT PAYMENT VERIFICATION
    else:
        with st.spinner("Verifying Paystack Rent Payment status..."):
            verification = verify_paystack_payment(reference)
            if verification.get("status") and verification.get("data", {}).get("status") == "success":
                data = verification["data"]
                meta = data.get("metadata", {})
                try:
                    existing_check = sb.table("payments").select("id").ilike("notes", f"%{reference}%").execute()
                    if existing_check and existing_check.data:
                        st.info(f"ℹ️ Payment Ref `{reference}` was already recorded previously.")
                    else:
                        payload = {
                            "tenant_id": meta.get("tenant_id") if meta.get("tenant_id") else None,
                            "amount": data["amount"] / 100.0,
                            "payment_method": data.get("channel", "online_paystack"),
                            "notes": f"Paystack Ref: {reference} | Email: {data.get('customer', {}).get('email')}",
                            "payment_date": str(date.today()),
                            "status": "paid"
                        }
                        if user_id: payload["user_id"] = user_id
                        if user_email: payload["user_email"] = user_email

                        sb.table("payments").insert(payload).execute()
                        clear_cache()
                        st.toast("✅ Rent Payment credited!", icon="💳")
                        st.success(f"✅ Rent Payment of {fmt_money(data['amount']/100, data.get('currency'))} verified and credited!")
                except Exception as e:
                    logger.error(f"Error logging payment: {e}")
                    st.error(f"Error logging payment to database: {e}")
            else:
                st.error("❌ Payment verification failed or transaction was cancelled.")

    try: st.query_params.clear()
    except Exception: pass
