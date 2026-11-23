"""
RentMaster-GH - Pre-Move-In Property Condition Portal
Landlords upload real condition photos; Tenants inspect and accept prior to rent payments.
"""
import base64
import streamlit as st
from datetime import datetime
from services.database import sb


def get_property_condition_report(property_id):
    """Fetch property condition photos & status from Supabase / Session state."""
    default_report = {
        "property_id": property_id,
        "landlord_notes": "Property cleaned, freshly painted, air conditioning and plumbing fully functional.",
        "photos": [
            {"title": "Living Room & AC", "url": "https://unsplash.com"},
            {"title": "Kitchen & Cabinets", "url": "https://unsplash.com"},
            {"title": "Bathroom & Plumbing", "url": "https://unsplash.com"}
        ],
        "tenant_accepted": False,
        "accepted_at": None,
    }

    if not sb:
        return st.session_state.get(f"condition_report_{property_id}", default_report)

    try:
        res = sb.table("property_conditions").select("*").eq("property_id", property_id).execute()
        if res.data:
            return res.data
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


def _render_condition_image(url_or_data, caption):
    s = str(url_or_data or "")
    if s.startswith("data:") and ";base64," in s:
        _, b64 = s.split(";base64,", 1)
        st.image(base64.b64decode(b64), caption=caption, use_container_width=True)
    elif s:
        st.image(s, caption=caption, use_container_width=True)


def render_landlord_condition_upload_widget(property_id):
    """Renders real photo upload form and gallery manager for Landlords."""
    st.markdown("### 📸 Pre-Move-In Property Condition Report")
    st.caption("Document the actual state of the property with real photos before your tenant inspects and accepts it.")

    report = get_property_condition_report(property_id)

    with st.expander("➕ Upload New Condition Photos & Notes", expanded=True):
        with st.form(key=f"landlord_cond_form_{property_id}", clear_on_submit=True):
            photo_title = st.text_input("Area / Room Title *", placeholder="e.g., Master Bedroom, ECG Prepaid Meter, Kitchen Sink")
            photo_file = st.file_uploader("Upload Clear Photo *", type=["jpg", "jpeg", "png", "webp"])
            condition_notes = st.text_area("Landlord Condition Notes", value=report.get("landlord_notes", ""), placeholder="Describe any existing features or notes...")

            submit = st.form_submit_button("📤 Publish Condition Photo to Tenant", type="primary", use_container_width=True)

            if submit:
                if not photo_title.strip() or not photo_file:
                    st.error("Please enter a room title and select an image file.")
                else:
                    raw = photo_file.getvalue()
                    mime = getattr(photo_file, "type", None) or "image/jpeg"
                    data_uri = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
                    new_photo = {
                        "title": photo_title.strip(),
                        "url": data_uri,
                        "uploaded_at": datetime.now().strftime("%Y-%m-%d"),
                    }
                    report.setdefault("photos", []).append(new_photo)
                    report["landlord_notes"] = condition_notes
                    report["tenant_accepted"] = False
                    save_property_condition_report(report)
                    st.success(f"✅ Real photo '{photo_title.strip()}' published successfully!")
                    st.rerun()

    st.markdown("#### 🖼️ Published Property Photos")
    photos = report.get("photos", [])
    if photos:
        cols = st.columns(min(3, len(photos)))
        for idx, photo in enumerate(photos):
            with cols[idx % 3]:
                _render_condition_image(photo.get("url"), photo.get("title", f"Photo {idx+1}"))
                if st.button("🗑️ Remove", key=f"del_cond_photo_{property_id}_{idx}", use_container_width=True):
                    report["photos"].pop(idx)
                    save_property_condition_report(report)
                    st.rerun()
    else:
        st.info("No condition photos uploaded for this property yet.")


def render_tenant_condition_approval_widget(user, property_id="demo_prop_1"):
    """Renders the Property Inspection gallery for tenants."""
    report = get_property_condition_report(property_id)
    is_accepted = report.get("tenant_accepted", False)

    st.markdown("### 🏘️ Property State & Pre-Move-In Inspection")
    st.caption("Review the landlord's uploaded photos depicting the current condition of the unit before making your rent payment.")

    photos = report.get("photos", [])
    if photos:
        st.markdown("#### 📸 Property Photos")
        p_cols = st.columns(min(3, len(photos)))
        for idx, photo in enumerate(photos):
            with p_cols[idx % 3]:
                _render_condition_image(photo.get("url"), photo.get("title", f"Photo {idx+1}"))

    if report.get("landlord_notes"):
        st.info(f"💬 **Landlord's Note on Property Condition:** {report['landlord_notes']}")

    st.divider()

    if is_accepted:
        st.success(f"✅ **Property Condition Accepted:** You inspected and agreed to the property state on `{report.get('accepted_at', 'Recently')}`.")
        return True

    st.warning("⚠️ **Action Required:** You must inspect and accept the property state before proceeding to make rent payments.")
    with st.container(border=True):
        agree_cb = st.checkbox("I have reviewed all property photos above and agree to accept the unit in its current state.", key=f"cond_chk_{property_id}")
        if st.button("🤝 Accept Property Condition & Unlock Rent Payment", type="primary", disabled=not agree_cb, use_container_width=True, key=f"cond_btn_{property_id}"):
            report["tenant_accepted"] = True
            report["accepted_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_property_condition_report(report)
            st.success("🎉 Property condition accepted! Rent Payment Portal is now unlocked.")
            st.rerun()

    return False
