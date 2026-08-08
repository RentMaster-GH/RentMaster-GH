# components/kyc.py
import streamlit as st
import streamlit.components.v1 as components


def render_id_verification_widget(entity_type: str = "Tenant", key_prefix: str = "id_widget"):
    st.markdown(f"##### 🆔 {entity_type} Identity Verification (KYC)")
    st.markdown(
        f"""
        <div style="background-color: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px; padding: 1rem; margin-bottom: 1rem;">
            <h6 style="margin: 0 0 0.4rem 0; color: #0369a1; font-weight: 600;">📌 {entity_type} ID Verification Guidelines</h6>
            <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.85rem; color: #0c4a6e; line-height: 1.4;">
                <li><b>Accepted IDs:</b> Ghana Card / National ID, Passport, Driver's License, Voter ID.</li>
                <li><b>Quality Standard:</b> All 4 corners visible, no glare or blur. Text must be legible.</li>
                <li><b>Privacy Compliance:</b> Protected in accordance with the <i>Data Protection Act (Act 843)</i> / GDPR regulations.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

    capture_method = st.radio(
        "Choose ID Capture Method",
        ["📁 Drag & Drop File Upload", "📷 Live Camera Capture"],
        horizontal=True,
        key=f"{key_prefix}_capture_method"
    )

    uploaded_id_file = None
    if "Drag & Drop" in capture_method:
        uploaded_id_file = st.file_uploader(
            f"Drop {entity_type} ID document file here (PNG, JPG, JPEG, PDF)",
            type=["png", "jpg", "jpeg", "pdf"],
            key=f"{key_prefix}_file_dropzone"
        )
    else:
        st.info("📷 **Live Camera Stream Initializing:** Allow camera access in your browser if prompted. Align ID card inside frame and click 'Take Photo'.")
        
        uploaded_id_file = st.camera_input(
            f"Take photo of {entity_type} ID Card",
            key=f"{key_prefix}_camera_capture",
            help="Align ID card inside frame and click 'Take Photo'"
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
            setTimeout(autoStartCamera, 250);
            setTimeout(autoStartCamera, 600);
            </script>
            """,
            height=0,
            width=0
        )

    if uploaded_id_file:
        st.success("✅ Document captured successfully!")
        if hasattr(uploaded_id_file, "type") and "pdf" in str(uploaded_id_file.type):
            st.info("📄 PDF File Selected")
        else:
            st.image(uploaded_id_file, caption=f"Captured {entity_type} ID Preview", width=320)

    return uploaded_id_file
