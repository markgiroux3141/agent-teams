# Coupon Endpoint Decision — 2026-04-22

## Status

`/v2/coupons/apply` endpoint is **NOT in current v2.yaml**.

## Decision

**ADDING TODAY.** Committed to frontend.

## Schema

Awaiting frontend confirmation on exact request/response structure for the discount object.

Frontend is building against a mock from last sprint:
- Endpoint: `/v2/coupons/apply`
- Returns: discount object (exact shape TBD per frontend's incoming spec)

## Timeline

- Frontend provides schema spec → ETA 2 hours to wire and push v2.yaml update
- Unblocks frontend's coupon flow implementation
- Supports Friday ship with feature parity

## Next Step

1. Frontend provides discount object schema
2. Backend adds endpoint to v2.yaml with proper types
3. Backend confirms update to frontend + pushes staging deploy
4. Frontend resumes coupon flow work
