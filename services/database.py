# services/database.py
import logging
import uuid
import streamlit as st
from supabase import create_client
from services.helpers import get_secret

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RentMaster")

SUPABASE_URL = get_secret("VITE_SUPABASE_URL") or get_secret("SUPABASE_URL")
SUPABASE_KEY = get_secret("VITE_SUPABASE_ANON_KEY") or get_secret("SUPABASE_KEY")


@st.cache_resource
def get_client():
    url = (SUPABASE_URL or "").strip()
    key = (SUPABASE_KEY or "").strip()
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase Client Connection Error: {e}")
        return None


sb = get_client()


@st.cache_data(ttl=10)
def fetch_properties(user_id: str = None, user_email: str = None):
    if not sb or not user_id:
        return []
    try:
        r = sb.table("properties").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        logger.error(f"Error fetching properties: {e}")
        return []


@st.cache_data(ttl=10)
def fetch_landlords(user_id: str = None, user_email: str = None):
    if not sb or not user_id:
        return []
    try:
        r = sb.table("landlords").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        logger.error(f"Error fetching landlords: {e}")
        return []


@st.cache_data(ttl=10)
def fetch_tenants(user_id: str = None, user_email: str = None):
    if not sb or not user_id:
        return []
    try:
        r = sb.table("tenants").select("*, properties(*, landlords(*))").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        logger.error(f"Error fetching tenants: {e}")
        return []


@st.cache_data(ttl=10)
def fetch_payments(user_id: str = None, user_email: str = None):
    if not sb or not user_id:
        return []
    try:
        r = sb.table("payments").select("*, tenants(*)").eq("user_id", user_id).order("payment_date", desc=True).execute()
        return r.data or []
    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        return []


@st.cache_data(ttl=10)
def fetch_leases(user_id: str = None, user_email: str = None):
    if not sb or not user_id:
        return []
    try:
        r = sb.table("leases").select("*, properties(*), tenants(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        logger.error(f"Error fetching leases: {e}")
        return []


@st.cache_data(ttl=10)
def fetch_maintenance(user_id: str = None, user_email: str = None):
    if not sb or not user_id:
        return []
    try:
        r = sb.table("maintenance_requests").select("*, properties(*), tenants(*)").eq("user_id", user_id).order("created_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        logger.error(f"Error fetching maintenance: {e}")
        return []


@st.cache_data(ttl=15)
def fetch_ads():
    if not sb:
        return []
    try:
        r = sb.table("ads").select("*").order("created_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        logger.error(f"Error fetching ads: {e}")
        return []


def clear_cache():
    fetch_properties.clear()
    fetch_landlords.clear()
    fetch_tenants.clear()
    fetch_payments.clear()
    fetch_leases.clear()
    fetch_maintenance.clear()
    fetch_ads.clear()


def upload_id_to_supabase(file_obj, identifier: str, folder: str = "tenants"):
    if not sb: return None
    try:
        file_bytes = file_obj.getvalue()
        file_ext = file_obj.name.split(".")[-1] if hasattr(file_obj, "name") and "." in file_obj.name else "jpg"
        file_path = f"{folder}/{uuid.uuid4().hex[:8]}_{identifier}.{file_ext}"

        bucket = sb.storage.from_("id-documents")
        bucket.upload(file_path, file_bytes, {"content-type": getattr(file_obj, "type", "image/jpeg"), "upsert": "true"})

        return bucket.get_public_url(file_path)
    except Exception as e:
        logger.error(f"Storage Upload Failed: {e}")
        st.error(f"Failed to upload document: {e}")
        return None
