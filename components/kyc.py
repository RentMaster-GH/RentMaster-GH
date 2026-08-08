# components/kyc.py
import streamlit as st
import streamlit.components.v1 as components


def render_id_verification_widget(entity_type: str = "Tenant", key_prefix: str = "id_widget"):
    """
    Renders ID Document Upload and Live Camera Selfie Photo Capture widget.
    Returns a tuple: (uploaded_id_file, selfie_file)
    """
    st.markdown(f"##### 🆔 {entity_type} Identity Verification (KYC)")
    st.markdown(
        f"""
        <div style="background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
            <h6 style="margin: 0 0 0.4rem 0; color: #0369a1; font-weight: 600;">📌 {entity_type} ID Verification Guidelines</h6>
            <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: #0c4a6e; line-height: 1.4;">
                <li><b>Accepted IDs:</b> Ghana Card / National ID, Passport, Driver's License, Voter ID.</li>
                <li><b>Quality Standard:</b> Clear, legible text, no blur or glare.</li>
                <li><b>Verification Process:</b> App Manager Review &rarr; Landlord Property Acceptance &rarr; Tenant Mutual Agreement.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown(f"**1. Upload {entity_type} ID Card**")
        uploaded_id_file = st.file_uploader(
            f"Upload {entity_type} ID Document (PNG, JPG, JPEG, PDF)",
            type=["png", "jpg", "jpeg", "pdf"],
            key=f"{key_prefix}_file_dropzone"
        )
        if uploaded_id_file:
            st.success("✅ ID Card document attached!")

    with c2:
        st.markdown(f"**2. Take Live Selfie Photo**")
        selfie_file = st.camera_input(
            f"Take live selfie of {entity_type}",
            key=f"{key_prefix}_selfie_camera",
            help="Align face inside camera frame and click 'Take Photo'"
        )

        components.html(
            """
            <script>
            function autoStartCamera() {
                const doc = window.parent.document;
                const buttons = doc.querySelectorAll('button');
                for (let btn of buttons) {
                    const txt = btn.innerText || btn.textContent || "";
                    if (txt.includes('Turn on camera') || txt.includes('Start camera') || txt.includes('Allow access')) {
                        btn.click();
                        break;
                    }
                }
            }
            autoStartCamera();
            setTimeout(autoStartCamera, 300);
            </script>
            """,
            height=0,
            width=0
        )
        if selfie_file:
            st.success("✅ Live selfie captured!")

    return uploaded_id_file, selfie_file
