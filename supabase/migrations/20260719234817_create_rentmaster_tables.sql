/*
# RentMaster-GH: Create properties, tenants, and payments tables

## Overview
Creates the core schema for a rental management application. This is a
single-tenant app (no sign-in screen), so all policies allow both the
`anon` and `authenticated` roles to perform full CRUD on shared/public data.

## New Tables

1. `properties`
   - `id` (uuid, primary key, auto-generated)
   - `name` (text, not null) - display name of the property
   - `address` (text, not null) - street address of the property
   - `rent_amount` (numeric, not null, default 0) - monthly rent in USD
   - `created_at` (timestamptz, default now())

2. `tenants`
   - `id` (uuid, primary key, auto-generated)
   - `name` (text, not null) - tenant full name
   - `email` (text) - contact email (nullable)
   - `phone` (text) - contact phone (nullable)
   - `property_id` (uuid, foreign key -> properties.id, on delete cascade)
   - `created_at` (timestamptz, default now())

3. `payments`
   - `id` (uuid, primary key, auto-generated)
   - `tenant_id` (uuid, foreign key -> tenants.id, on delete cascade)
   - `amount` (numeric, not null, default 0) - payment amount in USD
   - `payment_date` (date, not null) - when the payment was made
   - `status` (text, not null, default 'pending') - pending | paid | overdue
   - `created_at` (timestamptz, default now())

## Indexes
- `tenants_property_id_idx` on tenants(property_id) for join performance
- `payments_tenant_id_idx` on payments(tenant_id) for join performance

## Security (RLS)
- RLS enabled on all three tables.
- Four policies (SELECT/INSERT/UPDATE/DELETE) per table, scoped to
  `TO anon, authenticated` with `USING (true)` / `WITH CHECK (true)`
  because the data is intentionally shared/public (single-tenant, no auth).

## Notes
1. All tables use `gen_random_uuid()` for primary keys.
2. Foreign keys cascade on delete so removing a property clears its tenants,
   and removing a tenant clears their payments.
3. `status` on payments is free text constrained by the app layer to one of
   pending | paid | overdue.
*/

CREATE TABLE IF NOT EXISTS properties (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  address text NOT NULL,
  rent_amount numeric(10, 2) NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tenants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  email text,
  phone text,
  property_id uuid REFERENCES properties(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  amount numeric(10, 2) NOT NULL DEFAULT 0,
  payment_date date NOT NULL DEFAULT CURRENT_DATE,
  status text NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tenants_property_id_idx ON tenants(property_id);
CREATE INDEX IF NOT EXISTS payments_tenant_id_idx ON payments(tenant_id);

ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;

-- properties policies
DROP POLICY IF EXISTS "anon_select_properties" ON properties;
CREATE POLICY "anon_select_properties" ON properties FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_properties" ON properties;
CREATE POLICY "anon_insert_properties" ON properties FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_properties" ON properties;
CREATE POLICY "anon_update_properties" ON properties FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_properties" ON properties;
CREATE POLICY "anon_delete_properties" ON properties FOR DELETE
  TO anon, authenticated USING (true);

-- tenants policies
DROP POLICY IF EXISTS "anon_select_tenants" ON tenants;
CREATE POLICY "anon_select_tenants" ON tenants FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_tenants" ON tenants;
CREATE POLICY "anon_insert_tenants" ON tenants FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_tenants" ON tenants;
CREATE POLICY "anon_update_tenants" ON tenants FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_tenants" ON tenants;
CREATE POLICY "anon_delete_tenants" ON tenants FOR DELETE
  TO anon, authenticated USING (true);

-- payments policies
DROP POLICY IF EXISTS "anon_select_payments" ON payments;
CREATE POLICY "anon_select_payments" ON payments FOR SELECT
  TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_payments" ON payments;
CREATE POLICY "anon_insert_payments" ON payments FOR INSERT
  TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_payments" ON payments;
CREATE POLICY "anon_update_payments" ON payments FOR UPDATE
  TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_payments" ON payments;
CREATE POLICY "anon_delete_payments" ON payments FOR DELETE
  TO anon, authenticated USING (true);
