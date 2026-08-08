# ui/pages_management.py
import logging
import streamlit as st
from datetime import datetime, date, timedelta
from services.helpers import (
    get_active_user_info, get_current_currency, fmt_money, fmt_date,
    prop_label, tenant_label, compute_tenant_ledger, GLOBAL_PAYOUT_BANKS
)
from services.database import (
    sb, fetch_properties, fetch_landlords, fetch_tenants, fetch_payments,
    fetch_leases, fetch_maintenance, clear_cache, upload_id_to_supabase
)
from services.paystack import save_landlord_bank_details, initialize_paystack_payment
from services.pdf_generator import generate_receipt_pdf
from services.alerts import render_overdue_alerts_widget
from components.kyc import render_id_verification_widget
from components.chat import render_chat_interface
from components.property_condition import render_landlord_condition_upload_widget
from components.agreements import render_landlord_agreement_creator_widget
from ui.pages_core import header

logger = logging.getLogger("RentMaster")


def page_properties():
    header()
    st.subheader("Properties")
    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    with st.expander("Add New Property", expanded=False):
        with st.form("add_property"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Property Name *")
                address = st.text_input("Address / Location *")
                rent = st.number_input(f"Monthly Rent ({curr_code})", min_value=0.0, value=0.0, step=50.0)
            with col2:
                ptype = st.selectbox("Property Type", ["apartment", "house", "commercial", "other"])
                beds = st.number_input("Bedrooms", min_value=0, value=0)
                baths = st.number_input("Bathrooms", min_value=0, value=0)
            desc = st.text_area("Description")
            is_occupied = st.checkbox("Is Occupied", value=False)

            if st.form_submit_button("Add Property"):
                if not name or not address:
                    st.error("Property name and address are required.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    payload = {
                        "name": name, "address": address, "monthly_rent": float(rent),
                        "property_type": ptype, "bedrooms": int(beds), "bathrooms": int(baths),
                        "is_occupied": is_occupied, "description": desc,
                    }
                    if user_id: payload["user_id"] = user_id
                    if user_email: payload["user_email"] = user_email

                    sb.table("properties").insert(payload).execute()
                    clear_cache()
                    st.success(f"Property '{name}' added.")
                    st.rerun()

    props = fetch_properties(user_id, user_email)
    if not props:
        st.info("No properties yet. Add one above.")
        return

    st.markdown("---")
    st.markdown(f"**{len(props)} Properties**")
    for p in props:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            with col1:
                st.markdown(f"**{p.get('name') or p.get('property_name', 'Unnamed')}**")
                st.caption(p.get("address", ""))
            with col2:
                rent_val = p.get('monthly_rent') if p.get('monthly_rent') is not None else p.get('rent_amount')
                st.markdown(f"Rent: {fmt_money(rent_val)}")
            with col3:
                st.markdown(f"Status: **{'Occupied' if p.get('is_occupied') else 'Vacant'}**")
            with col4:
                if st.button("Delete", key=f"del_prop_{p['id']}", type="secondary"):
                    if sb:
                        sb.table("properties").delete().eq("id", p["id"]).execute()
                        clear_cache()
                        st.rerun()

            # Pre-Move-In Property Condition & Photos Management Portal
            with st.expander("📸 Property Pre-Move-In Condition Photos & Report", expanded=False):
                render_landlord_condition_upload_widget(property_id=p["id"])


def page_landlords():
    header()
    st.subheader("Landlord & Payout Management")

    user_id, user_email = get_active_user_info()
    landlords = fetch_landlords(user_id, user_email)
    tenants = fetch_tenants(user_id, user_email)

    landlord_options = {"new": "➕ Add New Landlord"}
    for l in landlords:
        landlord_options[l["id"]] = f"{l['name']} ({l.get('phone', 'No Phone')})"

    selected_id = st.selectbox("Select Landlord to Manage", options=list(landlord_options.keys()), format_func=lambda x: landlord_options[x])
    selected_landlord = next((l for l in landlords if l["id"] == selected_id), None)

    st.markdown("#### 1. Landlord KYC Identity Verification")
    landlord_id_file = render_id_verification_widget(entity_type="Landlord", key_prefix="landlord")

    st.markdown("#### 2. Landlord Payout Destination Details")
    with st.form("landlord_payout_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Landlord Full Name *", value=selected_landlord.get("name", "") if selected_landlord else "")
            email = st.text_input("Email Address", value=selected_landlord.get("email", "") if selected_landlord else "")
            phone = st.text_input("Phone Number *", value=selected_landlord.get("phone", "") if selected_landlord else "")
            country = st.selectbox("Landlord Country *", list(GLOBAL_PAYOUT_BANKS.keys()), key="landlord_country_select")

        with col2:
            available_banks = GLOBAL_PAYOUT_BANKS[country]
            bank_name = st.selectbox("Payout Provider / Bank *", list(available_banks.keys()))
            account_number = st.text_input("Account / Mobile Money / IBAN *", value=selected_landlord.get("account_number", "") if selected_landlord else "")
            selected_bank_code = available_banks[bank_name]

        if st.form_submit_button("Save Landlord Payout Details", type="primary", use_container_width=True):
            if not name or not phone or not account_number:
                st.error("Please fill in required fields.")
            else:
                target_id = selected_id if selected_id != "new" else None
                try:
                    id_card_url = None
                    if landlord_id_file:
                        id_card_url = upload_id_to_supabase(landlord_id_file, name, folder="landlords")

                    data, code = save_landlord_bank_details(
                        landlord_id=target_id, name=name, email=email, phone=phone,
                        bank_name=bank_name, account_number=account_number, bank_code=selected_bank_code,
                        platform_fee_pct=0.0, id_card_url=id_card_url, user_id=user_id, user_email=user_email
                    )
                    clear_cache()
                    st.success(f"✅ Landlord registered! Paystack Code: `{code}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to save details: {e}")

    if landlords:
        st.markdown("---")
        st.markdown(f"**{len(landlords)} Landlords Registered**")
        for l in landlords:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.markdown(f"**{l.get('name', 'Unnamed')}**")
                c2.markdown(f"Provider: **{l.get('bank_name', '-')}**")
                c3.markdown(f"Subaccount: `{l.get('paystack_subaccount_code', 'Unlinked')}`")
                with c4:
                    if st.button("Delete", key=f"del_landlord_{l['id']}", type="secondary"):
                        if sb:
                            sb.table("landlords").delete().eq("id", l["id"]).execute()
                            clear_cache()
                            st.rerun()


def page_tenants():
    header()
    st.subheader("Tenants Management")
    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    props = fetch_properties(user_id, user_email)
    prop_options = {p["id"]: prop_label(p) for p in props} or {"": "No properties available"}

    # CLEAN ADD TENANT FORM
    with st.expander("Add New Tenant", expanded=False):
        with st.form("add_tenant"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Tenant Name *", placeholder="e.g. Kwame Mensah")
                email = st.text_input("Email Address *", placeholder="tenant@example.com")
                rent_amount = st.number_input(f"Agreed Monthly Rent ({curr_code})", min_value=0.0, value=0.0, step=50.0)
            with col2:
                phone = st.text_input("Phone Number", placeholder="+233 20 000 0000")
                prop_id = st.selectbox("Assigned Property", list(prop_options.keys()), format_func=lambda x: prop_options.get(x, "-"))

            col3, col4 = st.columns(2)
            with col3:
                st.date_input("Lease Start", value=date.today())
            with col4:
                st.date_input("Lease End", value=date.today() + timedelta(days=365))
            active = st.checkbox("Active Tenant", value=True)

            if st.form_submit_button("Add Tenant", type="primary", use_container_width=True):
                if not name or not email:
                    st.error("Tenant name and email address are required.")
                elif sb:
                    payload = {
                        "name": name, "email": email or None, "phone": phone or None,
                        "property_id": prop_id or None, "rent_amount": float(rent_amount),
                        "is_active": active, "verification_status": "unverified"
                    }
                    if user_id: payload["user_id"] = user_id
                    if user_email: payload["user_email"] = user_email

                    sb.table("tenants").insert(payload).execute()
                    clear_cache()
                    st.success(f"✅ Tenant '{name}' added! Email linked to tenant portal.")
                    st.rerun()

    tenants = fetch_tenants(user_id, user_email)
    if tenants:
        st.markdown("---")
        st.markdown(f"**{len(tenants)} Tenants Registered**")
        for t in tenants:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                col1.markdown(f"**{t.get('name', 'Unnamed')}** (`{t.get('email', 'No Email')}`)")
                col2.markdown(f"Property: {prop_label(t.get('properties'))}")
                with col3:
                    status = "Active" if t.get("is_active") else "Inactive"
                    st.markdown(f"Status: **{status}**")
                    
                    v_status = t.get("verification_status", "unverified")
                    mgr_time_str = t.get("manager_approved_at")

                    # LANDLORD 2-DAY ACCEPTANCE BADGE & BUTTON
                    if v_status in ["manager_approved", "pending_manager_approval"] and not t.get("landlord_acceptance"):
                        deadline_text = "48h window active"
                        if mgr_time_str:
                            try:
                                app_time = datetime.fromisoformat(mgr_time_str)
                                hours_left = max(0, int(((app_time + timedelta(days=2)) - datetime.now()).total_seconds() // 3600))
                                deadline_text = f"⏰ {hours_left}h left to accept"
                            except Exception:
                                pass

                        st.warning(f"🛡️ Manager Approved ({deadline_text})")
                        if st.button("✅ Accept Tenant", key=f"accept_tenant_{t['id']}", type="primary"):
                            if sb:
                                sb.table("tenants").update({"landlord_acceptance": True}).eq("id", t["id"]).execute()
                                clear_cache()
                                st.toast("✅ Tenant Accepted & Admitted!", icon="🤝")
                                st.rerun()
                    elif t.get("landlord_acceptance"):
                        st.success("✅ Landlord Accepted")
                    else:
                        st.caption(f"KYC Status: `{v_status.upper()}`")
                with col4:
                    with st.popover("💬 Chat & Video"):
                        render_chat_interface(
                            tenant_id=t.get("id"),
                            current_user_id=user_id,
                            current_user_role="landlord",
                            current_user_email=user_email,
                            recipient_name=t.get("name", "Tenant")
                        )

                    if st.button("Delete", key=f"del_tenant_{t['id']}", type="secondary"):
                        if sb:
                            sb.table("tenants").delete().eq("id", t["id"]).execute()
                            clear_cache()
                            st.rerun()


def page_payments():
    header()
    st.subheader("Rent Ledger & Payments Hub")
    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    tenants = fetch_tenants(user_id, user_email)
    all_payments = fetch_payments(user_id, user_email)

    # Render Automated Rent Overdue Alert Engine
    render_overdue_alerts_widget(tenants, all_payments)
    st.markdown("---")

    tab_ledger, tab_manual, tab_log = st.tabs([
        "📜 Tenant Rent Ledger & Pay Rent",
        "📝 Record Offline Payment",
        "📊 Master Payment Log & Receipts"
    ])

    with tab_ledger:
        if tenants:
            tenant_map = {t["id"]: f"{t.get('name')} — {prop_label(t.get('properties'))}" for t in tenants}
            selected_tenant_id = st.selectbox("Select Tenant Ledger", options=list(tenant_map.keys()), format_func=lambda x: tenant_map[x], key="ledger_tenant_select")
            selected_tenant = next((t for t in tenants if t["id"] == selected_tenant_id), None)
            ledger = compute_tenant_ledger(selected_tenant, all_payments)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Monthly Rent", fmt_money(ledger["monthly_rent"]))
            m2.metric("Total Charged", fmt_money(ledger["total_charged"]))
            m3.metric("Total Paid", fmt_money(ledger["total_paid"]))
            m4.metric("Ledger Balance", fmt_money(abs(ledger["balance"])))

            with st.form("rent_checkout_form"):
                pay_amount = st.number_input(f"Payment Amount ({curr_code}) *", min_value=1.0, value=float(max(ledger["balance"], ledger["monthly_rent"])), step=50.0)
                receipt_email = st.text_input("Receipt Email *", value=selected_tenant.get("email") or "")
                callback_domain = st.text_input("Callback Base URL", value="https://www.rentmastergh.com")

                if st.form_submit_button("💳 Proceed to Checkout", type="primary", use_container_width=True):
                    res = initialize_paystack_payment(
                        email=receipt_email, amount_in_main_unit=pay_amount, callback_url=callback_domain,
                        metadata={"type": "rent_payment", "tenant_id": selected_tenant_id, "user_id": user_id}, currency=curr_code
                    )
                    if res.get("status"):
                        st.link_button("👉 Click Here to Pay Now", res["data"]["authorization_url"], type="primary", use_container_width=True)

    with tab_log:
        if all_payments:
            for p in all_payments:
                with st.container(border=True):
                    col1, col2, col3, col4, col5 = st.columns([2.5, 2, 2, 2, 1.5])
                    t_obj = p.get("tenants")
                    col1.markdown(f"**{tenant_label(t_obj)}**")
                    col2.markdown(f"Amount: **{fmt_money(p.get('amount'))}**")
                    col3.markdown(f"Date: {fmt_date(p.get('payment_date'))}")
                    col4.markdown(f"Status: **{str(p.get('status')).upper()}**")
                    with col5:
                        if p.get("status") == "paid":
                            try:
                                pdf_bytes = generate_receipt_pdf(t_obj or {}, p, t_obj.get("properties") if isinstance(t_obj, dict) else None)
                                st.download_button("📄 PDF Receipt", data=pdf_bytes, file_name=f"Receipt_{p['id'][:6]}.pdf", mime="application/pdf", key=f"rec_btn_{p['id']}")
                            except Exception as e:
                                st.caption("PDF Error")


def page_leases():
    header()
    st.subheader("Leases & Tenancy Agreements")
    curr_code = get_current_currency()
    user_id, user_email = get_active_user_info()

    props = fetch_properties(user_id, user_email)
    tenants = fetch_tenants(user_id, user_email)
    prop_options = {p["id"]: prop_label(p) for p in props} or {"": "No properties available"}
    tenant_options = {t["id"]: tenant_label(t) for t in tenants} or {"": "No tenants available"}

    with st.expander("➕ Create New Lease Agreement", expanded=False):
        with st.form("add_lease_form"):
            col1, col2 = st.columns(2)
            with col1:
                pid = st.selectbox("Property *", list(prop_options.keys()), format_func=lambda x: prop_options.get(x, "-"))
                start = st.date_input("Lease Start Date *", value=date.today())
            with col2:
                tid = st.selectbox("Tenant *", list(tenant_options.keys()), format_func=lambda x: tenant_options.get(x, "-"))
                end = st.date_input("Lease End Date *", value=date.today() + timedelta(days=365))
            
            deposit = st.number_input(f"Security Deposit Amount ({curr_code})", min_value=0.0, value=0.0, step=100.0)
            status = st.selectbox("Lease Status", ["active", "expired", "terminated"])
            
            if st.form_submit_button("Create Lease Agreement", type="primary"):
                if not pid or not tid:
                    st.error("Please select a valid property and tenant.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    try:
                        payload = {
                            "property_id": pid, "tenant_id": tid,
                            "start_date": str(start), "end_date": str(end),
                            "deposit_amount": float(deposit), "status": status,
                        }
                        if user_id: payload["user_id"] = user_id
                        if user_email: payload["user_email"] = user_email

                        sb.table("leases").insert(payload).execute()
                        clear_cache()
                        st.success("✅ Lease agreement created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create lease: {e}")

    leases = fetch_leases(user_id, user_email)
    if not leases:
        st.info("No lease agreements found. Create one above.")
        return

    st.markdown("---")
    st.markdown(f"**{len(leases)} Lease Agreements**")

    for l in leases:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            with col1:
                st.markdown(f"**Property:** {prop_label(l.get('properties'))}")
                st.caption(f"Tenant: {tenant_label(l.get('tenants'))}")
            with col2:
                st.caption(f"Start: {fmt_date(l.get('start_date'))}")
                st.caption(f"End: {fmt_date(l.get('end_date'))}")
            with col3:
                st.markdown(f"Deposit: **{fmt_money(l.get('deposit_amount'))}**")
            with col4:
                status_badge = "green" if l.get("status") == "active" else "orange"
                st.markdown(f"Status: :{status_badge}[**{str(l.get('status', '-')).upper()}**]")
            with col5:
                if st.button("Delete", key=f"del_lease_{l['id']}", type="secondary"):
                    if sb:
                        sb.table("leases").delete().eq("id", l["id"]).execute()
                        clear_cache()
                        st.rerun()

            # Landlord Tenancy Agreement Manager
            with st.expander("📜 Manage / Issue Tenancy Agreement", expanded=False):
                render_landlord_agreement_creator_widget(lease_id=l["id"])


def page_maintenance():
    header()
    st.subheader("Maintenance Requests & Ticket Center")
    user_id, user_email = get_active_user_info()

    props = fetch_properties(user_id, user_email)
    tenants = fetch_tenants(user_id, user_email)
    prop_options = {p["id"]: prop_label(p) for p in props} or {"": "No properties available"}
    tenant_options = {t["id"]: tenant_label(t) for t in tenants} or {"": "None / General Maintenance"}

    with st.expander("🛠️ File New Maintenance Request", expanded=False):
        with st.form("add_maintenance_form"):
            col1, col2 = st.columns(2)
            with col1:
                pid = st.selectbox("Property *", list(prop_options.keys()), format_func=lambda x: prop_options.get(x, "-"))
                title = st.text_input("Issue Title *", placeholder="e.g. Plumbing Leak in Kitchen")
            with col2:
                tid = st.selectbox("Tenant (Optional)", list(tenant_options.keys()), format_func=lambda x: tenant_options.get(x, "None"))
                priority = st.selectbox("Urgency Priority", ["low", "medium", "high", "urgent"])
            
            desc = st.text_area("Detailed Issue Description")
            status = st.selectbox("Ticket Status", ["open", "in_progress", "resolved", "closed"])
            
            if st.form_submit_button("Submit Maintenance Request", type="primary"):
                if not pid or not title:
                    st.error("Please fill in property and issue title.")
                elif not sb:
                    st.error("Database connection missing.")
                else:
                    try:
                        payload = {
                            "property_id": pid,
                            "tenant_id": tid if (tid and tid != "") else None,
                            "title": title, "description": desc,
                            "priority": priority, "status": status,
                        }
                        if user_id: payload["user_id"] = user_id
                        if user_email: payload["user_email"] = user_email

                        sb.table("maintenance_requests").insert(payload).execute()
                        clear_cache()
                        st.success("✅ Maintenance ticket filed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to file request: {e}")

    requests_list = fetch_maintenance(user_id, user_email)
    if not requests_list:
        st.info("No maintenance requests filed. File one above.")
        return

    st.markdown("---")
    st.markdown(f"**{len(requests_list)} Maintenance Tickets**")

    for m in requests_list:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1])
            with col1:
                st.markdown(f"**{m.get('title', 'Untitled')}**")
                if m.get("description"):
                    st.caption(m["description"])
                st.caption(f"Property: {prop_label(m.get('properties'))}")
            with col2:
                pr = m.get('priority', 'medium').upper()
                st.markdown(f"Priority: `{pr}`")
            with col3:
                st.markdown(f"Status: **{str(m.get('status', 'open')).upper()}**")
            with col4:
                st.caption(f"Filed: {fmt_date(m.get('created_at'))}")
            with col5:
                if st.button("Delete", key=f"del_maint_{m['id']}", type="secondary"):
                    if sb:
                        sb.table("maintenance_requests").delete().eq("id", m["id"]).execute()
                        clear_cache()
                        st.rerun()
