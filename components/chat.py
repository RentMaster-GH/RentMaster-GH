# components/chat.py
import streamlit as st
import streamlit.components.v1 as components
from services.helpers import fmt_date
from services.database import sb


def fetch_chat_messages(tenant_id: str):
    """
    Fetches chat message history for a specific tenancy file.
    """
    if not sb or not tenant_id:
        return []
    try:
        res = sb.table("chat_messages").select("*").eq("tenant_id", tenant_id).order("created_at", ascending=True).execute()
        return res.data or []
    except Exception:
        return []


def send_chat_message(tenant_id: str, sender_id: str, sender_role: str, sender_email: str, message_text: str):
    """
    Inserts a new text message into the chat database.
    """
    if not sb or not message_text.strip():
        return False
    try:
        sb.table("chat_messages").insert({
            "tenant_id": tenant_id,
            "sender_id": sender_id,
            "sender_role": sender_role,
            "sender_email": sender_email,
            "message": message_text.strip(),
        }).execute()
        return True
    except Exception as e:
        st.error(f"Failed to send message: {e}")
        return False


def render_chat_interface(tenant_id: str, current_user_id: str, current_user_role: str, current_user_email: str, recipient_name: str = "Property Manager"):
    """
    Renders text messaging bubbles and embedded WebRTC Video Call room.
    """
    st.markdown(f"#### 💬 Direct Communication Hub ({recipient_name})")

    tab_chat, tab_video = st.tabs(["💬 Text Messages", "📹 HD Video & Audio Call"])

    # TAB 1: TEXT MESSAGING
    with tab_chat:
        messages = fetch_chat_messages(tenant_id)

        # Chat Bubble Container
        with st.container(height=320, border=True):
            if not messages:
                st.info("👋 No messages yet. Send a text message below to start communicating!")
            else:
                for msg in messages:
                    is_me = (msg.get("sender_id") == current_user_id) or (msg.get("sender_role") == current_user_role)
                    align = "right" if is_me else "left"
                    bg_color = "#e0f2fe" if is_me else "#f1f5f9"
                    border_color = "#0284c7" if is_me else "#cbd5e1"
                    role_tag = "You" if is_me else msg.get("sender_role", "").title()

                    st.markdown(
                        f"""
                        <div style="text-align: {align}; margin-bottom: 0.8rem;">
                            <div style="display: inline-block; background-color: {bg_color}; border: 1px solid {border_color}; padding: 8px 14px; border-radius: 12px; max-width: 78%; text-align: left;">
                                <span style="font-size: 0.72rem; font-weight: bold; color: #475569;">{role_tag} &middot; {fmt_date(msg.get('created_at'))}</span>
                                <p style="margin: 3px 0 0 0; font-size: 0.9rem; color: #0f172a;">{msg.get('message')}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # Send Message Input Form
        with st.form(f"chat_form_{tenant_id}", clear_on_submit=True):
            col_inp, col_btn = st.columns([4, 1])
            with col_inp:
                new_msg = st.text_input("Type your message...", placeholder="Type your message here...", label_visibility="collapsed")
            with col_btn:
                sent = st.form_submit_button("Send 📩", type="primary", use_container_width=True)

            if sent and new_msg:
                if send_chat_message(tenant_id, current_user_id, current_user_role, current_user_email, new_msg):
                    st.rerun()

    # TAB 2: WEBRTC VIDEO CALL ROOM
    with tab_video:
        st.markdown("##### 📹 Encrypted HD Video Call Room")
        st.caption("Enjoy browser-to-browser encrypted video calling. Allow camera/microphone permissions when prompted.")

        room_id = f"RentMaster_Tenancy_{str(tenant_id).replace('-', '')[:16]}"
        jitsi_url = f"https://meet.jit.si/{room_id}#config.prejoinPageEnabled=false"

        st.info(f"🔒 **Private Call Room Active:** `{room_id}`")
        
        # Embed WebRTC Jitsi Video Room
        components.iframe(jitsi_url, height=480, scrolling=True)
