# Vouchly — API Reference

All API responses follow a consistent JSON format:

```json
// Success response (200, 201)
{
  "success": true,
  "message": "Human-readable status message",
  "data": { ... }
}

// Error response (400, 401, 403, 404, 409, 429, 500)
{
  "success": false,
  "message": "Error description",
  "errors": {
    "field_name": "Specific field validation message"
  }
}
```

---

## Authentication (`/api/auth`)

### 1. Register Owner
- **Endpoint:** `POST /api/auth/signup`
- **Auth required:** No
- **Request Body (JSON):**
  ```json
  {
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "password": "StrongPassword123!",
    "confirm_password": "StrongPassword123!" // optional
  }
  ```
- **Response (201):** Verification token generated and email simulated in console.

### 2. Login Owner
- **Endpoint:** `POST /api/auth/login`
- **Auth required:** No
- **Request Body (JSON):**
  ```json
  {
    "email": "jane@example.com",
    "password": "StrongPassword123!"
  }
  ```
- **Response (200):** Sets `access_token` and `refresh_token` as HttpOnly cookies.

### 3. Current User
- **Endpoint:** `GET /api/auth/me`
- **Auth required:** Yes (`access_token` cookie)
- **Response (200):** Owner profile details.

### 4. Refresh Token
- **Endpoint:** `POST /api/auth/refresh`
- **Auth required:** Yes (`refresh_token` cookie)
- **Response (200):** Sets new rotated `access_token` and `refresh_token` cookies.

### 5. Logout
- **Endpoint:** `POST /api/auth/logout`
- **Auth required:** Yes
- **Response (200):** Clears authentication cookies and revokes refresh token.

### 6. Verify Email
- **Endpoint:** `GET /api/auth/verify-email?token=<token>`
- **Auth required:** No
- **Response (200):** Activates email verification status.

### 7. Forgot Password
- **Endpoint:** `POST /api/auth/forgot-password`
- **Auth required:** No
- **Request Body:** `{ "email": "jane@example.com" }`

### 8. Reset Password
- **Endpoint:** `POST /api/auth/reset-password`
- **Auth required:** No
- **Request Body:** `{ "token": "<token>", "new_password": "NewPassword123!" }`

---

## Spaces (`/api/spaces`)

### 1. List Spaces
- **Endpoint:** `GET /api/spaces`
- **Auth required:** Yes
- **Response (200):** Returns array of spaces owned by current user along with submission counts.

### 2. Create Space
- **Endpoint:** `POST /api/spaces`
- **Auth required:** Yes
- **Content-Type:** `multipart/form-data` or `application/json`
- **Fields:**
  - `name` (required)
  - `slug` (required, unique, URL-safe: `a-z`, `0-9`, `-`)
  - `business_name`
  - `welcome_heading`
  - `description`
  - `thank_you_message`
  - `brand_color` (hex)
  - `enable_star_rating` ("true"/"false")
  - `require_avatar` ("true"/"false")
  - `custom_questions` (JSON string array)
  - `logo` (Image file)

### 3. Get Space Details
- **Endpoint:** `GET /api/spaces/<space_id>`
- **Auth required:** Yes (Ownership verified)

### 4. Update Space
- **Endpoint:** `PATCH /api/spaces/<space_id>`
- **Auth required:** Yes (Ownership verified)

### 5. Delete Space
- **Endpoint:** `DELETE /api/spaces/<space_id>`
- **Auth required:** Yes (Deletes space and all associated testimonials)

---

## Testimonials & Moderation

### 1. Public Submit Testimonial
- **Endpoint:** `POST /api/public/spaces/<slug>/testimonials` or `POST /api/public/<slug>/testimonials`
- **Auth required:** No
- **Content-Type:** `multipart/form-data` or `application/json`
- **Fields:**
  - `customer_name` (required)
  - `customer_email` (required)
  - `review_text` (required, 10–2000 chars)
  - `company_name`
  - `company_role`
  - `rating` (1–5, required if enabled)
  - `avatar` (Image file, required if space configured)
  - `consent` (boolean/checkbox)

### 2. List Testimonials for Space
- **Endpoint:** `GET /api/spaces/<space_id>/testimonials`
- **Auth required:** Yes
- **Query Parameters:**
  - `status`: `all` | `pending` | `approved` | `rejected` | `archived`
  - `search`: Keyword string
  - `rating`: 1–5
  - `sort`: `newest` | `oldest` | `rating_high` | `rating_low`
  - `page`: default 1
  - `per_page`: default 15

### 3. Moderate Testimonial
- **Endpoints:**
  - `POST /api/testimonials/<id>/approve`
  - `POST /api/testimonials/<id>/reject`
  - `POST /api/testimonials/<id>/archive`
  - `POST /api/testimonials/<id>/restore`
  - `POST /api/testimonials/<id>/feature`
  - `POST /api/testimonials/<id>/like`
  - `PATCH /api/testimonials/<id>` (edit text/name)
  - `DELETE /api/testimonials/<id>`
- **Auth required:** Yes (Ownership verified)

---

## Public Display Endpoints

### 1. Public Space Info
- **Endpoint:** `GET /api/public/spaces/<slug>`
- **Auth required:** No
- **Response:** Public space branding, questions, and settings (never leaks owner info).

### 2. Public Wall of Love Data
- **Endpoint:** `GET /api/public/wall/<slug>`
- **Auth required:** No
- **Query Parameters:** `page`, `per_page`
- **Response:** Approved testimonials for the space. Customer email is strictly excluded.

### 3. Public Widget Data
- **Endpoint:** `GET /api/public/widgets/<slug>`
- **Auth required:** No
- **Response:** Approved testimonials formatted for embeds.

---

## Analytics & Overview

### 1. Dashboard Overview
- **Endpoint:** `GET /api/dashboard/overview`
- **Auth required:** Yes
- **Response:** Metrics across all spaces (total, pending, approved, average rating, recent submissions, activity).

### 2. Space Analytics
- **Endpoint:** `GET /api/spaces/<space_id>/analytics`
- **Auth required:** Yes
- **Query Parameters:** `trend_days` (default 30)
- **Response:** Rating distribution (1–5 stars) and daily submission count trends.

### 3. Notifications
- **Endpoint:** `GET /api/notifications`
- **Auth required:** Yes
- **Response:** Notification list with unread counter.
- **Mark read:** `POST /api/notifications/mark-read`
