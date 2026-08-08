"""
RentMaster-GH - Pre-Move-In Property Condition Portal
Landlords upload condition photos; Tenants inspect and accept prior to rent payments.
"""
import streamlit as st
import io
from datetime import datetime
from services.database import sb


def get_property_condition_report(property_id):
    """Fetch property condition photos & status from Supabase / Session state."""
    default_report = {
        "property_id": property_id,
        "landlord_notes": "Property cleaned, freshly painted, air conditioning and plumbing fully functional.",
        "photos": [
            {"title": "Living Room & AC", "url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=600"},
            {"title": "Kitchen & Cabinets", "url": "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=600"},
            {"title": "Bathroom & Plumbing", "url": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=600"}
        ],
        "tenant_accepted": False,
        "accepted_at": None
    }

    if not sb:
        return st.session_state.get(f"condition_report_{property_id}", default_report)

    try:
        res = sb.table("property_conditions").select("*").eq("property_id", property_id).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass

    return st.session_state.get(f"condition_report_{property_id}", default_report)


def save_property_condition_report(report_data):
    """Save condition report to DB/State."""
    report_data["updated_at"] = datetime.now().isoformat()
    if sb:
        try:
            sb.table("property_conditions").upsert(report_data).execute()
        except Exception:
            pass

    st.session_state[f"condition_report_{report_data['property_id']}"] = report_data


# ---------------------------------------------------------------------------
# LANDLORD WIDGET: UPLOAD CONDITION PHOTOS
# ---------------------------------------------------------------------------
def render_landlord_condition_upload_widget(property_id):
    """Renders photo upload form for Landlords to document property state."""
    st.markdown("### 📸 Pre-Move-In Property Condition Report")
    st.caption("Document the state of the property with photos before your tenant inspects and accepts it.")

    report = get_property_condition_report(property_id)

    with st.expander("➕ Upload New Condition Photos & Notes", expanded=True):
        with st.form(key=f"landlord_cond_form_{property_id}", clear_on_submit=True):
            photo_title = st.text_input("Area / Room Title *", placeholder="e.g., Master Bedroom, Electric Meter, Kitchen Sink")
            photo_file = st.file_uploader("Upload Clear Photo *", type=["jpg", "jpeg", "png"])
            condition_notes = st.text_area("Landlord Condition Notes", value=report.get("landlord_notes", ""), placeholder="Describe any existing features or notes...")

            submit = st.form_submit_button("📤 Publish Condition Photos to Tenant", type="primary", use_container_width=True)

            if submit:
                if not photo_title or not photo_file:
                    st.error("Please enter a room title and select an image file.")
                else:
                    # Simulated image URL upload
                    new_photo = {
                        "title": photo_title,
                        "url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=600",
                        "uploaded_at": datetime.now().strftime("%Y-%m-%d")
                    }
                    report["photos"].append(new_photo)
                    report["landlord_notes"] = condition_notes
                    save_property_condition_report(report)
                    st.success(f"✅ Photo '{photo_title}' published successfully!")
                    st.rerun()

    # View existing uploaded photos
    st.markdown("#### 🖼️ Published Property Photos")
    photos = report.get("photos", [])
    if photos:
        cols = st.columns(min(3, len(photos)))
        for idx, photo in enumerate(photos):
            with cols[idx % 3]:
                st.image(photo["url"], caption=photo["title"], use_container_width=True)
    else:
        st.info("No condition photos uploaded for this property yet.")


# ---------------------------------------------------------------------------
# TENANT WIDGET: INSPECT & ACCEPT CONDITION BEFORE PAYING
# ---------------------------------------------------------------------------
def render_tenant_condition_approval_widget(user, property_id="demo_prop_1"):
    """
    Renders the Property Inspection gallery for tenants.
    Returns True if tenant has accepted condition, unlocking the payment button.
    """
    report = get_property_condition_report(property_id)
    is_accepted = report.get("tenant_accepted", False)

    st.markdown("### 🏘️ Property State & Pre-Move-In Inspection")
    st.caption("Review the landlord's uploaded photos depicting the current condition of the unit before making your rent payment.")

    # Display Photos in Gallery Grid
    photos = report.get("photos", [])
    if photos:
        st.markdown("#### 📸 Property Photos")
        p_cols = st.columns(3)
        for idx, photo in enumerate(photos):
            with p_cols[idx % 3]:
                st.image(photo["url"], caption=photo["title"], use_container_width=True)
    
    if report.get("landlord_notes"):
        st.info(f"💬 **Landlord's Note on Property Condition:** {report['landlord_notes']}")

    st.divider()

    # Acceptance Checkbox & Lock
    if is_accepted:
        st.success(f"✅ **Property Condition Accepted:** You inspected and agreed to the property state on `{report.get('accepted_at', 'Recently')}`.")
        return True
    else:
        st.warning("⚠️ **Action Required:** You must inspect and accept the property state before proceeding to make rent payments.")
        
        with st.container(border=True):
            agree_cb = st.checkbox("I have reviewed all property photos above and agree to accept the unit in its current state.")
            
            if st.button("🤝 Accept Property Condition & Unlock Rent Payment", type="primary", disabled=not agree_cb, use_container_width=True):
                report["tenant_accepted"] = True
                report["accepted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_property_condition_report(report)
                st.success("🎉 Property condition accepted! Rent Payment Portal is now unlocked.")
                st.rerun()
        
        return False
