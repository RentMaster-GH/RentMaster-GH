"""
RentMaster-GH - Direct Tenant-Landlord Chat & Video Calling Module
Supports real-time text chat and WebRTC HD Video Calling via Jitsi Meet.
"""
import streamlit as st
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
# MAIN CHAT & VIDEO CALL INTERFACE
# ---------------------------------------------------------------------------
def render_chat_interface(tenant_id, current_user_id, current_user_role="landlord", current_user_email="user@example.com", recipient_name="Tenant"):
    """
    Renders text chat thread and WebRTC HD video call room launcher.
    """
    st.markdown(f"### 💬 Communication Hub: {recipient_name}")
    
    # WebRTC Video Room Name
    video_room_id = f"RentMasterGH-Call-{str(tenant_id)[:8]}"
    jitsi_video_url = f"https://meet.jit.si/{video_room_id}"

    # 1. LIVE VIDEO CALL LAUNCHER BANNER
    with st.container(border=True):
        col_v1, col_v2 = st.columns([3, 1])
        with col_v1:
            st.markdown(f"📹 **HD Video Call Room:** `{video_room_id}`")
            st.caption("Click to launch a secure end-to-end encrypted video call with this tenant.")
        with col_v2:
            st.link_button("🎥 Start Video Call", jitsi_video_url, type="primary", use_container_width=True)

    st.divider()

    # 2. INSTANT TEXT CHAT MESSAGING THREAD
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
    st.caption("Select a prospective or actual tenant below to start a live chat or HD video call.")

    tenants = fetch_tenants(user_id, user_email) if 'fetch_tenants' in globals() else []

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

    # Render Active Chat and Video Call Interface
    render_chat_interface(
        tenant_id=selected_tenant_id,
        current_user_id=user_id,
        current_user_role="landlord",
        current_user_email=user_email,
        recipient_name=selected_tenant.get("name", "Tenant")
    )
