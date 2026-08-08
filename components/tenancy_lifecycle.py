"""
RentMaster-GH - Tenancy Expiration, Renewal, 14-Day Landlord Review & 3-Month Grace Period Engine
"""
import streamlit as st
from datetime import datetime, timedelta
from services.database import sb


def calculate_lease_lifecycle(lease_end_date_str):
    """
    Calculates lease timeline:
    - Days until expiration
    - Is inside 90-day notification window?
    - Is expired?
    - Grace period month calculation (Month 1, 2, or 3)
    """
    try:
        end_date = datetime.strptime(str(lease_end_date_str)[:10], "%Y-%m-%d")
        now = datetime.now()
        days_until_expiration = (end_date - now).days

        # Expiration States
        is_90_day_window = 0 <= days_until_expiration <= 90
        is_expired = days_until_expiration < 0
        grace_days = abs(days_until_expiration) if is_expired else 0

        # Grace Period Month (1 to 3)
        grace_month = 0
        if is_expired:
            if grace_days <= 30:
                grace_month = 1
            elif grace_days <= 60:
                grace_month = 2
            elif grace_days <= 90:
                grace_month = 3
            else:
                grace_month = 4  # Grace period elapsed -> Legal action allowed

        return {
            "days_left": days_until_expiration,
            "is_90_day_window": is_90_day_window,
            "is_expired": is_expired,
            "grace_days": grace_days,
            "grace_month": grace_month,
            "grace_elapsed": grace_month > 3
        }
    except Exception:
        return {"days_left": 365, "is_90_day_window": False, "is_expired": False, "grace_days": 0, "grace_month": 0, "grace_elapsed": False}


# ---------------------------------------------------------------------------
# TENANT WIDGET: 90-DAY EXPIRATION ALERT & RENEWAL/TERMINATION REQUEST
# ---------------------------------------------------------------------------
def render_tenant_lease_lifecycle_widget(tenant_user, lease_data):
    """Renders expiration warnings, renewal request form, or Grace Period notices for tenants."""
    lease_id = lease_data.get("id", "demo_lease")
    end_date_str = str(lease_data.get("end_date", datetime.now().strftime("%Y-%m-%d")))

    lifecycle = calculate_lease_lifecycle(end_date_str)
    tenant_decision = lease_data.get("tenant_intent")  # 'renewal', 'termination', or None
    landlord_decision = lease_data.get("landlord_intent_decision")  # 'accepted', 'declined', 'pending'
    requested_at_str = lease_data.get("tenant_intent_requested_at")

    # 1. POST-EXPIRATION 3-MONTH GRACE PERIOD TRACKER
    if lifecycle["is_expired"]:
        st.error("⚠️ **Tenancy Agreement Expired**")
        
        if lifecycle["grace_elapsed"]:
            st.error(
                """
                🚨 **3-Month Grace Period Has Expired!**
                Your 3-month grace period has elapsed. You are required to vacate the premises immediately. 
                The landlord is legally authorized to initiate formal eviction proceedings under Ghana Rent Act provisions.
                """
            )
        else:
            st.warning(
                f"""
                ⏳ **3-Month Grace Period Active (Month {lifecycle['grace_month']} of 3)**
                Your lease expired on `{end_date_str[:10]}`. You have been granted a **3-Month Grace Period** to secure alternative accommodation.
                
                📌 **Payment Requirement:** You are required to continue paying your regular monthly rent for Month {lifecycle['grace_month']}.
                """
            )
        return

    # 2. 90-DAY PRE-EXPIRATION NOTIFICATION WINDOW
    if lifecycle["is_90_day_window"]:
        st.warning(f"⏰ **Impending Lease Expiration:** Your tenancy expires in **{lifecycle['days_left']} days** (`{end_date_str[:10]}`).")

        with st.container(border=True):
            st.markdown("#### 📝 Select Tenancy Action")
            
            if not tenant_decision:
                st.caption("Please notify your landlord whether you wish to renew your tenancy or terminate upon expiration.")
                
                intent = st.radio(
                    "Your Decision *",
                    ["🔄 Request Tenancy Renewal", "🚪 Request Tenancy Termination"],
                    key=f"intent_radio_{lease_id}"
                )
                
                duration = "1 Year"
                if "Renewal" in intent:
                    duration = st.selectbox("Requested Renewal Duration", ["1 Year", "2 Years", "6 Months"])

                if st.button("📤 Submit Decision to Landlord", type="primary", use_container_width=True):
                    decision_key = "renewal" if "Renewal" in intent else "termination"
                    
                    if sb:
                        try:
                            sb.table("leases").update({
                                "tenant_intent": decision_key,
                                "requested_duration": duration,
                                "tenant_intent_requested_at": datetime.now().isoformat(),
                                "landlord_intent_decision": "pending"
                            }).eq("id", lease_id).execute()
                        except Exception:
                            pass

                    st.success("✅ Decision submitted! Your landlord has 14 days to respond.")
                    st.rerun()

            else:
                # Decision already submitted -> Show status & 14-day landlord response window
                st.info(f"📩 You requested **{tenant_decision.title()}** on `{requested_at_str[:10] if requested_at_str else 'Recently'}`.")
                
                if landlord_decision == "pending":
                    # Calculate Landlord 14-day countdown
                    fourteen_day_text = "Landlord has 14 days to review"
                    if requested_at_str:
                        try:
                            req_time = datetime.fromisoformat(requested_at_str)
                            days_left_landlord = max(0, 14 - (datetime.now() - req_time).days)
                            fourteen_day_text = f"⏰ Landlord decision due in {days_left_landlord} days"
                        except Exception:
                            pass
                    st.warning(f"⏳ **Awaiting Landlord Response:** {fourteen_day_text}")

                elif landlord_decision == "accepted":
                    st.success("🎉 **Landlord Accepted!** Your request has been approved.")
                elif landlord_decision == "declined":
                    st.error("❌ **Landlord Declined:** Please prepare for transition or 3-month grace period.")


# ---------------------------------------------------------------------------
# LANDLORD WIDGET: 14-DAY DECISION REVIEW CENTER
# ---------------------------------------------------------------------------
def render_landlord_lease_lifecycle_widget(lease_data):
    """Renders 14-day decision center for landlords reviewing tenant requests."""
    lease_id = lease_data.get("id", "demo_lease")
    end_date_str = str(lease_data.get("end_date", datetime.now().strftime("%Y-%m-%d")))
    lifecycle = calculate_lease_lifecycle(end_date_str)

    tenant_decision = lease_data.get("tenant_intent")
    landlord_decision = lease_data.get("landlord_intent_decision", "pending")
    requested_at_str = lease_data.get("tenant_intent_requested_at")

    # 1. EXPIRED LEASE & GRACE PERIOD EVICTION LEGAL NOTICE
    if lifecycle["is_expired"]:
        if lifecycle["grace_elapsed"]:
            st.error(
                f"""
                🚨 **3-Month Grace Period Has Elapsed!**
                Tenant has occupied the facility for over 90 days past expiration (`{end_date_str[:10]}`).
                ⚖️ **Legal Action Unlocked:** You are now legally entitled to initiate eviction proceedings via Rent Control / District Court.
                """
            )
        else:
            st.warning(
                f"""
                ⏳ **Tenant Active in Grace Period (Month {lifecycle['grace_month']} of 3)**
                Lease expired on `{end_date_str[:10]}`. Tenant is currently in Month {lifecycle['grace_month']} of the 3-month grace period.
                Tenant is expected to continue paying monthly rent during this transition.
                """
            )
        return

    # 2. 14-DAY REVIEW WINDOW FOR TENANT INTENT
    if tenant_decision:
        with st.container(border=True):
            st.markdown(f"#### 📩 Tenant Request: **{tenant_decision.title()}**")
            
            # Calculate 14-day deadline countdown
            days_remaining_landlord = 14
            if requested_at_str:
                try:
                    req_time = datetime.fromisoformat(requested_at_str)
                    days_remaining_landlord = max(0, 14 - (datetime.now() - req_time).days)
                except Exception:
                    pass

            st.caption(f"Submitted on `{requested_at_str[:10] if requested_at_str else 'N/A'}` | ⏰ **14-Day Response Window:** {days_remaining_landlord} days remaining.")

            if landlord_decision == "pending":
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("✅ Accept Request", key=f"landlord_app_{lease_id}", type="primary", use_container_width=True):
                        if sb:
                            sb.table("leases").update({"landlord_intent_decision": "accepted"}).eq("id", lease_id).execute()
                        st.success("Accepted!")
                        st.rerun()
                with c2:
                    if st.button("❌ Decline Request", key=f"landlord_dec_{lease_id}", type="secondary", use_container_width=True):
                        if sb:
                            sb.table("leases").update({"landlord_intent_decision": "declined"}).eq("id", lease_id).execute()
                        st.error("Declined!")
                        st.rerun()
                with c3:
                    if st.button("⏳ Hold / Pending Decision", key=f"landlord_hold_{lease_id}", use_container_width=True):
                        st.info("Marked as Pending Definite Decision.")
            else:
                st.info(f"Decision Status: **{landlord_decision.upper()}**")
