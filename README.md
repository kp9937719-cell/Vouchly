# Vouchly

> **Turn Feedback Into Trust** — Collect, moderate, and showcase customer testimonials with beautifully designed social proof tools.

---

## Table of Contents

- [Project Description](#project-description)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Running the Project](#running-the-project)
- [Running Tests](#running-tests)
- [API Overview](#api-overview)
- [Assumptions & Limitations](#assumptions--limitations)

---

## Project Description

Vouchly is a full-stack web application that helps business owners collect, manage, and display customer testimonials. Owners sign up, create branded **Spaces** (collection forms), share a unique public link with their customers, then review and approve submissions through a moderation dashboard.

Approved testimonials can be displayed on a public **Wall of Love** page or embedded directly into any website using a generated JavaScript snippet.

---

## Features

| Feature | Description |
|---|---|
| **Branded Spaces** | Create custom testimonial collection forms with your logo, colours, and welcome message |
| **Frictionless Collection** | Customers submit testimonials via a public link — no account required |
| **Moderation Inbox** | Review, approve, reject, feature, or archive testimonials |
| **Wall of Love** | A public, shareable page showcasing your approved testimonials |
| **Embeddable Widgets** | Generate `<script>` embed codes for grids, carousels, or badge-style widgets |
| **Rating Analytics** | View submission trends, rating distributions, and space-level stats |
| **JWT Authentication** | Secure login with HttpOnly access + refresh token cookies and token rotation |
| **Email Verification** | Cryptographic signed tokens (itsdangerous) for account activation |
| **Dark / Light Theme** | User-selectable UI theme persisted to the profile |
| **Rate Limiting** | IP-based request throttling on all endpoints, stricter limits on auth routes |

---

## Technology Stack

### Backend
| Technology | Version | Purpose |
|---|---|---|
| **Python** | 3.10+ | Core language |
| **Flask** | 3.0.3 | Web framework |
| **PyMongo** | 4.8.0 | MongoDB driver |
| **PyJWT** | 2.9.0 | JWT token generation and validation |
| **itsdangerous** | 2.2.0 | Signed tokens for email verification |
| **Werkzeug** | 3.0.3 | Password hashing, file utilities |
| **Flask-CORS** | 4.0.1 | Cross-origin resource sharing for embed widgets |
| **Flask-Limiter** | 3.7.0 | IP-based rate limiting |
| **Pillow** | 10.4.0 | Image validation and processing for uploads |
| **python-dotenv** | 1.0.1 | `.env` file loading |
| **dnspython** | 2.6.1 | DNS resolution for MongoDB Atlas SRV URIs |

### Database
| Technology | Purpose |
|---|---|
| **MongoDB** | Primary data store (owners, spaces, testimonials, tokens, logs) |

### Frontend
| Technology | Purpose |
|---|---|
| **Jinja2** | Server-side HTML templating (bundled with Flask) |
| **Vanilla JavaScript (ES6+)** | All UI interactions, form submissions, API calls |
| **CSS Custom Properties** | Design system with theme variables (light / dark) |
| **Font Awesome 6** | Icons |
| **Google Fonts** | Playfair Display, Inter, DM Sans |

### Testing
| Technology | Version | Purpose |
|---|---|---|
| **pytest** | 8.3.2 | Test runner |
| **pytest-flask** | 1.3.0 | Flask-specific test fixtures |

---

## Project Structure

```
proofly/
├── app.py                  # Flask application factory & page routes
├── auth.py                 # Authentication blueprint (JWT, signup, login, verification)
├── spaces.py               # Spaces blueprint (CRUD + public collection endpoints)
├── testimonials.py         # Testimonials blueprint (submit, moderate, filter)
├── analytics.py            # Analytics blueprint (stats, charts)
├── widgets.py              # Widgets blueprint (embed code generation)
├── config.py               # Centralised configuration (reads .env)
├── database.py             # MongoDB connection & index initialisation
├── utils.py                # Shared helpers (responses, validation, file uploads)
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Public page base layout
│   ├── dashboard_base.html # Authenticated dashboard base layout
│   ├── landing.html        # Public landing page
│   ├── login.html          # Login page
│   ├── signup.html         # Signup page
│   ├── dashboard.html      # Main dashboard
│   ├── spaces.html         # Space list page
│   ├── testimonials.html   # Testimonial inbox
│   ├── analytics.html      # Analytics page
│   ├── wall_of_love.html   # Public Wall of Love
│   ├── collection.html     # Public testimonial submission form
│   └── ...                 # Other templates
│
├── static/
│   ├── css/                # Stylesheets (style.css, dashboard.css, auth.css, ...)
│   ├── js/                 # JavaScript modules (auth.js, main.js, spaces.js, ...)
│   ├── uploads/            # User-uploaded images (logos, avatars) — git-ignored
│   └── vouchly-logo.png    # App logo
│
├── tests/
│   ├── conftest.py         # Pytest fixtures and test app factory
│   └── test_auth.py        # Auth endpoint tests
│
├── .env                    # Local environment variables (never commit this)
├── .env.example            # Template showing all required variables
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## Prerequisites

Make sure the following are installed on your machine before you begin:

- **Python 3.10 or higher** — [python.org](https://www.python.org/downloads/)
- **MongoDB 6.0 or higher** (local) **or** a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster
- **pip** (comes with Python)
- **git** (optional, for cloning)

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd proofly
```

### 2. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

All configuration is controlled through a `.env` file in the project root.

### Setup

```bash
# Copy the example file
cp .env.example .env
```

Then open `.env` in your editor and fill in the values:

```env
# ── Flask ─────────────────────────────────────
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-long-random-secret-key-here

# ── MongoDB ────────────────────────────────────
# Local instance:
MONGO_URI=mongodb://localhost:27017/
# OR MongoDB Atlas:
# MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=vouchly

# ── JWT Secrets ────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_ACCESS_SECRET=your-access-secret-here
JWT_REFRESH_SECRET=your-refresh-secret-here
JWT_ACCESS_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7

# ── Cookies ────────────────────────────────────
COOKIE_SECURE=False       # Set True in production (requires HTTPS)
COOKIE_SAMESITE=Lax

# ── File Uploads ───────────────────────────────
UPLOAD_FOLDER=static/uploads
MAX_UPLOAD_SIZE_MB=5

# ── Application URL ────────────────────────────
APP_BASE_URL=http://localhost:5000

# ── Rate Limiting ──────────────────────────────
RATELIMIT_DEFAULT=200 per day;50 per hour
RATELIMIT_AUTH=10 per minute

# ── Email (Development) ────────────────────────
# When True, verification links are printed to the terminal instead of emailed.
DEV_EMAIL_SIMULATE=True

# ── Email (Production — SMTP) ──────────────────
# Uncomment and fill in to send real emails:
# MAIL_SERVER=smtp.gmail.com
# MAIL_PORT=587
# MAIL_USERNAME=your-email@gmail.com
# MAIL_PASSWORD=your-app-password
# MAIL_USE_TLS=True
# MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### Generate secret keys

```bash
python -c "import secrets; print('ACCESS:', secrets.token_hex(32)); print('REFRESH:', secrets.token_hex(32))"
```

---

## Database Setup

Vouchly uses **MongoDB** as its database. No manual schema creation is needed — the app creates all necessary indexes automatically on startup.

### Option A — Local MongoDB

1. Install MongoDB Community Edition: [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community)
2. Start the MongoDB service:
   ```bash
   # macOS (with Homebrew)
   brew services start mongodb-community

   # Windows (PowerShell as Administrator)
   net start MongoDB

   # Linux (systemd)
   sudo systemctl start mongod
   ```
3. Set `MONGO_URI=mongodb://localhost:27017/` in your `.env`.

### Option B — MongoDB Atlas (Cloud, Free Tier)

1. Create a free account at [mongodb.com/atlas](https://www.mongodb.com/atlas)
2. Create a **Free Tier (M0)** cluster
3. Under **Database Access**, create a database user with read/write permissions
4. Under **Network Access**, add your IP address (or `0.0.0.0/0` for development)
5. Click **Connect → Drivers**, copy the SRV connection string, and paste it into your `.env`:
   ```env
   MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

### Collections & Indexes

The following MongoDB collections are created and indexed automatically when the app starts:

| Collection | Purpose |
|---|---|
| `owners` | User accounts |
| `spaces` | Testimonial collection spaces |
| `testimonials` | Customer testimonial submissions |
| `refresh_tokens` | JWT refresh tokens (with TTL auto-expiry) |
| `email_verification_tokens` | Email verification tokens (TTL) |
| `password_reset_tokens` | Password reset tokens (TTL) |
| `moderation_logs` | Audit trail for moderation actions |
| `notifications` | In-app notification messages |

> **No manual setup required.** Running `python app.py` will automatically create all indexes via `init_db()`.

---

## Running the Project

### Development server

With the virtual environment active and `.env` configured:

```bash
python app.py
```

The application will start at **[http://localhost:5000](http://localhost:5000)**.

Alternatively, use the Flask CLI:

```bash
flask run
```

### Development email verification

When `DEV_EMAIL_SIMULATE=True`, no real emails are sent. Instead, the verification link is:
1. **Printed to the terminal** — check the console where `python app.py` is running
2. **Displayed on screen** — shown directly on the verification pending page

Copy the link from the terminal or click it on-screen to complete email verification during local development.

---

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_auth.py -v
```

---

## API Overview

All API endpoints are prefixed with `/api/`. The application returns consistent JSON responses:

```json
// Success
{ "success": true, "message": "...", "data": { ... } }

// Error
{ "success": false, "message": "...", "errors": { "field": "reason" } }
```

### Authentication — `/api/auth/`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/signup` | Create a new account |
| `POST` | `/api/auth/login` | Login and receive JWT cookies |
| `POST` | `/api/auth/logout` | Logout and revoke refresh token |
| `POST` | `/api/auth/refresh` | Rotate access + refresh tokens |
| `POST` | `/api/auth/verify-email` | Verify email with signed token |
| `POST` | `/api/auth/resend-verification` | Request a new verification link |
| `POST` | `/api/auth/forgot-password` | Request a password reset link |
| `POST` | `/api/auth/reset-password` | Set new password with reset token |
| `GET`  | `/api/auth/me` | Get current user info |

### Spaces — `/api/spaces/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/spaces` | List all spaces for the logged-in owner |
| `POST` | `/api/spaces` | Create a new space |
| `GET` | `/api/spaces/<id>` | Get a single space |
| `PUT` | `/api/spaces/<id>` | Update a space |
| `DELETE` | `/api/spaces/<id>` | Delete a space |

### Testimonials — `/api/testimonials/`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/testimonials` | List testimonials (filterable) |
| `PATCH` | `/api/testimonials/<id>/approve` | Approve a testimonial |
| `PATCH` | `/api/testimonials/<id>/reject` | Reject a testimonial |
| `PATCH` | `/api/testimonials/<id>/feature` | Feature / unfeature |
| `DELETE` | `/api/testimonials/<id>` | Delete a testimonial |

### Public Endpoints (no auth required)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/public/spaces/<slug>` | Get space info for collection form |
| `POST` | `/api/public/spaces/<slug>/submit` | Submit a testimonial |
| `GET` | `/api/public/wall/<slug>` | Get approved testimonials for Wall of Love |
| `GET` | `/api/public/widgets/<slug>` | Get widget data for embed scripts |

---

## Assumptions & Limitations

### Assumptions

- **Single-tenant per account**: Each registered owner manages their own independent set of spaces and testimonials. There is no team/multi-user access to a shared account.
- **No real email in development**: By default (`DEV_EMAIL_SIMULATE=True`), no SMTP server is required. All email content is printed to the console. For production, configure SMTP credentials in `.env`.
- **Image uploads stored locally**: Uploaded logos and avatars are saved to `static/uploads/` on the local filesystem. For production deployments, this should be replaced with cloud storage (e.g., AWS S3, Cloudflare R2).
- **MongoDB is required**: There is no SQL or SQLite fallback. A running MongoDB instance (local or Atlas) is mandatory.
- **Python 3.10+**: The codebase uses modern Python syntax and type hints. Older Python versions are not tested or supported.

### Limitations

- **No real-time updates**: The dashboard does not use WebSockets. Stats and notification counts are fetched on page load or via manual refresh.
- **No payment / subscription system**: Vouchly is a free-tier single-plan app with no billing integration.
- **Email delivery requires SMTP setup**: Password reset and (in production) email verification require valid SMTP credentials. The development simulation mode cannot send real emails.
- **Rate limiting is in-memory**: `Flask-Limiter` is configured with `storage_uri="memory://"`, meaning rate limit counters reset on server restart and do not persist across multiple workers/processes. For production, use a Redis backend.
- **No CDN for static assets**: All CSS, JS, and uploaded images are served directly by Flask. For production, serve static files via a reverse proxy (nginx) or CDN.
- **Widget embed requires JavaScript**: The embeddable widgets are JavaScript-based and will not render in environments that block scripts.
- **File uploads capped at 5 MB**: The maximum upload size for logos and avatars is 5 MB (configurable via `MAX_UPLOAD_SIZE_MB`).
