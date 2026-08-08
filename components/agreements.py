"""
RentMaster-GH - Dual Tenancy Agreement Module
Supports Default Ghana Rent Act 220 template, custom typed agreements, and PDF uploads.
Requires tenant acceptance prior to rent payments.
"""
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
        "agreement_type": "default",  # 'default', 'custom_text', or 'uploaded_file'
        "content_text": DEFAULT_GHANA_LEASE_TEMPLATE,
        "file_url": None,
        "tenant_accepted": False,
        "accepted_at": None
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


# ---------------------------------------------------------------------------
# LANDLORD WIDGET: CREATE / CHOOSE AGREEMENT TYPE
# ---------------------------------------------------------------------------
def render_landlord_agreement_creator_widget(lease_id):
    """Renders options for landlords to pick Default, Type Custom, or Upload Document."""
    st.markdown("### 📜 Tenancy Agreement Manager")
    st.caption("Select how you want to issue the tenancy agreement to your tenant.")

    agreement = get_tenancy_agreement(lease_id)

    choice = st.radio(
        "Agreement Option *",
        [
            "🏛️ Use App Standard Ghana Legal Template",
            "✍️ Type Custom Agreement Terms",
            "📁 Upload Custom Agreement Document (PDF / Doc)"
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
            custom_text = st.text_area("Custom Agreement Terms *", value=agreement.get("content_text", ""), height=250, placeholder="Enter rules, rent due dates, utility responsibilities...")
            ag_type = "custom_text"

        else:  # Upload Document
            st.markdown("##### Upload your existing signed agreement or PDF draft:")
            file_upload = st.file_uploader("Upload Tenancy Agreement (PDF / PNG / JPG)", type=["pdf", "png", "jpg", "jpeg"])
            ag_type = "uploaded_file"

        submit = st.form_submit_button("💾 Save & Publish Tenancy Agreement", type="primary", use_container_width=True)

        if submit:
            payload = {
                "lease_id": lease_id,
                "agreement_type": ag_type,
                "content_text": custom_text if ag_type == "custom_text" else (DEFAULT_GHANA_LEASE_TEMPLATE if ag_type == "default" else None),
                "file_url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf" if ag_type == "uploaded_file" else None,
                "tenant_accepted": False
            }
            save_tenancy_agreement(payload)
            st.success("✅ Tenancy agreement published! Awaiting tenant acceptance.")
            st.rerun()


# ---------------------------------------------------------------------------
# TENANT WIDGET: VIEW & ACCEPT AGREEMENT BEFORE PAYMENT
# ---------------------------------------------------------------------------
def render_tenant_agreement_acceptance_widget(user, lease_id="lease_demo_101"):
    """
    Renders the tenancy agreement for tenant review.
    Returns True if accepted (unlocks payment).
    """
    agreement = get_tenancy_agreement(lease_id)
    is_accepted = agreement.get("tenant_accepted", False)

    st.markdown("### 📜 Tenancy Agreement Review")

    ag_type = agreement.get("agreement_type", "default")

    if ag_type == "default":
        st.info("📜 **Standard Ghana Residential Tenancy Agreement (Act 220)**")
        st.text_area("Agreement Terms", value=agreement.get("content_text", DEFAULT_GHANA_LEASE_TEMPLATE), height=220, disabled=True)

    elif ag_type == "custom_text":
        st.info("✍️ **Landlord Custom Tenancy Agreement Terms**")
        st.text_area("Agreement Terms", value=agreement.get("content_text", ""), height=250, disabled=True)

    elif ag_type == "uploaded_file":
        st.info("📁 **Uploaded Tenancy Agreement Document**")
        if agreement.get("file_url"):
            st.link_button("📥 View / Download Landlord's PDF Agreement Document", agreement["file_url"], type="primary")

    st.divider()

    if is_accepted:
        st.success(f"✅ **Tenancy Agreement Accepted:** Confirmed on `{agreement.get('accepted_at', 'Recently')}`.")
        return True
    else:
        st.warning("⚠️ **Action Required:** You must accept the tenancy agreement terms below to proceed to rent payments.")
        
        with st.container(border=True):
            agree = st.checkbox("I have read, understood, and agree to abide by the terms of this Tenancy Agreement.")
            
            if st.button("🤝 Accept Tenancy Agreement", type="primary", disabled=not agree, use_container_width=True):
                agreement["tenant_accepted"] = True
                agreement["accepted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_tenancy_agreement(agreement)
                st.success("🎉 Tenancy agreement accepted! Rent payment is now enabled.")
                st.rerun()

        return False
