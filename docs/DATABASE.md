# Vouchly — Database Architecture & Schema

Vouchly uses **MongoDB** with PyMongo. All document schemas and indexes are outlined below.

---

## Collections & Schemas

### 1. `owners`
Business owners who create spaces and moderate testimonials.

```javascript
{
  "_id": ObjectId("..."),
  "full_name": "Jane Doe",
  "email": "jane@example.com",           // Indexed, unique, lowercase
  "password_hash": "scrypt:32768:8:1...",
  "business_name": "Acme Inc.",
  "brand_color": "#B89A5A",
  "email_verified": true,
  "is_active": true,
  "created_at": ISODate("2026-09-19T..."),
  "updated_at": ISODate("2026-09-19T...")
}
```

### 2. `spaces`
Testimonial collection campaigns configured by owners.

```javascript
{
  "_id": ObjectId("..."),
  "owner_id": ObjectId("..."),           // Reference to owners._id
  "name": "Acme Product Launch",
  "slug": "acme-launch",                 // Indexed, unique, URL-safe
  "business_name": "Acme Inc.",
  "logo": "static/uploads/logos/uuid.png",
  "brand_color": "#B89A5A",
  "welcome_heading": "Share your experience with Acme!",
  "description": "Tell us how Acme helped your business.",
  "thank_you_message": "Thank you for sharing your feedback!",
  "require_avatar": false,
  "enable_star_rating": true,
  "custom_questions": [
    { "label": "How did you hear about us?", "required": false, "type": "text" }
  ],
  "theme_settings": {
    "background_color": "#F8F6F0",
    "text_color": "#111111"
  },
  "is_active": true,
  "created_at": ISODate("2026-09-19T..."),
  "updated_at": ISODate("2026-09-19T...")
}
```

### 3. `testimonials`
Customer review submissions.

```javascript
{
  "_id": ObjectId("..."),
  "space_id": ObjectId("..."),           // Reference to spaces._id
  "owner_id": ObjectId("..."),           // Denormalized for fast ownership checks
  "customer_name": "Alice Smith",
  "customer_email": "alice@example.com", // Kept private, never in public APIs
  "company_name": "Smith Co.",
  "company_role": "CEO",
  "avatar": "static/uploads/avatars/uuid.jpg",
  "rating": 5,                           // 1–5 or null
  "review_text": "Vouchly revolutionized how we show social proof.",
  "custom_answers": {
    "0": "LinkedIn referral"
  },
  "status": "approved",                  // "pending" | "approved" | "rejected" | "archived"
  "is_featured": true,
  "likes": 3,
  "submitted_at": ISODate("2026-09-19T..."),
  "moderated_at": ISODate("2026-09-19T..."),
  "moderated_by": ObjectId("..."),
  "created_at": ISODate("2026-09-19T..."),
  "updated_at": ISODate("2026-09-19T...")
}
```

### 4. `refresh_tokens`
Long-lived JWT refresh tokens for secure session renewal.

```javascript
{
  "_id": ObjectId("..."),
  "owner_id": ObjectId("..."),
  "token": "...",                        // Indexed, unique
  "is_revoked": false,
  "created_at": ISODate("..."),
  "expires_at": ISODate("...")           // TTL Index: auto-deleted on expiry
}
```

### 5. `email_verification_tokens` & `password_reset_tokens`
One-time tokens for security flows.

```javascript
{
  "_id": ObjectId("..."),
  "owner_id": ObjectId("..."),
  "token": "...",                        // Indexed, unique
  "created_at": ISODate("..."),
  "expires_at": ISODate("...")           // TTL Index: expires after 24 hours
}
```

### 6. `notifications`
In-app alerts for space owners.

```javascript
{
  "_id": ObjectId("..."),
  "owner_id": ObjectId("..."),           // Indexed
  "title": "New Testimonial Received",
  "message": "Alice Smith submitted a testimonial for Acme Launch.",
  "type": "info",                        // "info" | "success" | "warning"
  "is_read": false,
  "created_at": ISODate("...")
}
```

### 7. `moderation_logs`
Audit log of review approval/rejection actions.

```javascript
{
  "_id": ObjectId("..."),
  "owner_id": ObjectId("..."),
  "testimonial_id": ObjectId("..."),
  "action": "approved",
  "prev_status": "pending",
  "new_status": "approved",
  "created_at": ISODate("...")
}
```

### 8. `widget_configurations`
Saved widget embed styling preferences per space.

```javascript
{
  "_id": ObjectId("..."),
  "space_id": ObjectId("..."),
  "owner_id": ObjectId("..."),
  "config": {
    "layout": "grid",                    // "grid" | "carousel" | "badge"
    "theme": "light",                    // "light" | "dark"
    "count": 6,
    "brand_color": "#B89A5A",
    "show_ratings": true,
    "show_avatars": true,
    "show_company": true
  },
  "updated_at": ISODate("...")
}
```

---

## Database Indexes

Executed automatically on application start in `database.init_db(app)`:

| Collection | Index Fields | Properties | Purpose |
|------------|--------------|------------|---------|
| `owners` | `email` (ASC) | `unique=True` | Prevent duplicate email registrations |
| `spaces` | `slug` (ASC) | `unique=True` | Enforce unique public URLs |
| `spaces` | `owner_id` (ASC) | — | Fast lookup of owner's spaces |
| `testimonials` | `space_id` (ASC) | — | Group testimonials by space |
| `testimonials` | `owner_id` (ASC) | — | Ownership verification check |
| `testimonials` | `status` (ASC) | — | Status tab filtering |
| `testimonials` | `submitted_at` (DESC) | — | Date sorting |
| `testimonials` | `space_id` + `status` | Compound | Fast public wall & widget queries |
| `refresh_tokens` | `token` (ASC) | `unique=True` | Token lookup |
| `refresh_tokens` | `expires_at` (ASC) | `expireAfterSeconds=0` | MongoDB TTL auto-cleanup |
| `email_verification_tokens` | `token` (ASC) | `unique=True` | Verification token lookup |
| `email_verification_tokens` | `expires_at` (ASC) | `expireAfterSeconds=0` | Auto-expire after 24h |
| `password_reset_tokens` | `token` (ASC) | `unique=True` | Reset token lookup |
| `password_reset_tokens` | `expires_at` (ASC) | `expireAfterSeconds=0` | Auto-expire after 24h |
| `notifications` | `owner_id` (ASC) | — | User notifications list |
| `notifications` | `created_at` (DESC) | — | Recent notification ordering |
| `moderation_logs`| `owner_id` (ASC) | — | User audit logs |
