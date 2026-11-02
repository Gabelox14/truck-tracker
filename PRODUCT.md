# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two internal user types for a single vehicle-transport (car-hauling) business:

- **Admin / dispatcher** — manages the fleet's master data (trucks, driver accounts, named zones) and reviews trips: sets the amount charged per trip and documents the cargo (car brand + a photo of the VIN) after a driver logs a trip. Admin additionally controls user roles and zones; dispatcher handles day-to-day trucks/drivers.
- **Driver** — uses the app from a phone while on the road. Starts a trip by picking a truck and an origin/destination zone, and marks it as arrived when done. Sees only their own trips. Can submit evidence for their own trips — a photo of each car's VIN and a voice note with route and cost — but never sees amounts; whatever they submit is a proposal that staff confirms.

## Product Purpose

An internal operations tool that replaces informal tracking (paper, chat messages) for a car-hauling business: which truck went where, what vehicles it carried, and what was charged. Not a public product — built for this one operation.

## Positioning

Deliberately not a GPS/real-time location tracker. Trips are tracked by state (in progress / completed) between named zones the admin defines, not live coordinates — no device GPS or connectivity dependency for the driver. What differentiates it from a generic fleet tracker is the per-trip cargo record: each trip logs the car(s) being hauled (brand + a VIN photo) and the amount charged, giving the business a billing-ready audit trail per trip rather than just a location log.

## Operating Context

- Admin/dispatcher works from a desktop-style panel (tabs: Camiones, Choferes, Zonas, Viajes, Usuarios) to manage master data and process trips after the fact.
- Driver works from a phone in the field, often on unreliable mobile connectivity, using a minimal single-screen flow (start trip → mark arrived).
- Zones (named locations like "Bodega Central", "Puerto") are set up by admin in advance; drivers only select from that list.

## Capabilities and Constraints

- Roles: `admin` (full control, incl. zones and role assignment), `dispatcher` (trucks/drivers, same trip visibility as admin), `driver` (own trips only).
- Entities: trucks (plate), drivers (linked 1:1 to a login), zones (admin-managed named locations), trips (driver + truck + origin/destination zone + status + amount + one or more cargo cars, each with a brand and an optional VIN photo).
- Auth is email/password via Supabase Auth; backend verifies sessions itself (JWKS), independent of the frontend.
- Automatic capture: VIN photos and voice notes go through the backend to a private Supabase Storage bucket. Claude reads the VIN (validated by check digit and decoded with NHTSA vPIC); voice notes are transcribed and Claude extracts origin, destination, cost and currency. Anything that doesn't add up is marked "Revisar" and lands in the admin "Por revisar" tab, where staff confirm, correct, or turn unassigned uploads (drafts) into trips. Only admin/dispatcher confirm data, edit cars, and set amounts.
- Amounts are in CRC or USD per trip; the two currencies are never summed together.
- No live GPS tracking by design (see Positioning).
- Driver-facing screens must hold up on a phone over inconsistent mobile connectivity.

## Brand Commitments

Confirmed brand name: "Full Soluciones G&A S.A". Used verbatim in the app header, login screen, browser title, and API title — not abbreviated or shortened.

## Evidence on Hand

None. No real trips, trucks, or driver data exist yet — everything used so far was disposable test data. Future design work must not fabricate sample fleet/trip data as if it were real.

## Product Principles

1. Zone-based trip state, not GPS — the driver's flow must never assume a live location signal.
2. Hard role separation: a driver cannot see billing or other drivers' trips, and can only submit evidence for their own trips — never confirm or edit it.
3. Every trip is auditable after the fact — cargo and amount are recorded per trip, not bolted on separately.
4. Driver surface is mobile-first and minimal; admin/dispatch surface is desktop-oriented and information-dense.
