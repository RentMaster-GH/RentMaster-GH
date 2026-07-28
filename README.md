# RentMaster-GH v2

A rental property management web app built with **Streamlit** and **Supabase**.
Manages properties, tenants, payments, leases, and maintenance requests
through a full interactive dashboard UI.

## Tech Stack

- **Python 3.11** + **Streamlit** (interactive web app, not a static site)
- **Supabase** (PostgreSQL database with RLS)
- **python-dotenv** (environment variables from `.env`)

## Features

- Dashboard with portfolio analytics (occupancy, rent totals, payment breakdown)
- Full CRUD for properties, tenants, payments, leases, and maintenance requests
- File upload support (up to 200 MB via `server.maxUploadSize`)
- WebSocket-enabled for real-time updates
- Custom domain ready (deploy to any host that supports Streamlit)

## Local Development

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in Supabase URL and anon key
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

App serves on `http://localhost:8501`.

## Deployment

### Streamlit config

`.streamlit/config.toml` is preconfigured with:
- `server.maxUploadSize = 200` (200 MB file uploads)
- `server.enableWebsocketActivation = true` (websockets on)
- `server.headless = true` (no browser auto-open)
- `server.address = "0.0.0.0"` (bind to all interfaces)

### Heroku / Render / Railway (recommended for Streamlit)

A `Procfile` is included:
```
web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
```

Deploy steps:
1. Push to your hosting provider (Heroku, Render, Railway, etc.)
2. Set environment variables: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
3. The app runs as a server process (not a static site)

### Custom Domain

After deploying, add a custom domain through your hosting provider's
dashboard. Most providers (Heroku, Render, Railway) let you add a custom
domain and provide DNS records to point your domain to the app.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_SUPABASE_URL` | Your Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Your Supabase anon (public) key |

Copy `.env.example` to `.env` and fill in the values.

## Database

The app uses 5 Supabase tables with Row Level Security enabled:
- `properties` - rental units with type, bedrooms, bathrooms, occupancy
- `tenants` - tenant records linked to properties
- `payments` - rent payments with status and method
- `leases` - lease terms with deposit and status
- `maintenance_requests` - filed issues with priority and status

Migrations are in `supabase/migrations/`.

## Running

The app stays running as a server process. Streamlit's built-in server
handles WebSocket connections for real-time UI updates and file uploads.
