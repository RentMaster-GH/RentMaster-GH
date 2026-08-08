"""
RentMaster-GH - Dual KYC & 48-Hour Landlord Acceptance Engine
Handles Tenant & Landlord ID submissions, Live Camera/Upload capture,
App Manager Verification, and 48-Hour Counterparty Agreement Approvals.
"""
import streamlit as st
import io
from datetime import datetime, timedelta
from services.database import sb


# ---------------------------------------------------------------------------
# KYC STATUS HELPERS & DATABASE CALLS
# ---------------------------------------------------------------------------
def get_kyc_record(user_id):
    """Fetch KYC record for a specific user from Supabase."""
    if not sb:
        return st.session_state.get(f"kyc_record_{user_id}", None)
    try:
        res = sb.table("kyc_verifications").select("*").eq("user_id", user_id).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return st.session_state.get(f"kyc_record_{user_id}", None)


def save_kyc_record(record_data):
    """Save or update KYC record in Supabase / Session State fallback."""
    record_data["updated_at"] = datetime.now().isoformat()
    if sb:
        try:
            sb.table("kyc_verifications").upsert(record_data).execute()
        except Exception:
            pass
    # Local fallback storage
    st.session_state[f"kyc_record_{record_data['user_id']}"] = record_data


# ---------------------------------------------------------------------------
# PAYMENT ELIGIBILITY CHECK (Manager Approved + Landlord 2-Day Acceptance)
# ---------------------------------------------------------------------------
def check_tenant_kyc_payment_eligibility(tenant_data):
    """
    Checks if tenant is eligible to make rent payments:
    1. App Manager Approved = True
    2. Landlord Accepted = True (within 2 days of manager approval)
    """
    if not tenant_data:
        return False, "Unlinked tenant profile."

    status = tenant_data.get("verification_status", "unverified")
    landlord_accepted = tenant_data.get("landlord_acceptance", False)
    mgr_approved_at_str = tenant_data.get("manager_approved_at")

    # Check Manager Approval
    if status != "manager_approved" and not tenant_data.get("manager_approved", False):
        return False, "⏳ App Manager KYC verification is pending."

    # Check Landlord Acceptance & 2-Day Deadline
    if not landlord_accepted:
        if mgr_approved_at_str:
            try:
                approved_time = datetime.fromisoformat(mgr_approved_at_str)
                deadline = approved_time + timedelta(days=2)
                now = datetime.now()

                if now > deadline:
                    return False, "⏰ Landlord 2-day acceptance period has expired. Please contact support."
                else:
                    time_left = deadline - now
                    hours_left = int(time_left.total_seconds() // 3600)
                    return False, f"⏳ Awaiting Landlord Acceptance ({hours_left} hours remaining in 2-day window)."
            except Exception:
                pass
        return False, "⏳ Awaiting Landlord Acceptance (within 2-day window of App Manager approval)."

    return True, "✅ Fully Verified & Accepted!"


# ---------------------------------------------------------------------------
# MAIN PUBLIC WIDGET EXPORT
# ---------------------------------------------------------------------------
def render_id_verification_widget(user=None, entity_type="Tenant", role="tenant", key_prefix="kyc", counterparty_id=None):
    """
    Main widget exported for tenant_portal.py and landlord dashboards.
    """
    user_id = getattr(user, "id", "demo_user") if user else "demo_user"
    user_email = getattr(user, "email", "user@example.com") if user else "user@example.com"
    target_role = entity_type.lower() if entity_type else role

    st.markdown(f"### 🆔 {entity_type} Identity Verification (KYC)")

    with st.expander(f"📌 {entity_type} ID Verification Guidelines", expanded=True):
        st.markdown(
            """
            * **Accepted IDs:** National ID, Passport, Driver's License, Voter ID.
            * **Quality Standard:** Clear, legible text, no blur or glare.
            * **Verification Process:** 
              1. **App Manager Review** (Document Audit & Live Selfie Audit)
              2. **Landlord Property Acceptance** (Must accept within **2 days / 48 hours** of App Manager approval)
              3. **Mutual Tenancy Agreement Completed**
            """
        )

    record = get_kyc_record(user_id)
    current_status = record.get("status", "unverified") if record else "unverified"

    # Status Badges Display
    if current_status == "unverified":
        st.warning("⚠️ **Status: Unverified.** Complete your identity verification below to unlock feature access.")
    elif current_status in ["pending_manager", "pending_manager_approval"]:
        st.info("⏳ **Status: Submitted for Review.** Your documents have been received and are pending App Manager approval.")
    elif current_status == "pending_counterparty":
        st.info("⏳ **Status: Manager Approved!** Awaiting agreement confirmation from your counterparty within the 2-day window.")
    elif current_status == "approved":
        st.success("✅ **Status: Fully Verified & Approved!** You are cleared for payments and lease agreements.")
    elif current_status == "rejected":
        st.error(f"❌ **Status: Rejected.** Reason: {record.get('rejection_reason', 'Information mismatch. Please re-submit.')}")

    st.divider()

    # Submission Form (If Unverified or Rejected)
    if current_status in ["unverified", "rejected"]:
        _render_kyc_submission_form(user_id, user_email, target_role, counterparty_id, key_prefix)

    # View Submitted Details
    elif record:
        with st.expander("📄 View Submitted KYC Details", expanded=(current_status != "approved")):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Full Name:** {record.get('full_name')}")
                st.write(f"**ID Type:** {record.get('id_type')}")
                st.write(f"**ID Number:** {record.get('id_number')}")
                st.write(f"**Phone Number:** {record.get('phone_number')}")
            with c2:
                st.write(f"**Submission Date:** {record.get('created_at', 'N/A')[:10]}")
                st.write(f"**Manager Verified:** {'Yes ✅' if record.get('manager_approved') else 'No ⏳'}")
                st.write(f"**Counterparty Accepted:** {'Yes ✅' if record.get('counterparty_approved') else 'No ⏳'}")

    return current_status == "approved"


# ---------------------------------------------------------------------------
# SUBMISSION FORM (Camera + Document Upload)
# ---------------------------------------------------------------------------
def _render_kyc_submission_form(user_id, user_email, role, counterparty_id, key_prefix="kyc"):
    st.markdown("#### 📝 Step 1: Personal & ID Information")
    
    with st.form(key=f"kyc_form_{key_prefix}_{user_id}"):
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Official Name (Matches ID) *", placeholder="e.g. Kwame Mensah")
            id_type = st.selectbox("Accepted ID Document Type *", ["National ID", "Passport", "Driver's License", "Voter ID"])
            id_number = st.text_input("ID Number *", placeholder="e.g. 123456789")
        with col2:
            phone_number = st.text_input("Phone Number *", placeholder="+233 20 000 0000")
            address = st.text_input("Digital Address / Residential Address", placeholder="e.g. GA-123-4567")

        st.markdown("#### 📸 Step 2: Photo ID Document & Live Camera Selfie Capture")
        cap_tab1, cap_tab2 = st.tabs(["📷 Take Live Selfie Photo", "📁 Upload ID Document Image"])

        photo_camera = None
        photo_upload = None

        with cap_tab1:
            photo_camera = st.camera_input("Take a clear live selfie holding your ID next to your face *", key=f"cam_{key_prefix}_{user_id}")

        with cap_tab2:
            photo_upload = st.file_uploader("Upload clear photo of ID Document (PNG, JPG, PDF) *", type=["jpg", "jpeg", "png", "pdf"], key=f"file_{key_prefix}_{user_id}")

        consent = st.checkbox("I confirm that the submitted information and document photos are accurate and belong to me.")

        submit_btn = st.form_submit_button("📤 Submit for App Manager Verification", type="primary", use_container_width=True)

        if submit_btn:
            if not full_name or not id_number or not phone_number:
                st.error("Please fill in all required personal information fields marked with *.")
            elif not consent:
                st.error("You must agree to the accuracy confirmation checkbox.")
            elif not photo_camera and not photo_upload:
                st.error("Please capture a live camera photo or upload an ID document image.")
            else:
                record_payload = {
                    "user_id": user_id,
                    "email": user_email,
                    "role": role,
                    "full_name": full_name,
                    "id_type": id_type,
                    "id_number": id_number,
                    "phone_number": phone_number,
                    "address": address,
                    "counterparty_id": counterparty_id,
                    "status": "pending_manager",
                    "manager_approved": False,
                    "counterparty_approved": False,
                    "created_at": datetime.now().isoformat()
                }
                save_kyc_record(record_payload)
                
                # Update Supabase table status
                if sb:
                    try:
                        table_name = "tenants" if role == "tenant" else "landlords"
                        sb.table(table_name).update({
                            "verification_status": "pending_manager_approval",
                            "id_number": id_number,
                            "id_type": id_type
                        }).eq("email", user_email).execute()
                    except Exception:
                        pass

                st.success("✅ KYC details submitted successfully! Awaiting App Manager review.")
                st.rerun()


# ---------------------------------------------------------------------------
# APP MANAGER REVIEW PANEL (Renders in Settings / Manager View)
# ---------------------------------------------------------------------------
def render_manager_kyc_approval_panel():
    """Renders the App Manager review table to approve or reject pending submissions."""
    st.markdown("### 🛡️ App Manager KYC Verification Queue")
    
    records = []
    if sb:
        try:
            res = sb.table("kyc_verifications").select("*").eq("status", "pending_manager").execute()
            records = res.data or []
        except Exception:
            pass

    if not records:
        st.info("🎉 No pending KYC verification requests awaiting App Manager approval.")
        return

    for rec in records:
        with st.expander(f"📌 {rec.get('role', 'User').title()}: {rec.get('full_name')} ({rec.get('email')})", expanded=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**ID Type:** {rec.get('id_type')} | **ID Number:** {rec.get('id_number')}")
                st.write(f"**Phone:** {rec.get('phone_number')} | **Address:** {rec.get('address')}")
            with col2:
                c_app, c_rej = st.columns(2)
                with c_app:
                    if st.button("Approve ✅", key=f"mgr_app_{rec['user_id']}", type="primary"):
                        rec["status"] = "pending_counterparty"
                        rec["manager_approved"] = True
                        rec["manager_approved_at"] = datetime.now().isoformat()
                        save_kyc_record(rec)
                        
                        if sb:
                            try:
                                table_name = "tenants" if rec.get("role") == "tenant" else "landlords"
                                sb.table(table_name).update({
                                    "verification_status": "manager_approved",
                                    "manager_approved": True,
                                    "manager_approved_at": datetime.now().isoformat()
                                }).eq("email", rec["email"]).execute()
                            except Exception:
                                pass

                        st.success("Approved by Manager! 2-day Landlord acceptance timer initiated.")
                        st.rerun()
                with c_rej:
                    if st.button("Reject ❌", key=f"mgr_rej_{rec['user_id']}"):
                        rec["status"] = "rejected"
                        rec["rejection_reason"] = "Information did not match official database."
                        save_kyc_record(rec)
                        st.error("Rejected.")
                        st.rerun()


# ---------------------------------------------------------------------------
# COUNTERPARTY AGREEMENT WIDGET
# ---------------------------------------------------------------------------
def render_counterparty_acceptance_widget(current_user_id, target_user_id, relationship_type="tenant_accepting_landlord"):
    """Rendered when Landlord or Tenant needs to accept counterparty's verified profile."""
    target_record = get_kyc_record(target_user_id)

    if not target_record:
        st.info("ℹ️ Counterparty profile verification is pending.")
        return False

    status = target_record.get("status")

    if status == "pending_counterparty":
        st.warning("⚠️ Action Required: Please review and accept the counterparty's verified profile to proceed.")
        
        with st.container(border=True):
            st.markdown(f"#### 📜 Verified Profile: {target_record.get('full_name')}")
            st.write(f"**ID Type:** {target_record.get('id_type')}")
            st.write(f"**Phone Number:** {target_record.get('phone_number')}")
            st.caption("✅ Approved by App Manager")

            agree = st.checkbox(f"I acknowledge and agree to transact/rent with {target_record.get('full_name')}.")
            
            if st.button("Confirm & Accept Agreement", type="primary", disabled=not agree):
                target_record["status"] = "approved"
                target_record["counterparty_approved"] = True
                save_kyc_record(target_record)
                st.success("🎉 Agreement finalized! Transaction path is now unlocked.")
                st.rerun()
        return False

    elif status == "approved":
        st.success("✅ Rental Agreement & Profile mutual verification is active.")
        return True

    return False
