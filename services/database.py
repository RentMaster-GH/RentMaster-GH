import os
import json
import uuid
import base64
import logging
import requests
import streamlit as st
from types import SimpleNamespace
from dotenv import load_dotenv
from services.helpers import get_secret

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RentMaster")


def _resolve_backend_url() -> str:
    raw = (
        os.environ.get("BACKEND_URL")
        or os.environ.get("VITE_BACKEND_URL")
        or get_secret("BACKEND_URL")
        or get_secret("VITE_BACKEND_URL")
        or "https://api.credibleartisans.com"
    )
    url = str(raw).strip().rstrip("/")
    if url.endswith("/auth"):
        url = url[:-5]
    if url in ("https://credibleartisans.com", "https://www.credibleartisans.com"):
        url = "https://api.credibleartisans.com"
    return url


BACKEND_URL = _resolve_backend_url()
APP_ID = (
    os.environ.get("APP_ID")
    or os.environ.get("VITE_APP_ID")
    or get_secret("APP_ID")
    or get_secret("VITE_APP_ID")
    or "rentmaster-gh"
).strip()


def _safe_json(resp) -> dict:
    if not resp.content:
        return {}
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {"data": data}
    except Exception:
        snippet = resp.text[:180].strip() if resp.text else ""
        raise Exception(
            f"Backend returned non-JSON response (HTTP {resp.status_code}) from {resp.url}: {snippet}"
        )


def _ns(d):
    if isinstance(d, dict):
        return SimpleNamespace(**{k: _ns(v) for k, v in d.items()})
    if isinstance(d, list):
        return [_ns(x) for x in d]
    return d


class CustomAuthClient:
    def _headers(self, token=None):
        h = {"Content-Type": "application/json"}
        tok = token or st.session_state.get("_rm_access_token")
        if tok:
            h["Authorization"] = f"Bearer {tok}"
        return h

    def _build_user(self, raw_user: dict, extra_meta: dict = None):
        claims = raw_user.get("custom_claims") or {}
        if isinstance(claims, str):
            try:
                claims = json.loads(claims)
            except Exception:
                claims = {}
        meta = {**claims, **(extra_meta or {})}
        if "role" not in meta:
            meta["role"] = meta.get("account_role") or raw_user.get("role") or "landlord"
        return SimpleNamespace(
            id= raw_user.get("id") or raw_user.get("sub") or str(uuid.uuid4()),
            email=raw_user.get("email", ""),
            role=meta["role"],
            user_metadata=dict(meta),
        )

    def sign_in_with_password(self, credentials: dict):
        email = (credentials.get("email") or "").strip().lower()
        password = credentials.get("password") or ""
        resp = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"app_id": APP_ID, "email": email, "password": password},
            timeout=15,
        )
        data = _safe_json(resp)
        if not resp.ok:
            raise Exception(data.get("error") or data.get("message") or f"Login failed ({resp.status_code})")

        access_token = data.get("accessToken") or data.get("access_token")
        refresh_token = data.get("refreshToken") or data.get("refresh_token")
        st.session_state["_rm_access_token"] = access_token
        st.session_state["_rm_refresh_token"] = refresh_token

        raw_user = data.get("user") or {"email": email}
        user_obj = self._build_user(raw_user)
        session_obj = _ns({"access_token": access_token, "refresh_token": refresh_token})
        return _ns({"user": user_obj, "session": session_obj})

    def sign_up(self, payload: dict):
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        options = payload.get("options") or {}
        user_data = options.get("data") or {}
        custom_claims = {**user_data, "account_role": user_data.get("role", "landlord")}

        resp = requests.post(
            f"{BACKEND_URL}/auth/register",
            json={
                "app_id": APP_ID,
                "email": email,
                "password": password,
                "role": "user",
                "custom_claims": custom_claims,
            },
            timeout=15,
        )
        data = _safe_json(resp)
        if not resp.ok:
            raise Exception(data.get("error") or data.get("message") or f"Sign up failed ({resp.status_code})")

        access_token = data.get("accessToken") or data.get("access_token")
        refresh_token = data.get("refreshToken") or data.get("refresh_token")
        if access_token:
            st.session_state["_rm_access_token"] = access_token
            st.session_state["_rm_refresh_token"] = refresh_token

        raw_user = data.get("user") or {"email": email}
        user_obj = self._build_user(raw_user, user_data)
        session_obj = _ns({"access_token": access_token, "refresh_token": refresh_token}) if access_token else None
        return _ns({"user": user_obj, "session": session_obj})

    def set_session(self, access_token: str, refresh_token: str):
        st.session_state["_rm_access_token"] = access_token
        st.session_state["_rm_refresh_token"] = refresh_token
        resp = requests.get(f"{BACKEND_URL}/me", headers=self._headers(access_token), timeout=10)
        if not resp.ok and refresh_token:
            r2 = requests.post(
                f"{BACKEND_URL}/auth/refresh",
                json={"refreshToken": refresh_token},
                timeout=10,
            )
            if r2.ok:
                d2 = _safe_json(r2)
                access_token = d2.get("accessToken") or d2.get("access_token")
                refresh_token = d2.get("refreshToken") or d2.get("refresh_token")
                st.session_state["_rm_access_token"] = access_token
                st.session_state["_rm_refresh_token"] = refresh_token
                resp = requests.get(f"{BACKEND_URL}/me", headers=self._headers(access_token), timeout=10)

        if resp.ok:
            me_data = _safe_json(resp)
            payload = me_data.get("payload") or me_data.get("user") or me_data
            user_obj = self._build_user(payload)
            return _ns({"user": user_obj})
        return None

    def sign_in_with_oauth(self, opts: dict):
        return _ns({"url": None})

    def exchange_code_for_session(self, opts: dict):
        return None

    def sign_out(self):
        ref = st.session_state.get("_rm_refresh_token")
        if ref:
            try:
                requests.post(f"{BACKEND_URL}/auth/logout", json={"refreshToken": ref}, timeout=8)
            except Exception:
                pass
        st.session_state.pop("_rm_access_token", None)
        st.session_state.pop("_rm_refresh_token", None)


class CustomTableQuery:
    def __init__(self, collection: str, client: "CustomBackendClient"):
        self.collection = collection
        self.client = client
        self._op = "select"
        self._select_cols = "*"
        self._payload = None
        self._filters = []
        self._order_col = None
        self._order_desc = False
        self._limit_val = None
        self._single = False

    def select(self, cols: str = "*"):
        self._select_cols = cols
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        return self

    def upsert(self, payload):
        self._op = "upsert"
        self._payload = payload
        return self

    def update(self, payload: dict):
        self._op = "update"
        self._payload = payload
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col: str, val):
        self._filters.append(("eq", col, val))
        return self

    def neq(self, col: str, val):
        self._filters.append(("neq", col, val))
        return self

    def in_(self, col: str, vals: list):
        self._filters.append(("in", col, vals))
        return self

    def order(self, col: str, desc: bool = False):
        self._order_col = col
        self._order_desc = desc
        return self

    def limit(self, count: int):
        self._limit_val = count
        return self

    def single(self):
        self._single = True
        return self

    def _flatten(self, rec: dict) -> dict:
        if not isinstance(rec, dict):
            return {}
        data = rec.get("data") if isinstance(rec.get("data"), dict) else {}
        merged = {**data}
        for k in ("id", "app_id", "collection", "owner_id", "created_at", "updated_at"):
            if k in rec and rec[k] is not None:
                merged[k] = rec[k]
        if "user_id" not in merged and "owner_id" in merged:
            merged["user_id"] = merged["owner_id"]
        return merged

    def _match(self, row: dict) -> bool:
        for op, col, val in self._filters:
            rv = row.get(col)
            if op == "eq" and str(rv) != str(val):
                return False
            if op == "neq" and str(rv) == str(val):
                return False
            if op == "in" and rv not in val:
                return False
        return True

    def _hydrate(self, rows: list) -> list:
        if not rows or "(" not in self._select_cols:
            return rows
        if "properties(" in self._select_cols:
            props = {p["id"]: p for p in self.client._raw_list("properties") if p.get("id")}
            lands = {l["id"]: l for l in self.client._raw_list("landlords") if l.get("id")} if "landlords(" in self._select_cols else {}
            for r in rows:
                prop = props.get(r.get("property_id"))
                if prop and lands and prop.get("landlord_id"):
                    prop = {**prop, "landlords": lands.get(prop.get("landlord_id"))}
                r["properties"] = prop
        if "tenants(" in self._select_cols:
            tens = {t["id"]: t for t in self.client._raw_list("tenants") if t.get("id")}
            for r in rows:
                r["tenants"] = tens.get(r.get("tenant_id"))
        return rows

    def execute(self):
        headers = self.client._get_auth_headers()
        if self._op == "select":
            rows = self.client._raw_list(self.collection)
            rows = [r for r in rows if self._match(r)]
            if self._order_col:
                rows.sort(key=lambda x: str(x.get(self._order_col) or ""), reverse=self._order_desc)
            if self._limit_val is not None:
                rows = rows[: self._limit_val]
            rows = self._hydrate(rows)
            if self._single:
                return _ns({"data": rows[0] if rows else None})
            return _ns({"data": rows})

        if self._op in ("insert", "upsert"):
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            created = []
            for item in items:
                clean = {k: v for k, v in (item or {}).items() if not isinstance(v, dict) or k not in ("properties", "tenants", "landlords")}
                resp = requests.post(
                    f"{BACKEND_URL}/data/{self.collection}",
                    headers=headers,
                    json={"app_id": APP_ID, "data": clean},
                    timeout=15,
                )
                if resp.ok:
                    d = _safe_json(resp)
                    rec = d.get("record") or d
                    created.append(self._flatten(rec))
            return _ns({"data": created[0] if self._single and created else created})

        if self._op == "update":
            rows = [r for r in self.client._raw_list(self.collection) if self._match(r)]
            updated = []
            for r in rows:
                rid = r.get("id")
                if not rid:
                    continue
                merged = {**r, **(self._payload or {})}
                for meta_k in ("id", "app_id", "collection", "owner_id", "created_at", "updated_at", "properties", "tenants", "landlords"):
                    merged.pop(meta_k, None)
                resp = requests.patch(
                    f"{BACKEND_URL}/data/{self.collection}/{rid}",
                    headers=headers,
                    json={"app_id": APP_ID, "data": merged},
                    timeout=15,
                )
                if resp.ok:
                    d = _safe_json(resp)
                    rec = d.get("record") or d
                    updated.append(self._flatten(rec))
            return _ns({"data": updated})

        if self._op == "delete":
            rows = [r for r in self.client._raw_list(self.collection) if self._match(r)]
            for r in rows:
                rid = r.get("id")
                if rid:
                    requests.delete(f"{BACKEND_URL}/data/{self.collection}/{rid}?app_id={APP_ID}", headers=headers, timeout=15)
            return _ns({"data": rows})

        return _ns({"data": []})


class CustomStorageBucket:
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self._cache = {}

    def upload(self, path: str, file_bytes: bytes, opts: dict = None):
        mime = (opts or {}).get("content-type", "image/jpeg")
        b64 = base64.b64encode(file_bytes).decode("ascii")
        self._cache[path] = f"data:{mime};base64,{b64}"
        return {"path": path}

    def get_public_url(self, path: str) -> str:
        return self._cache.get(path, "")


class CustomStorageClient:
    def from_(self, bucket_name: str):
        return CustomStorageBucket(bucket_name)


class CustomBackendClient:
    def __init__(self):
        self.auth = CustomAuthClient()
        self.storage = CustomStorageClient()

    def _get_auth_headers(self):
        tok = st.session_state.get("_rm_access_token") or st.session_state.get("_rm_guest_token")
        if not tok:
            try:
                guest_email = f"guest_{uuid.uuid4().hex[:10]}@rentmaster.local"
                guest_pw = f"Guest_{uuid.uuid4().hex}!"
                r = requests.post(
                    f"{BACKEND_URL}/auth/register",
                    json={"app_id": APP_ID, "email": guest_email, "password": guest_pw, "role": "user"},
                    timeout=10,
                )
                if r.ok:
                    d = _safe_json(r)
                    tok = d.get("accessToken") or d.get("access_token")
                    st.session_state["_rm_guest_token"] = tok
            except Exception:
                pass
        h = {"Content-Type": "application/json"}
        if tok:
            h["Authorization"] = f"Bearer {tok}"
        return h

    def _raw_list(self, collection: str) -> list:
        try:
            resp = requests.get(
                f"{BACKEND_URL}/data/{collection}?app_id={APP_ID}",
                headers=self._get_auth_headers(),
                timeout=15,
            )
            if not resp.ok:
                return []
            d = _safe_json(resp)
            records = d.get("records") or d.get("data") or (d if isinstance(d, list) else [])
            q = CustomTableQuery(collection, self)
            return [q._flatten(r) for r in records]
        except Exception as e:
            logger.error(f"Error listing {collection}: {e}")
            return []

    def table(self, collection: str):
        return CustomTableQuery(collection, self)


@st.cache_resource
def get_client():
    return CustomBackendClient()


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


@st.cache_data(ttl=10)
def fetch_tenant_profile_by_email(email: str):
    if not sb or not email:
        return None
    try:
        r = sb.table("tenants").select("*, properties(*, landlords(*))").eq("email", email).order("created_at", desc=True).limit(1).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        logger.error(f"Error fetching tenant profile for {email}: {e}")
        return None


def clear_cache():
    fetch_properties.clear()
    fetch_landlords.clear()
    fetch_tenants.clear()
    fetch_payments.clear()
    fetch_leases.clear()
    fetch_maintenance.clear()
    fetch_ads.clear()
    fetch_tenant_profile_by_email.clear()


def upload_id_to_supabase(file_obj, identifier: str, folder: str = "tenants"):
    if not sb or not file_obj:
        return None
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
