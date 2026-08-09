"""
RentMaster-GH - Direct Tenant-Landlord Instant In-App Video Calling & Chat Module
Supports embedded WebRTC HD Video Calls directly on the same screen with zero-lobby instant connection.
"""
import streamlit as st
import streamlit.components.v1 as components
import json
from datetime import datetime
from services.database import sb, fetch_tenants


def get_chat_messages(tenant_id):
    """Fetch chat history between landlord and tenant."""
    default_messages = [
        {"sender": "tenant", "sender_name": "Kwame Mensah", "message": "Hello Landlord, I have inspected the property condition photos and accepted them.", "time": "10:30 AM"},
        {"sender": "landlord", "sender_name": "Property Manager", "message": "Great Kwame! I have initiated the tenancy agreement. Please review and accept to unlock checkout.", "time": "10:32 AM"}
    ]

    if not sb:
        return st.session_state.get(f"chat_history_{tenant_id}", default_messages)

    try:
        res = sb.table("messages").select("*").eq("tenant_id", tenant_id).order("created_at", desc=False).execute()
        if res.data:
            return res.data
    except Exception:
        pass

    return st.session_state.get(f"chat_history_{tenant_id}", default_messages)


def save_chat_message(tenant_id, sender_role, sender_name, message_text):
    """Save new chat message."""
    new_msg = {
        "tenant_id": tenant_id,
        "sender": sender_role,
        "sender_name": sender_name,
        "message": message_text,
        "time": datetime.now().strftime("%I:%M %p"),
        "created_at": datetime.now().isoformat()
    }

    if sb:
        try:
            sb.table("messages").insert(new_msg).execute()
        except Exception:
            pass

    history_key = f"chat_history_{tenant_id}"
    if history_key not in st.session_state:
        st.session_state[history_key] = []
    st.session_state[history_key].append(new_msg)


# ---------------------------------------------------------------------------
# MAIN EMBEDDED IN-APP CHAT & INSTANT VIDEO CALL INTERFACE
# ---------------------------------------------------------------------------
def render_chat_interface(tenant_id, current_user_id, current_user_role="landlord", current_user_email="user@example.com", recipient_name="Tenant"):
    """
    Renders text chat thread and Embedded Instant Video Call directly on the same screen.
    """
    st.markdown(f"### 💬 Communication Hub: {recipient_name}")
    
    # Unique Call Room ID & Instant Launch Configuration
    video_room_id = f"RentMasterGH-Call-{str(tenant_id)[:8]}"
    
    # URL parameters for instant start (skips prejoin lobby page & turns camera/mic on instantly)
    instant_jitsi_url = (
        f"https://meet.jit.si/{video_room_id}"
        f"#config.prejoinPageEnabled=false"
        f"&config.startWithAudioMuted=false"
        f"&config.startWithVideoMuted=false"
        f"&config.disableDeepLinking=true"
    )

    call_state_key = f"active_call_{tenant_id}"
    is_call_active = st.session_state.get(call_state_key, False)

    # 1. EMBEDDED INSTANT VIDEO CALL SCREEN
    if is_call_active:
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 12px; border-radius: 12px; color: white; margin-bottom: 15px; border: 1px solid #334155;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 1.05rem; font-weight: bold; color: #4ade80;">🟢 LIVE HD VIDEO CALL &middot; {recipient_name}</span>
                    <span style="font-size: 0.85rem; color: #94a3b8;">Encrypted WebRTC Channel</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Embedded Video Frame on the Same Screen
        iframe_html = f"""
        <iframe 
            src="{instant_jitsi_url}" 
            allow="camera; microphone; display-capture; autoplay; clipboard-write" 
            style="width: 100%; height: 520px; border: 0px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3);"
        ></iframe>
        """
        components.html(iframe_html, height=530)

        # End Call Button
        if st.button("🔴 Hang Up / End Video Call", key=f"end_call_btn_{tenant_id}", type="primary", use_container_width=True):
            st.session_state[call_state_key] = False
            st.rerun()

        st.divider()

    else:
        # 2. START INSTANT VIDEO CALL BANNER
        with st.container(border=True):
            col_v1, col_v2 = st.columns([3, 1])
            with col_v1:
                st.markdown(f"📹 **Instant Direct HD Video Calling**")
                st.caption("Call starts immediately on this screen without opening new tabs or joining lobbies.")
            with col_v2:
                if st.button("🎥 Start Video Call Now", key=f"start_call_btn_{tenant_id}", type="primary", use_container_width=True):
                    st.session_state[call_state_key] = True
                    st.rerun()

        st.divider()

    # 3. INSTANT TEXT CHAT MESSAGING THREAD
    st.markdown("#### 💬 Direct Messages")
    messages = get_chat_messages(tenant_id)

    # Render Chat History Bubble Box
    chat_container = st.container(height=300, border=True)
    with chat_container:
        if not messages:
            st.info("No message history yet. Start the conversation below!")
        for msg in messages:
            is_me = msg.get("sender") == current_user_role
            avatar_emoji = "🏠" if msg.get("sender") == "landlord" else "👤"
            
            with st.chat_message("user" if is_me else "assistant", avatar=avatar_emoji):
                st.write(f"**{msg.get('sender_name', 'User')}** `{msg.get('time', '')}`")
                st.write(msg.get("message"))

    # Message Input Form
    with st.form(key=f"chat_send_form_{tenant_id}", clear_on_submit=True):
        col_in1, col_in2 = st.columns([4, 1])
        with col_in1:
            user_input = st.text_input("Type your message...", label_visibility="collapsed", placeholder="Type a message or inquiry...")
        with col_in2:
            send_btn = st.form_submit_button("Send 📤", type="primary", use_container_width=True)

        if send_btn and user_input:
            sender_display_name = "Landlord / Manager" if current_user_role == "landlord" else "Tenant"
            save_chat_message(tenant_id, current_user_role, sender_display_name, user_input)
            st.rerun()


# ---------------------------------------------------------------------------
# LANDLORD DEDICATED TENANT COMMUNICATION PORTAL
# ---------------------------------------------------------------------------
def render_landlord_communication_hub(user):
    """
    Dedicated Communication Hub tab for Landlords to select and talk to any tenant.
    """
    user_id = getattr(user, "id", "demo_landlord")
    user_email = getattr(user, "email", "landlord@example.com")

    st.markdown("## 📞 Landlord Direct Tenant Communication Portal")
    st.caption("Select a prospective or actual tenant below to start an instant in-app video call or text chat.")

    try:
        tenants = fetch_tenants(user_id, user_email)
    except Exception:
        tenants = []

    if not tenants:
        tenants = [
            {"id": "tenant_demo_1", "name": "Kwame Mensah (Prospective Tenant)", "email": "kwame@example.com"},
            {"id": "tenant_demo_2", "name": "Abena Osei (Active Tenant - Flat 2B)", "email": "abena@example.com"}
        ]

    tenant_options = {t["id"]: f"👤 {t['name']} ({t.get('email', 'No Email')})" for t in tenants}

    selected_tenant_id = st.selectbox(
        "Select Tenant to Contact *",
        options=list(tenant_options.keys()),
        format_func=lambda x: tenant_options[x]
    )

    selected_tenant = next((t for t in tenants if t["id"] == selected_tenant_id), tenants[0])

    st.divider()

    # Render Active Chat and Instant Video Call Interface
    render_chat_interface(
        tenant_id=selected_tenant_id,
        current_user_id=user_id,
        current_user_role="landlord",
        current_user_email=user_email,
        recipient_name=selected_tenant.get("name", "Tenant")
    )
