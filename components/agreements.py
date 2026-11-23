"""
RentMaster-GH - Dual Tenancy Agreement Module
Supports Default Ghana Rent Act 220 template, custom typed agreements, and real PDF/Image uploads
with SHA-256 tenant e-signature audit stamps.
"""
import base64
import hashlib
import streamlit as st
from datetime import datetime
from services.database import sb

DEFAULT_GHANA_LEASE_TEMPLATE = """
📋 REPUBLIC OF GHANA RESIDENTIAL TENANCY AGREEMENT
(Under the Rent Act, 1963 - Act 220)

1. PREMISES & PARTIES:
   This Tenancy Agreement is made between the Landlord and Tenant for the designated rental unit.

2. RENT & PAYMENTS:
   - Rent shall be paid through the RentMaster-GH digital platform or approved channels.
   - Payments may be made in full or through authorized flexible installments.
   - Maintenance reserve/security deposit is held for repairs and unit upkeep.

3. OBLIGATIONS OF THE TENANT:
   - To keep the interior of the premises in good and tenantable condition.
   - Not to assign, sublet, or part with possession of the premises without written consent.
   - To use the premises solely for private residential purposes.

4. OBLIGATIONS OF THE LANDLORD:
   - To ensure the tenant enjoys quiet possession without unlawful interruption.
   - To maintain structural integrity and external fixtures of the property.

5. GOVERNING LAW:
   This agreement is subject to the Rent Act of Ghana (Act 220) and Rent Control Department regulations.
"""


def get_tenancy_agreement(lease_id):
    """Fetch agreement details for a lease."""
    default_record = {
        "lease_id": lease_id,
        "agreement_type": "default",
        "content_text": DEFAULT_GHANA_LEASE_TEMPLATE,
        "file_url": None,
        "file_name": None,
        "tenant_accepted": False,
        "accepted_at": None,
        "accepted_by_name": None,
        "acceptance_hash": None,
    }

    if not sb:
        return st.session_state.get(f"agreement_{lease_id}", default_record)

    try:
        res = sb.table("tenancy_agreements").select("*").eq("lease_id", lease_id).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass

    return st.session_state.get(f"agreement_{lease_id}", default_record)


def save_tenancy_agreement(agreement_data):
    """Save agreement to DB or Session State."""
    agreement_data["updated_at"] = datetime.now().isoformat()
    if sb:
        try:
            sb.table("tenancy_agreements").upsert(agreement_data).execute()
        except Exception:
            pass

    st.session_state[f"agreement_{agreement_data['lease_id']}"] = agreement_data


def render_landlord_agreement_creator_widget(lease_id):
    """Renders options for landlords to pick Default, Type Custom, or Upload Real Document."""
    st.markdown("### 📜 Tenancy Agreement Manager")
    st.caption("Select how you want to issue the tenancy agreement to your tenant.")

    agreement = get_tenancy_agreement(lease_id)

    choice = st.radio(
        "Agreement Option *",
        [
            "🏛️ Use App Standard Ghana Legal Template",
            "✍️ Type Custom Agreement Terms",
            "📁 Upload Custom Agreement Document (PDF / Image)"
        ],
        key=f"agreement_choice_{lease_id}"
    )

    with st.form(key=f"agreement_form_{lease_id}"):
        custom_text = None
        file_upload = None

        if "Standard Ghana" in choice:
            st.info("The system will attach the standard Ghana Rent Act 220 Residential Tenancy Agreement.")
            st.text_area("Preview Standard Template Terms", value=DEFAULT_GHANA_LEASE_TEMPLATE, height=200, disabled=True)
            ag_type = "default"

        elif "Type Custom" in choice:
            st.markdown("##### Type your customized rules, covenants, and payment terms below:")
            custom_text = st.text_area("Custom Agreement Terms *", value=agreement.get("content_text") or "", height=250, placeholder="Enter rules, rent due dates, utility responsibilities...")
            ag_type = "custom_text"

        else:
            st.markdown("##### Upload your existing signed agreement or PDF draft:")
            file_upload = st.file_uploader("Upload Tenancy Agreement (PDF / PNG / JPG)", type=["pdf", "png", "jpg", "jpeg"])
            ag_type = "uploaded_file"

        submit = st.form_submit_button("💾 Save & Publish Tenancy Agreement", type="primary", use_container_width=True)

        if submit:
            if ag_type == "custom_text" and not (custom_text or "").strip():
                st.error("❌ Please enter your custom tenancy agreement terms before publishing.")
                return
            if ag_type == "uploaded_file" and file_upload is None:
                st.error("❌ Please select a PDF or image file to upload before publishing.")
                return

            encoded_url = None
            uploaded_name = None
            if ag_type == "uploaded_file" and file_upload is not None:
                raw_bytes = file_upload.getvalue()
                mime_type = getattr(file_upload, "type", None) or "application/pdf"
                uploaded_name = getattr(file_upload, "name", f"Tenancy_Agreement_{lease_id}.pdf")
                encoded_url = f"data:{mime_type};base64,{base64.b64encode(raw_bytes).decode('ascii')}"

            payload = {
                "lease_id": lease_id,
                "agreement_type": ag_type,
                "content_text": custom_text.strip() if ag_type == "custom_text" else (DEFAULT_GHANA_LEASE_TEMPLATE if ag_type == "default" else None),
                "file_url": encoded_url,
                "file_name": uploaded_name,
                "tenant_accepted": False,
                "accepted_at": None,
                "accepted_by_name": None,
                "acceptance_hash": None,
            }
            save_tenancy_agreement(payload)
            st.success("✅ Tenancy agreement published! Awaiting tenant digital signature.")
            st.rerun()


def render_tenant_agreement_acceptance_widget(user, lease_id="lease_demo_101"):
    """Renders tenancy agreement for tenant review and SHA-256 digital signature."""
    agreement = get_tenancy_agreement(lease_id)
    is_accepted = agreement.get("tenant_accepted", False)

    st.markdown("### 📜 Tenancy Agreement Review")
    ag_type = agreement.get("agreement_type", "default")

    if ag_type == "default":
        st.info("📜 **Standard Ghana Residential Tenancy Agreement (Act 220)**")
        st.text_area("Agreement Terms", value=agreement.get("content_text") or DEFAULT_GHANA_LEASE_TEMPLATE, height=220, disabled=True)

    elif ag_type == "custom_text":
        st.info("✍️ **Landlord Custom Tenancy Agreement Terms**")
        st.text_area("Agreement Terms", value=agreement.get("content_text") or "", height=250, disabled=True)

    elif ag_type == "uploaded_file":
        st.info("📁 **Uploaded Tenancy Agreement Document**")
        f_url = str(agreement.get("file_url") or "")
        if f_url.startswith("data:") and ";base64," in f_url:
            header_part, b64_part = f_url.split(";base64,", 1)
            mime_part = header_part.replace("data:", "")
            file_bytes = base64.b64decode(b64_part)
            fname = agreement.get("file_name") or f"Tenancy_Agreement_{lease_id}.pdf"
            if mime_part.startswith("image/"):
                st.image(file_bytes, caption=fname, use_container_width=True)
            st.download_button("📥 Download Landlord's Agreement Document", data=file_bytes, file_name=fname, mime=mime_part, type="primary", key=f"dl_ag_{lease_id}")
        elif f_url:
            st.link_button("📥 View / Download Landlord's PDF Agreement Document", f_url, type="primary")

    st.divider()

    if is_accepted:
        signer = agreement.get("accepted_by_name") or getattr(user, "email", "Tenant")
        sig_hash = agreement.get("acceptance_hash") or "VERIFIED"
        st.success(f"✅ **Tenancy Agreement Digitally Signed** by **{signer}** on `{agreement.get('accepted_at', 'Recently')}` (Sig: `{sig_hash[:16]}`).")
        return True

    st.warning("⚠️ **Action Required:** You must review and digitally sign the tenancy agreement below before making rent payments.")
    with st.container(border=True):
        default_name = getattr(user, "full_name", None) or getattr(user, "email", "").split("@")[0]
        sig_name = st.text_input("Type Your Full Legal Name as Digital Signature *", value=default_name, key=f"sig_name_{lease_id}")
        agree = st.checkbox("I have read, understood, and agree to abide by the terms of this Tenancy Agreement.", key=f"chk_ag_{lease_id}")

        if st.button("🤝 Sign & Accept Tenancy Agreement", type="primary", disabled=not (agree and sig_name.strip()), use_container_width=True, key=f"btn_ag_{lease_id}"):
            accepted_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            tenant_email = getattr(user, "email", "tenant@example.com")
            raw_sig = f"{lease_id}|{sig_name.strip()}|{tenant_email}|{accepted_ts}"
            sig_digest = hashlib.sha256(raw_sig.encode("utf-8")).hexdigest()

            agreement["tenant_accepted"] = True
            agreement["accepted_at"] = accepted_ts
            agreement["accepted_by_name"] = sig_name.strip()
            agreement["accepted_by_email"] = tenant_email
            agreement["acceptance_hash"] = sig_digest
            save_tenancy_agreement(agreement)
            st.success("🎉 Tenancy agreement digitally signed! Rent payment is now enabled.")
            st.rerun()

    return False
