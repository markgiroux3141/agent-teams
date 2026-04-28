# `/v2/coupons/apply` Schema Specification

## Endpoint
POST `/v2/coupons/apply`

## Request Schema

```json
{
  "coupon_code": "string (required)",
  "user_id": "string (required)",
  "cart_total": "number (required, in cents)",
  "currency": "string (optional, default: 'USD')"
}
```

### Request Fields
- **coupon_code**: The promo/coupon code entered by user (e.g., "SAVE20", "WELCOME10")
- **user_id**: UUID of authenticated user applying coupon
- **cart_total**: Total cart amount in cents (e.g., 12999 = $129.99)
- **currency**: ISO 4217 currency code (optional, defaults to USD)

## Response Schema (Success - 200)

```json
{
  "applied": true,
  "discount_amount": number,
  "discount_type": "FIXED|PERCENTAGE",
  "discount_percent": number,
  "discount_description": "string",
  "expires_at": "ISO 8601 timestamp",
  "coupon_id": "string",
  "new_total": number
}
```

### Response Fields
- **applied**: Boolean - whether discount was successfully applied
- **discount_amount**: Absolute discount in cents (e.g., 2000 = $20.00)
- **discount_type**: Either "FIXED" (flat amount) or "PERCENTAGE" (percent off)
- **discount_percent**: Percentage value if type is PERCENTAGE (e.g., 20 for 20%)
- **discount_description**: Human-readable discount text (e.g., "20% off your order")
- **expires_at**: ISO 8601 timestamp of when coupon expires
- **coupon_id**: Backend coupon ID for audit/transaction logging
- **new_total**: Updated cart total after discount in cents

## Response Schema (Error - 400/404/422)

```json
{
  "applied": false,
  "error": "string",
  "error_code": "INVALID_COUPON|EXPIRED|ALREADY_USED|INELIGIBLE|AMOUNT_MISMATCH"
}
```

### Error Codes
- **INVALID_COUPON**: Code doesn't exist or is malformed
- **EXPIRED**: Coupon has passed expiration date
- **ALREADY_USED**: User has already used this coupon
- **INELIGIBLE**: User doesn't meet eligibility criteria (min spend, geography, etc.)
- **AMOUNT_MISMATCH**: Cart amount outside coupon's valid range

## Implementation Notes
- Discount object used throughout checkout flow to update order total
- Applied coupon persists in transaction record for audit compliance (required Monday onward)
- No multi-coupon stacking (apply one coupon only)

## Source
Frontend checkout mock implementation, built against sprint planning requirements.
