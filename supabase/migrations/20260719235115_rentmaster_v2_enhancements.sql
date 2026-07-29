/*
# RentMaster-GH V2: Enhanced rental management schema

## Overview
Upgrades the RentMaster schema to Version 2. Adds lease tracking,
maintenance requests, and audit fields. Extends existing tables with
new columns (additive only - no data loss). This is a single-tenant app
with no sign-in screen, so all policies allow `anon` + `authenticated`
full CRUD on intentionally shared data.

## New Tables

1. `leases`
   - `id` (uuid, pk)
   - `property_id` (uuid, fk -> properties, on delete cascade)
   - `tenant_id` (uuid, fk -> tenants, on delete cascade)
   - `start_date` (date, not null)
   - `end_date` (date, not null)
   - `deposit_amount` (numeric, default 0)
   - `status` (text, default 'active') - active | expired | terminated
   - `created_at` (timestamptz)

2. `maintenance_requests`
   - `id` (uuid, pk)
   - `property_id` (uuid, fk -> properties, on delete cascade)
   - `tenant_id` (uuid, fk -> tenants, on delete set null) - nullable, may be filed by owner
   - `title` (text, not null)
   - `description` (text)
   - `priority` (text, default 'medium') - low | medium | high | urgent
   - `status` (text, default 'open') - open | in_progress | resolved | closed
   - `created_at` (timestamptz)
   - `updated_at` (timestamptz, default now())

## Modified Tables

1. `properties`
   - ADD `description` (text, nullable) - free-form property notes
   - ADD `property_type` (text, default 'apartment') - apartment | house | commercial | other
   - ADD `bedrooms` (int, default 1)
   - ADD `bathrooms` (int, default 1)
   - ADD `is_occupied` (bool, default false) - quick occupancy flag
   - ADD `updated_at` (timestamptz, default now())

2. `tenants`
   - ADD `lease_start` (date, nullable) - current lease start
   - ADD `lease_end` (date, nullable) - current lease end
   - ADD `is_active` (bool, default true)
   - ADD `updated_at` (timestamptz, default now())

3. `payments`
   - ADD `payment_method` (text, default 'cash') - cash | card | bank_transfer | check | other
   - ADD `notes` (text, nullable)
   - ADD `updated_at` (timestamptz, default now())

## Indexes
- `leases_property_id_idx` on leases(property_id)
- `leases_tenant_id_idx` on leases(tenant_id)
- `leases_status_idx` on leases(status)
- `maintenance_requests_property_id_idx` on maintenance_requests(property_id)
- `maintenance_requests_status_idx` on maintenance_requests(status)
- `maintenance_requests_priority_idx` on maintenance_requests(priority)
- `payments_status_idx` on payments(status)
- `payments_payment_date_idx` on payments(payment_date)

## Security (RLS)
- RLS enabled on `leases` and `maintenance_requests`.
- Four policies (SELECT/INSERT/UPDATE/DELETE) per new table, scoped to
  `TO anon, authenticated` with `USING (true)` / `WITH CHECK (true)`
  because the data is intentionally shared/public (single-tenant, no auth).

## Notes
1. All column additions use `IF NOT EXISTS` via DO $$ blocks so the
   migration is idempotent and safe to re-run.
2. No columns dropped, renamed, or retyped - zero data loss.
3. `updated_at` columns are maintained by the application layer on writes.
*/

-- Additive columns on properties
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'properties' AND column_name = 'description') THEN
    ALTER TABLE properties ADD COLUMN description text;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'properties' AND column_name = 'property_type') THEN
    ALTER TABLE properties ADD COLUMN property_type text NOT NULL DEFAULT 'apartment';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'properties' AND column_name = 'bedrooms') THEN
    ALTER TABLE properties ADD COLUMN bedrooms integer NOT NULL DEFAULT 1;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'properties' AND column_name = 'bathrooms') THEN
    ALTER TABLE properties ADD COLUMN bathrooms integer NOT NULL DEFAULT 1;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'properties' AND column_name = 'is_occupied') THEN
    ALTER TABLE properties ADD COLUMN is_occupied boolean NOT NULL DEFAULT false;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'properties' AND column_name = 'updated_at') THEN
    ALTER TABLE properties ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
  END IF;
END $$;

-- Additive columns on tenants
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'tenants' AND column_name = 'lease_start') THEN
    ALTER TABLE tenants ADD COLUMN lease_start date;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'tenants' AND column_name = 'lease_end') THEN
    ALTER TABLE tenants ADD COLUMN lease_end date;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'tenants' AND column_name = 'is_active') THEN
    ALTER TABLE tenants ADD COLUMN is_active boolean NOT NULL DEFAULT true;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'tenants' AND column_name = 'updated_at') THEN
    ALTER TABLE tenants ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
  END IF;
END $$;

-- Additive columns on payments
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'payments' AND column_name = 'payment_method') THEN
    ALTER TABLE payments ADD COLUMN payment_method text NOT NULL DEFAULT 'cash';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'payments' AND column_name = 'notes') THEN
    ALTER TABLE payments ADD COLUMN notes text;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_name = 'payments' AND column_name = 'updated_at') THEN
    ALTER TABLE payments ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
  END IF;
END $$;

-- New table: leases
CREATE TABLE IF NOT EXISTS leases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  start_date date NOT NULL,
  end_date date NOT NULL,
  deposit_amount numeric(10, 2) NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now()
);

-- New table: maintenance_requests
CREATE TABLE IF NOT EXISTS maintenance_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  property_id uuid NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  tenant_id uuid REFERENCES tenants(id) ON DELETE SET NULL,
  title text NOT NULL,
  description text,
  priority text NOT NULL DEFAULT 'medium',
  status text NOT NULL DEFAULT 'open',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS leases_property_id_idx ON leases(property_id);
CREATE INDEX IF NOT EXISTS leases_tenant_id_idx ON leases(tenant_id);
CREATE INDEX IF NOT EXISTS leases_status_idx ON leases(status);
CREATE INDEX IF NOT EXISTS maintenance_requests_property_id_idx ON maintenance_requests(property_id);
CREATE INDEX IF NOT EXISTS maintenance_requests_status_idx ON maintenance_requests(status);
CREATE INDEX IF NOT EXISTS maintenance_requests_priority_idx ON maintenance_requests(priority);
CREATE INDEX IF NOT EXISTS payments_status_idx ON payments(status);
CREATE INDEX IF NOT EXISTS payments_payment_date_idx ON payments(payment_date);

-- RLS on new tables
ALTER TABLE leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_requests ENABLE ROW LEVEL SECURITY;

-- leases policies
DROP POLICY IF EXISTS "anon_select_leases" ON leases;
CREATE POLICY "anon_select_leases" ON leases FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_leases" ON leases;
CREATE POLICY "anon_insert_leases" ON leases FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_leases" ON leases;
CREATE POLICY "anon_update_leases" ON leases FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_leases" ON leases;
CREATE POLICY "anon_delete_leases" ON leases FOR DELETE
  TO anon, authenticated USING (true);

-- maintenance_requests policies
DROP POLICY IF EXISTS "anon_select_maintenance" ON maintenance_requests;
CREATE POLICY "anon_select_maintenance" ON maintenance_requests FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_maintenance" ON maintenance_requests;
CREATE POLICY "anon_insert_maintenance" ON maintenance_requests FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_maintenance" ON maintenance_requests;
CREATE POLICY "anon_update_maintenance" ON maintenance_requests FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_maintenance" ON maintenance_requests;
CREATE POLICY "anon_delete_maintenance" ON maintenance_requests FOR DELETE
  TO anon, authenticated USING (true);
