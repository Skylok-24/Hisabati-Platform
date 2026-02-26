# Seller Announcements Management API

This document describes the APIs for authenticated sellers to manage their announcements.

## Authentication

All endpoints (except public ones) require a valid JWT access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Endpoints

### 1. List Seller's Announcements
**GET** `/api/seller/announcements/`

List all announcements created by the authenticated seller.

**Permissions**: Authenticated users (sellers)

**Response**:
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Premium Instagram Account",
      "description": "Active account with 1M followers",
      "price_original": 500,
      "price_usd": 500.00,
      "followers": 1000000,
      "account_created_at": "2023-01-15",
      "status": "active",
      "created_at": "2024-02-20T10:30:00Z",
      "account_link": "https://instagram.com/example",
      "category": "Social Media",
      "seller": {
        "email": "seller@example.com",
        "description": "Trusted seller",
        "whatsapp": "+1234567890",
        "country": {
          "name": "Egypt",
          "currency_code": "EGP",
          "currency_name": "Egyptian Pound",
          "rate_to_usd": 1.0
        }
      }
    }
  ]
}
```

### 2. Get Announcement Details (Seller)
**GET** `/api/seller/announcements/{id}/`

Retrieve details of a specific announcement (seller's own).

**Permissions**: Authenticated, must own the announcement

**Response**: Same as single announcement from list endpoint

### 3. Update Seller's Announcement
**PATCH** `/api/seller/announcements/{id}/`

Update an announcement. Only the seller who created it can update.

**Permissions**: Authenticated, must own the announcement

**Editable Fields**:
- `title` (string, max 50 chars)
- `description` (string)
- `price_original` (decimal, must be > 0)
- `followers` (integer)
- `account_created_at` (date)
- `status` (choice: 'active', 'sold', 'inactive')
- `account_link` (URL)
- `category_id` (integer, category ID)

**Request Example**:
```json
{
  "title": "Updated Premium Account",
  "price_original": 600,
  "status": "active",
  "description": "Updated description"
}
```

**Response**: Updated announcement details (same format as GET)

### 4. Delete Seller's Announcement
**DELETE** `/api/seller/announcements/{id}/`

Delete an announcement. Only the seller who created it can delete.

**Permissions**: Authenticated, must own the announcement

**Response**: 204 No Content (successful deletion) or error response

### 5. Get Public Announcement Details
**GET** `/api/announcements/{id}/`

Retrieve details of any announcement (public endpoint).

**Permissions**: Authenticated users (anyone)

**Response**: Same announcement details format

### 6. Update Public Announcement
**PATCH** `/api/announcements/{id}/`

Update an announcement via the public endpoint. Only the seller who owns it can update.

**Permissions**: Authenticated, must own the announcement

**Note**: Same as seller update endpoint, just different URL path

### 7. Delete Public Announcement
**DELETE** `/api/announcements/{id}/`

Delete an announcement via the public endpoint. Only the seller who owns it can delete.

**Permissions**: Authenticated, must own the announcement

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 400 Bad Request
```json
{
  "field_name": ["Error message"],
  "another_field": ["Another error"]
}
```

**Example Validation Error**:
```json
{
  "price_original": ["Price must be greater than 0"],
  "status": ["Status must be one of ['active', 'sold', 'inactive']"]
}
```

## Status Field Values

Valid status values for announcements:
- `active` - Announcement is active and visible
- `sold` - Item has been sold
- `inactive` - Announcement is inactive

## Example Workflows

### Workflow 1: List, Update, and Delete
```bash
# 1. Get your announcements
curl -X GET http://localhost:8000/api/seller/announcements/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 2. Update an announcement
curl -X PATCH http://localhost:8000/api/seller/announcements/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New Title",
    "price_original": 750
  }'

# 3. Delete an announcement
curl -X DELETE http://localhost:8000/api/seller/announcements/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Workflow 2: Mark as Sold
```bash
curl -X PATCH http://localhost:8000/api/seller/announcements/1/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "sold"
  }'
```

## Notes

1. **Price Conversion**: When you update `price_original`, the `price_usd` is automatically calculated based on the seller's country exchange rate.

2. **Author Verification**: The system ensures that only the seller who created an announcement can update or delete it.

3. **Pagination**: List endpoints return paginated results (10 per page by default).

4. **Read-only Fields**: The following fields cannot be modified:
   - `id`
   - `created_at`
   - `price_usd` (automatically calculated)

5. **Category**: When updating, use `category_id` (integer) in the request body, not `category` name.
