# Vouchly

> **Turn Feedback Into Trust** — Collect, moderate, and showcase customer testimonials with beautifully designed social proof tools.

---

## Table of Contents

- [Project Name](#project-name)
- [Project Description](#project-description)
- [Features](#features)
- [Technology Stack Used](#technology-stack-used)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [How to Install Dependencies](#how-to-install-dependencies)
- [How to Configure Environment Variables](#how-to-configure-environment-variables)
- [Database Setup](#database-setup)
- [How to Run the Project Locally](#how-to-run-the-project-locally)
- [Running Tests](#running-tests)
- [API Overview](#api-overview)
- [Assumptions & Limitations](#assumptions--limitations)

---

## Project Name

**Vouchly** (rebranded from Proofly)

---

## Project Description

Vouchly is a full-stack social proof and testimonial management web application built for modern businesses, creators, and agencies.

### The Problem It Solves
Collecting authentic customer testimonials usually requires chasing clients over email or messaging apps, resulting in scattered feedback that is difficult to format, verify, or embed into marketing websites.

### The Solution
Vouchly provides an end-to-end workflow:
1. **Spaces (Collection Forms)**: Owners set up branded submission forms with custom prompts, logos, and accent colours.
2. **Frictionless Submission**: Clients receive a clean, single-purpose public link to submit their rating, feedback, name, and optional avatar — without creating an account.
3. **Moderation Inbox**: Owners review submissions, approve the best ones, highlight top feedback as "Featured", or archive/reject entries.
4. **Wall of Love**: A public showcase page displaying approved testimonials in a responsive masonry grid.
5. **Embeddable Widgets**: A code generator that produces copy-paste `<script>` tags to display testimonials (grid, carousel, or badge) on any website (WordPress, Webflow, Shopify, custom HTML).
6. **Analytics**: Visual breakdown of average ratings, total submissions, and submission volume over time.

---

## Features

| Feature | Description |
|---|---|
| **Branded Collection Spaces** | Custom forms with brand colour, logo, custom questions, and thank-you messages |
| **Frictionless Client Submission** | Clients submit feedback with ratings (1–5 stars) without needing an account |
| **Moderation Dashboard** | Review, approve, reject, feature, archive, and filter testimonials |
| **Public Wall of Love** | Beautiful, responsive public gallery of all approved customer reviews |
| **Embed Generator** | Configurable widget snippets (grid, carousel, badge) ready for external sites |
| **Rating Analytics** | Real-time calculation of average rating, total count, and distribution |
| **Secure Authentication** | JWT with HttpOnly cookies, refresh token rotation, and password hashing |
| **Email Verification** | Secure verification links (itsdangerous signed tokens) via Gmail SMTP or dev simulation |
| **Theme Toggle** | Persistent Dark Mode / Light Mode support across dashboard pages |
| **Rate Limiting** | IP-based request throttling with strict limits on authentication routes |

---

## Technology Stack Used

### Backend
- **Python 3.10+**: Core programming language.
- **Flask (v3.0.3)**: Web framework utilizing application factories and modular Blueprints (`auth`, `spaces`, `testimonials`, `analytics`, `widgets`).
- **PyMongo (v4.8.0)**: Official MongoDB driver for document storage and queries.
- **PyJWT (v2.9.0)**: JSON Web Token encoding and decoding for stateless authentication.
- **itsdangerous (v2.2.0)**: Cryptographically signed, timestamped tokens for email verification.
- **Werkzeug (v3.0.3)**: Secure password hashing (`generate_password_hash`, `check_password_hash`) and secure filename handling.
- **Flask-CORS (v4.0.1)**: Enables cross-origin requests for embeddable widgets on external domains.
- **Flask-Limiter (v3.7.0)**: IP-based rate limiting to protect against brute-force attacks and abuse.
- **Pillow (v10.4.0)**: Image verification and processing for avatar and logo file uploads.
- **python-dotenv (v1.0.1)**: Environment variable loading from `.env` files.
- **dnspython (v2.6.1)**: DNS resolution required for MongoDB Atlas `mongodb+srv://` connection strings.

### Database
- **MongoDB 6.0+**: Document-oriented database for flexible storage of owners, spaces, testimonials, tokens, and logs.

### Frontend
- **Jinja2**: Server-side template rendering with reusable layouts (`base.html`, `dashboard_base.html`).
- **Vanilla JavaScript (ES6+)**: Modular scripts (`auth.js`, `spaces.js`, `testimonials.js`, `analytics.js`, `main.js`) handling API interactions and UI states.
- **CSS3 Design System**: Custom property variables (`style.css`, `dashboard.css`, `auth.css`) supporting Dark/Light mode.
- **Font Awesome 6**: UI icons.
- **Google Fonts**: *Playfair Display*, *Inter*, and *DM Sans*.

### Testing
- **pytest (v8.3.2)**: Automated test framework.
- **pytest-flask (v1.3.0)**: Flask test fixtures for HTTP client and context testing.

---

## Project Structure

```
proofly/
├── app.py                  # Flask application factory, error handlers, and page routes
├── auth.py                 # Auth blueprint (signup, login, logout, email verification, password reset)
├── spaces.py               # Spaces blueprint (CRUD for spaces & public space retrieval)
├── testimonials.py         # Testimonials blueprint (public submission, approval, filtering)
├── analytics.py            # Analytics blueprint (metrics, rating distributions, trends)
├── widgets.py              # Widgets blueprint (embed code generation and public widget data)
├── config.py               # Centralised configuration loading from .env
├── database.py             # MongoDB connection manager and index initialisation
├── utils.py                # Reusable utilities (JWT, SMTP email, responses, upload validation)
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Public base layout
│   ├── dashboard_base.html # Authenticated dashboard layout with sidebar & topbar
│   ├── landing.html        # Public homepage
│   ├── login.html          # User login
│   ├── signup.html         # User registration
│   ├── verification_pending.html # Email verification waiting screen with action buttons
│   ├── verify_email.html   # Email verification token confirmation page
│   ├── dashboard.html      # Owner overview dashboard
│   ├── spaces.html         # Space listing
│   ├── create_space.html   # New space creation form
│   ├── edit_space.html     # Space settings and customization
│   ├── testimonials.html   # Moderation inbox
│   ├── testimonial_detail.html # Single testimonial view
│   ├── collection.html     # Public testimonial submission form for clients
│   ├── wall_of_love.html   # Public wall of love showcase
│   ├── embed_generator.html# Embed snippet configurator
│   ├── analytics.html      # Metrics & chart displays
│   ├── settings.html       # Account settings
│   ├── profile.html        # Owner profile & branding
│   ├── forgot_password.html# Password reset request
│   ├── reset_password.html # New password form
│   ├── 404.html            # Custom not found page
│   └── 500.html            # Custom server error page
│
├── static/
│   ├── css/                # Stylesheets (style.css, dashboard.css, auth.css, etc.)
│   ├── js/                 # Client-side JavaScript modules
│   ├── uploads/            # Uploaded brand logos and client avatars (git-ignored)
│   └── vouchly-logo.png    # Official Vouchly logo image
│
├── tests/
│   ├── conftest.py         # Pytest test fixtures & mock MongoDB setup
│   └── test_auth.py        # Authentication & verification test suite
│
├── .env                    # Environment configuration (ignored in version control)
├── .env.example            # Annotated template for environment variables
├── requirements.txt        # Python dependency manifest
└── README.md               # Project documentation
```

---

## Prerequisites

Before setting up the project, make sure you have:

- **Python 3.10 or higher** installed (`python --version` or `python3 --version`)
- **MongoDB 6.0+** running locally **OR** a free [MongoDB Atlas](https://www.mongodb.com/atlas) cloud cluster
- **pip** package manager
- **A modern web browser** (Chrome, Firefox, Safari, Edge)

---

## How to Install Dependencies

### 1. Clone or open the repository

```bash
git clone <repository-url>
cd proofly
```

### 2. Create a virtual environment

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install required packages

```bash
pip install -r requirements.txt
```

---

## How to Configure Environment Variables

1. Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and configure the following parameters:

```env
# ── Flask Configuration ────────────────────────────────
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=change-this-to-a-long-random-secret-key

# ── MongoDB Connection ─────────────────────────────────
# For local MongoDB:
MONGO_URI=mongodb://localhost:27017/
# For MongoDB Atlas (cloud):
# MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=vouchly

# ── JWT Secrets ────────────────────────────────────────
# Generate secure strings with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_ACCESS_SECRET=your-secure-jwt-access-secret
JWT_REFRESH_SECRET=your-secure-jwt-refresh-secret
JWT_ACCESS_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7

# ── Cookie Security ────────────────────────────────────
COOKIE_SECURE=False       # Set to True in production with HTTPS
COOKIE_SAMESITE=Lax

# ── File Uploads ───────────────────────────────────────
UPLOAD_FOLDER=static/uploads
MAX_UPLOAD_SIZE_MB=5

# ── Application URLs ───────────────────────────────────
APP_BASE_URL=http://localhost:5000
PUBLIC_BASE_URL=http://localhost:5000

# ── Rate Limiting ──────────────────────────────────────
RATELIMIT_DEFAULT=200 per day;50 per hour
RATELIMIT_AUTH=10 per minute

# ── Email Verification Token ───────────────────────────
EMAIL_VERIFICATION_MAX_AGE=3600
EMAIL_VERIFICATION_SALT=vouchly-email-verification-salt

# ── Email Delivery (Gmail SMTP) ─────────────────────────
# When MAIL_USERNAME and MAIL_PASSWORD are set, real verification emails are sent.
# Set DEV_EMAIL_SIMULATE=True to simulate emails in the console without sending.
DEV_EMAIL_SIMULATE=False
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-character-google-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

### How to obtain a Google App Password for Gmail:
1. Sign in to your Google Account at [myaccount.google.com](https://myaccount.google.com/).
2. Navigate to **Security** and ensure **2-Step Verification** is turned **ON**.
3. In the top search bar, search for **App passwords**.
4. Create an entry (e.g. named `Vouchly`) and copy the generated **16-character password** (e.g. `abcd efgh ijkl mnop`).
5. Paste it into `MAIL_PASSWORD` in `.env` without spaces (`abcdefghijklmnop`).

---

## Database Setup

Vouchly uses **MongoDB** as its primary document database.

### Automatic Schema & Index Initialisation
There are no manual SQL migrations to run. When the Flask app starts (`init_db(app)` in `database.py`), it automatically establishes connections and creates the following indexes:

| Collection | Indexed Fields | Purpose |
|---|---|---|
| `owners` | `email` (Unique) | Enforces unique user accounts |
| `spaces` | `slug` (Unique), `owner_id` | Fast space lookups & URL resolution |
| `testimonials` | `space_id`, `owner_id`, `status`, `submitted_at` | Efficient moderation filtering |
| `refresh_tokens` | `token` (Unique), `expires_at` (TTL) | JWT revocation & auto-expiry |
| `email_verification_tokens` | `token` (Unique), `expires_at` (TTL) | Auto-cleanup of expired verification tokens |
| `password_reset_tokens` | `token` (Unique), `expires_at` (TTL) | Password reset lifecycle |
| `moderation_logs` | `owner_id`, `testimonial_id`, `created_at` | Audit trail history |
| `notifications` | `owner_id`, `created_at` | In-app notification delivery |

### Starting MongoDB

- **Local MongoDB (Windows PowerShell):**
  ```powershell
  net start MongoDB
  ```
- **Local MongoDB (macOS with Homebrew):**
  ```bash
  brew services start mongodb-community
  ```
- **Local MongoDB (Linux systemd):**
  ```bash
  sudo systemctl start mongod
  ```
- **MongoDB Atlas**: Ensure your IP address is whitelisted in Network Access (`0.0.0.0/0` for development).

---

## How to Run the Project Locally

### 1. Start the Flask application

Ensure your virtual environment is active:

```bash
python app.py
```

Or using Flask CLI:

```bash
flask run --host=0.0.0.0 --port=5000
```

### 2. Access the application

Open your browser and navigate to:
```
http://localhost:5000
```

### 3. Verification Behavior During Local Testing
- **With Gmail Credentials configured**: An activation email is delivered directly to the user's Gmail inbox.
- **Without Gmail Credentials / Fallback Mode**: When running locally without SMTP credentials or if delivery fails, the terminal prints the activation link, and the `/verification-pending` page displays an **"Activate Account Now"** button so you are never locked out during development.

---

## Running Tests

Vouchly includes automated tests covering authentication, tokens, spaces, and widgets.

```bash
# Run all tests
.\venv\Scripts\pytest

# Run tests with detailed verbose output
.\venv\Scripts\pytest -v

# Run authentication test suite specifically
.\venv\Scripts\pytest tests/test_auth.py -v
```

---

## API Overview

All API endpoints return JSON using a standard envelope format:
- Success: `{ "success": true, "message": "...", "data": { ... } }`
- Error: `{ "success": false, "message": "...", "errors": { "field": "reason" } }`

### Authentication (`/api/auth`)
- `POST /api/auth/signup`: Register a new business owner account.
- `POST /api/auth/login`: Authenticate and receive HttpOnly JWT cookies.
- `POST /api/auth/logout`: Revoke refresh token and clear cookies.
- `POST /api/auth/refresh`: Rotate refresh token and issue a fresh access token.
- `POST /api/auth/verify-email`: Verify account via signed token.
- `POST /api/auth/resend-verification`: Re-issue verification email.
- `POST /api/auth/forgot-password`: Request a password reset link.
- `POST /api/auth/reset-password`: Set new password with valid reset token.
- `GET  /api/auth/me`: Retrieve current authenticated owner profile.

### Spaces (`/api/spaces`)
- `GET    /api/spaces`: List all spaces owned by the current user.
- `POST   /api/spaces`: Create a new collection space.
- `GET    /api/spaces/<id>`: Retrieve space details.
- `PUT    /api/spaces/<id>`: Update space configuration (colours, prompts, logo).
- `DELETE /api/spaces/<id>`: Delete space and cascade delete its testimonials.

### Testimonials (`/api/testimonials`)
- `GET    /api/spaces/<space_id>/testimonials`: List testimonials for a space.
- `POST   /api/testimonials/<id>/approve`: Approve a submission for public display.
- `POST   /api/testimonials/<id>/reject`: Reject a submission.
- `POST   /api/testimonials/<id>/feature`: Toggle featured spotlight status.
- `DELETE /api/testimonials/<id>`: Permanently remove a testimonial.

### Public Endpoints (`/api/public`)
- `GET  /api/public/spaces/<slug>`: Get space information for public collection forms.
- `POST /api/public/spaces/<slug>/testimonials`: Submit a new client testimonial.
- `GET  /api/public/wall/<slug>`: Fetch approved testimonials for the public Wall of Love.
- `GET  /api/public/widgets/<slug>`: Fetch data for embeddable widgets.

---

## Assumptions & Limitations

### Assumptions
1. **Single-Tenant per Account**: Each business owner independently manages their own spaces and testimonials. There is currently no multi-user team collaboration or role-based access within a single account.
2. **MongoDB Dependency**: The application architecture strictly relies on MongoDB document structures, BSON ObjectIds, and TTL indexes. There is no SQL/SQLite fallback.
3. **Public Submission Openness**: Anyone with a Space's public URL can submit a testimonial. Submissions always default to `pending` status, giving owners complete editorial control before testimonials appear publicly.
4. **Local Upload Storage**: File uploads (logos and avatars) are written to `static/uploads/` on the local filesystem.

### Limitations
1. **In-Memory Rate Limiting**: `Flask-Limiter` uses in-memory storage by default (`storage_uri="memory://"`). Rate-limiting counters reset upon application restart and are not shared across multi-process WSGI workers. For production, a Redis storage URI should be configured.
2. **Synchronous Email Dispatch**: SMTP emails are dispatched synchronously during the request lifecycle. High-traffic environments should offload email sending to a task queue (e.g. Celery or RQ).
3. **Local File Storage in Containers**: Because uploads are stored locally in `static/uploads/`, running in containerised or ephemeral hosting environments (e.g. Heroku, AWS ECS) requires mounting a persistent volume or integrating an S3/Cloudflare R2 storage adapter.
4. **No Direct Video Recording**: The platform currently captures text and photo ratings. Video testimonial recording is not natively built in.
5. **Static Asset Serving**: Flask serves static CSS and JavaScript files directly. For production deployments, a reverse proxy such as Nginx or a CDN should be configured in front of Flask.
