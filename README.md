# RentMaster-GH v2

A rental management backend built with Flask and Supabase. Manages properties,
tenants, payments, leases, and maintenance requests through a paginated JSON
REST API. Deployable to Vercel.

## What's new in v2

- **Leases** - track lease terms, deposits, and status per property/tenant
- **Maintenance requests** - file and triage issues with priority and status
- **Pagination** - all list endpoints support `page` and `page_size`
- **Filtering** - filter by property type, occupancy, payment status, etc.
- **Richer dashboard** - occupancy, active leases, payment breakdown,
  maintenance summary
- **Audit timestamps** - `updated_at` on mutable records

## API

### Properties
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/properties` | List (paginated, `?property_type=`, `?is_occupied=`) |
| POST   | `/api/properties` | Create |
| GET    | `/api/properties/:id` | Get one |
| PUT    | `/api/properties/:id` | Update |
| DELETE | `/api/properties/:id` | Delete |

### Tenants
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/tenants` | List (`?property_id=`, `?is_active=`) |
| POST   | `/api/tenants` | Create |
| GET    | `/api/tenants/:id` | Get one |
| PUT    | `/api/tenants/:id` | Update |
| DELETE | `/api/tenants/:id` | Delete |

### Payments
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/payments` | List (`?tenant_id=`, `?status=`, `?payment_method=`) |
| POST   | `/api/payments` | Create |
| GET    | `/api/payments/:id` | Get one |
| PUT    | `/api/payments/:id` | Update |
| DELETE | `/api/payments/:id` | Delete |

### Leases
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/leases` | List (`?property_id=`, `?tenant_id=`, `?status=`) |
| POST   | `/api/leases` | Create |
| GET    | `/api/leases/:id` | Get one |
| PUT    | `/api/leases/:id` | Update |
| DELETE | `/api/leases/:id` | Delete |

### Maintenance
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/maintenance` | List (`?property_id=`, `?status=`, `?priority=`) |
| POST   | `/api/maintenance` | Create |
| GET    | `/api/maintenance/:id` | Get one |
| PUT    | `/api/maintenance/:id` | Update |
| DELETE | `/api/maintenance/:id` | Delete |

### Other
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/dashboard` | Portfolio overview and analytics |
| GET    | `/api/health` | Health check |
| GET    | `/` | API index |

### Pagination
All list endpoints return:
```json
{
  "data": [...],
  "page": 1,
  "page_size": 20,
  "total": 42,
  "total_pages": 3
}
```
Pass `?page=2&page_size=50` to navigate. Max page size is 100.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase URL and anon key
python app.py          # serves on http://localhost:5000
```

## Deploy to Vercel

Import the repo on Vercel - `vercel.json` configures the Python runtime.
Set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` as Vercel environment
variables.

## Tech

- Flask
- supabase-py
- python-dotenv
- gunicorn
