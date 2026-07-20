"""
RentMaster-GH v2 - Rental Management Flask Application
Supabase-backed API for properties, tenants, payments, leases, and
maintenance requests. Includes pagination, filtering, and dashboard analytics.
"""

import os
from datetime import datetime, date

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in the environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def serialize(value):
    """Recursively convert datetimes to ISO strings for JSON safety."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.items()}
    return value


def error_response(message, status=400):
    return jsonify({"error": message}), status


def parse_pagination():
    """Read page/page_size query params with sane bounds."""
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.args.get("page_size", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        page_size = DEFAULT_PAGE_SIZE
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    return page, page_size


def paginate(data, page, page_size):
    """Slice a list into a page and return a pagination envelope."""
    total = len(data)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "data": serialize(data[start:end]),
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


def get_body():
    return request.get_json(silent=True) or {}


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

PROPERTY_FIELDS = ("name", "address", "rent_amount", "description",
                   "property_type", "bedrooms", "bathrooms", "is_occupied")


@app.route("/api/properties", methods=["GET"])
def list_properties():
    page, page_size = parse_pagination()
    query = supabase.table("properties").select("*")
    prop_type = request.args.get("property_type")
    if prop_type:
        query = query.eq("property_type", prop_type)
    occupied = request.args.get("is_occupied")
    if occupied is not None:
        query = query.eq("is_occupied", occupied.lower() in ("1", "true", "yes"))
    result = query.order("created_at", desc=True).execute()
    return jsonify(paginate(result.data or [], page, page_size))


@app.route("/api/properties", methods=["POST"])
def create_property():
    body = get_body()
    if not body.get("name") or not body.get("address"):
        return error_response("name and address are required", 422)
    payload = {k: body[k] for k in PROPERTY_FIELDS if k in body}
    result = supabase.table("properties").insert(payload).execute()
    return jsonify(serialize(result.data[0] if result.data else None)), 201


@app.route("/api/properties/<property_id>", methods=["GET"])
def get_property(property_id):
    result = supabase.table("properties").select("*").eq("id", property_id).maybeSingle().execute()
    if not result.data:
        return error_response("property not found", 404)
    return jsonify(serialize(result.data))


@app.route("/api/properties/<property_id>", methods=["PUT"])
def update_property(property_id):
    body = get_body()
    updates = {k: body[k] for k in PROPERTY_FIELDS if k in body}
    if not updates:
        return error_response("no updatable fields supplied", 422)
    updates["updated_at"] = datetime.utcnow().isoformat()
    result = supabase.table("properties").update(updates).eq("id", property_id).execute()
    if not result.data:
        return error_response("property not found", 404)
    return jsonify(serialize(result.data[0]))


@app.route("/api/properties/<property_id>", methods=["DELETE"])
def delete_property(property_id):
    supabase.table("properties").delete().eq("id", property_id).execute()
    return jsonify({"deleted": property_id})


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------

TENANT_FIELDS = ("name", "email", "phone", "property_id",
                 "lease_start", "lease_end", "is_active")


@app.route("/api/tenants", methods=["GET"])
def list_tenants():
    page, page_size = parse_pagination()
    query = supabase.table("tenants").select("*, properties(*)")
    if request.args.get("property_id"):
        query = query.eq("property_id", request.args["property_id"])
    if request.args.get("is_active") is not None:
        query = query.eq("is_active", request.args["is_active"].lower() in ("1", "true", "yes"))
    result = query.order("created_at", desc=True).execute()
    return jsonify(paginate(result.data or [], page, page_size))


@app.route("/api/tenants", methods=["POST"])
def create_tenant():
    body = get_body()
    if not body.get("name"):
        return error_response("name is required", 422)
    payload = {k: body[k] for k in TENANT_FIELDS if k in body}
    result = supabase.table("tenants").insert(payload).execute()
    return jsonify(serialize(result.data[0] if result.data else None)), 201


@app.route("/api/tenants/<tenant_id>", methods=["GET"])
def get_tenant(tenant_id):
    result = supabase.table("tenants").select("*, properties(*)").eq("id", tenant_id).maybeSingle().execute()
    if not result.data:
        return error_response("tenant not found", 404)
    return jsonify(serialize(result.data))


@app.route("/api/tenants/<tenant_id>", methods=["PUT"])
def update_tenant(tenant_id):
    body = get_body()
    updates = {k: body[k] for k in TENANT_FIELDS if k in body}
    if not updates:
        return error_response("no updatable fields supplied", 422)
    updates["updated_at"] = datetime.utcnow().isoformat()
    result = supabase.table("tenants").update(updates).eq("id", tenant_id).execute()
    if not result.data:
        return error_response("tenant not found", 404)
    return jsonify(serialize(result.data[0]))


@app.route("/api/tenants/<tenant_id>", methods=["DELETE"])
def delete_tenant(tenant_id):
    supabase.table("tenants").delete().eq("id", tenant_id).execute()
    return jsonify({"deleted": tenant_id})


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

PAYMENT_FIELDS = ("tenant_id", "amount", "payment_date", "status",
                  "payment_method", "notes")


@app.route("/api/payments", methods=["GET"])
def list_payments():
    page, page_size = parse_pagination()
    query = supabase.table("payments").select("*, tenants(*)")
    if request.args.get("tenant_id"):
        query = query.eq("tenant_id", request.args["tenant_id"])
    if request.args.get("status"):
        query = query.eq("status", request.args["status"])
    if request.args.get("payment_method"):
        query = query.eq("payment_method", request.args["payment_method"])
    result = query.order("payment_date", desc=True).execute()
    return jsonify(paginate(result.data or [], page, page_size))


@app.route("/api/payments", methods=["POST"])
def create_payment():
    body = get_body()
    if not body.get("tenant_id") or body.get("amount") is None:
        return error_response("tenant_id and amount are required", 422)
    payload = {k: body[k] for k in PAYMENT_FIELDS if k in body}
    result = supabase.table("payments").insert(payload).execute()
    return jsonify(serialize(result.data[0] if result.data else None)), 201


@app.route("/api/payments/<payment_id>", methods=["GET"])
def get_payment(payment_id):
    result = supabase.table("payments").select("*, tenants(*)").eq("id", payment_id).maybeSingle().execute()
    if not result.data:
        return error_response("payment not found", 404)
    return jsonify(serialize(result.data))


@app.route("/api/payments/<payment_id>", methods=["PUT"])
def update_payment(payment_id):
    body = get_body()
    updates = {k: body[k] for k in PAYMENT_FIELDS if k in body}
    if not updates:
        return error_response("no updatable fields supplied", 422)
    updates["updated_at"] = datetime.utcnow().isoformat()
    result = supabase.table("payments").update(updates).eq("id", payment_id).execute()
    if not result.data:
        return error_response("payment not found", 404)
    return jsonify(serialize(result.data[0]))


@app.route("/api/payments/<payment_id>", methods=["DELETE"])
def delete_payment(payment_id):
    supabase.table("payments").delete().eq("id", payment_id).execute()
    return jsonify({"deleted": payment_id})


# ---------------------------------------------------------------------------
# Leases
# ---------------------------------------------------------------------------

LEASE_FIELDS = ("property_id", "tenant_id", "start_date", "end_date",
                "deposit_amount", "status")


@app.route("/api/leases", methods=["GET"])
def list_leases():
    page, page_size = parse_pagination()
    query = supabase.table("leases").select("*, properties(*), tenants(*)")
    if request.args.get("property_id"):
        query = query.eq("property_id", request.args["property_id"])
    if request.args.get("tenant_id"):
        query = query.eq("tenant_id", request.args["tenant_id"])
    if request.args.get("status"):
        query = query.eq("status", request.args["status"])
    result = query.order("created_at", desc=True).execute()
    return jsonify(paginate(result.data or [], page, page_size))


@app.route("/api/leases", methods=["POST"])
def create_lease():
    body = get_body()
    if not body.get("property_id") or not body.get("tenant_id"):
        return error_response("property_id and tenant_id are required", 422)
    if not body.get("start_date") or not body.get("end_date"):
        return error_response("start_date and end_date are required", 422)
    payload = {k: body[k] for k in LEASE_FIELDS if k in body}
    result = supabase.table("leases").insert(payload).execute()
    return jsonify(serialize(result.data[0] if result.data else None)), 201


@app.route("/api/leases/<lease_id>", methods=["GET"])
def get_lease(lease_id):
    result = supabase.table("leases").select("*, properties(*), tenants(*)").eq("id", lease_id).maybeSingle().execute()
    if not result.data:
        return error_response("lease not found", 404)
    return jsonify(serialize(result.data))


@app.route("/api/leases/<lease_id>", methods=["PUT"])
def update_lease(lease_id):
    body = get_body()
    updates = {k: body[k] for k in LEASE_FIELDS if k in body}
    if not updates:
        return error_response("no updatable fields supplied", 422)
    result = supabase.table("leases").update(updates).eq("id", lease_id).execute()
    if not result.data:
        return error_response("lease not found", 404)
    return jsonify(serialize(result.data[0]))


@app.route("/api/leases/<lease_id>", methods=["DELETE"])
def delete_lease(lease_id):
    supabase.table("leases").delete().eq("id", lease_id).execute()
    return jsonify({"deleted": lease_id})


# ---------------------------------------------------------------------------
# Maintenance Requests
# ---------------------------------------------------------------------------

MAINTENANCE_FIELDS = ("property_id", "tenant_id", "title", "description",
                      "priority", "status")


@app.route("/api/maintenance", methods=["GET"])
def list_maintenance():
    page, page_size = parse_pagination()
    query = supabase.table("maintenance_requests").select("*, properties(*), tenants(*)")
    if request.args.get("property_id"):
        query = query.eq("property_id", request.args["property_id"])
    if request.args.get("status"):
        query = query.eq("status", request.args["status"])
    if request.args.get("priority"):
        query = query.eq("priority", request.args["priority"])
    result = query.order("created_at", desc=True).execute()
    return jsonify(paginate(result.data or [], page, page_size))


@app.route("/api/maintenance", methods=["POST"])
def create_maintenance():
    body = get_body()
    if not body.get("property_id") or not body.get("title"):
        return error_response("property_id and title are required", 422)
    payload = {k: body[k] for k in MAINTENANCE_FIELDS if k in body}
    result = supabase.table("maintenance_requests").insert(payload).execute()
    return jsonify(serialize(result.data[0] if result.data else None)), 201


@app.route("/api/maintenance/<request_id>", methods=["GET"])
def get_maintenance(request_id):
    result = supabase.table("maintenance_requests").select("*, properties(*), tenants(*)").eq("id", request_id).maybeSingle().execute()
    if not result.data:
        return error_response("maintenance request not found", 404)
    return jsonify(serialize(result.data))


@app.route("/api/maintenance/<request_id>", methods=["PUT"])
def update_maintenance(request_id):
    body = get_body()
    updates = {k: body[k] for k in MAINTENANCE_FIELDS if k in body}
    if not updates:
        return error_response("no updatable fields supplied", 422)
    updates["updated_at"] = datetime.utcnow().isoformat()
    result = supabase.table("maintenance_requests").update(updates).eq("id", request_id).execute()
    if not result.data:
        return error_response("maintenance request not found", 404)
    return jsonify(serialize(result.data[0]))


@app.route("/api/maintenance/<request_id>", methods=["DELETE"])
def delete_maintenance(request_id):
    supabase.table("maintenance_requests").delete().eq("id", request_id).execute()
    return jsonify({"deleted": request_id})


# ---------------------------------------------------------------------------
# Dashboard / analytics
# ---------------------------------------------------------------------------

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    """Aggregate portfolio overview: counts, rent totals, payment breakdown."""
    properties = supabase.table("properties").select("rent_amount,is_occupied").execute().data or []
    tenants = supabase.table("tenants").select("id,is_active").execute().data or []
    payments = supabase.table("payments").select("amount,status").execute().data or []
    leases = supabase.table("leases").select("status").execute().data or []
    maintenance = supabase.table("maintenance_requests").select("status,priority").execute().data or []

    expected = sum(float(p["rent_amount"]) for p in properties)
    collected = sum(float(p["amount"]) for p in payments if p.get("status") == "paid")
    pending = sum(float(p["amount"]) for p in payments if p.get("status") == "pending")
    overdue = sum(float(p["amount"]) for p in payments if p.get("status") == "overdue")

    maintenance_by_status = {}
    for m in maintenance:
        s = m.get("status", "open")
        maintenance_by_status[s] = maintenance_by_status.get(s, 0) + 1

    return jsonify({
        "property_count": len(properties),
        "occupied_count": sum(1 for p in properties if p.get("is_occupied")),
        "tenant_count": len(tenants),
        "active_tenant_count": sum(1 for t in tenants if t.get("is_active")),
        "payment_count": len(payments),
        "active_lease_count": sum(1 for l in leases if l.get("status") == "active"),
        "expected_monthly_rent": expected,
        "collected": collected,
        "pending": pending,
        "overdue": overdue,
        "maintenance_open": maintenance_by_status.get("open", 0) + maintenance_by_status.get("in_progress", 0),
        "maintenance_by_status": maintenance_by_status,
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "rentmaster-gh",
        "version": "2.0.0",
    })


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "name": "RentMaster-GH API",
        "version": "2.0.0",
        "endpoints": [
            "/api/properties",
            "/api/tenants",
            "/api/payments",
            "/api/leases",
            "/api/maintenance",
            "/api/dashboard",
            "/api/health",
        ],
    })


# Vercel serverless entrypoint
app = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
