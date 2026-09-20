# Vouchly — Testimonial & Social Proof Collector

**Vouchly** is a full-stack web application that lets business owners collect customer testimonials, moderate submissions, showcase approved reviews publicly, and embed testimonial widgets on any website.

---

## Tech Stack

| Layer      | Technology                              |
|------------|-----------------------------------------|
| Backend    | Python 3.10+ · Flask 3.0               |
| Database   | MongoDB · PyMongo 4.8                  |
| Auth       | JWT (PyJWT) · HttpOnly cookies         |
| Frontend   | Vanilla HTML · CSS · JavaScript (no frameworks) |
| Templates  | Jinja2                                  |
| CSS Design | Custom design system (Minimalist Luxury) |

---

## Project Structure

```
vouchly/
├── app.py              # Flask app factory — main entry point
├── auth.py             # Authentication: signup, login, JWT, password reset
├── spaces.py           # Collection spaces (CRUD + public endpoint)
├── testimonials.py     # Submissions, moderation, public Wall of Love
├── analytics.py        # Rating stats, submission trends, notifications
├── widgets.py          # Embed widget API + widget page
├── database.py         # MongoDB connection + index setup
├── config.py           # Configuration (reads from .env)
├── utils.py            # Shared helpers (validation, upload, pagination)
│
├── templates/          # Jinja2 HTML templates
│   ├── base.html           # Public page base
│   ├── dashboard_base.html # Dashboard sidebar layout
│   ├── landing.html        # Landing page
│   ├── login.html          # Sign in page
│   ├── signup.html         # Sign up page
│   ├── dashboard.html      # Overview metrics
│   ├── spaces.html         # Manage spaces
│   ├── create_space.html   # Create space form
│   ├── edit_space.html     # Edit space form
│   ├── testimonials.html   # Moderation inbox
│   ├── collection.html     # Public form (customer-facing)
│   ├── wall_of_love.html   # Public Wall of Love
│   ├── analytics.html      # Analytics charts
│   ├── embed_generator.html # Embed code generator
│   ├── profile.html        # Owner profile
│   ├── settings.html       # Account settings
│   ├── widget.html         # Embeddable iframe widget
│   ├── 404.html / 500.html # Error pages
│   └── ...
│
├── static/
│   ├── css/
│   │   ├── style.css         # Global design system (CSS variables)
│   │   ├── auth.css          # Auth pages
│   │   ├── dashboard.css     # Dashboard layout + components
│   │   ├── collection.css    # Public form
│   │   ├── testimonials.css  # Moderation inbox
│   │   ├── showcase.css      # Landing page + Wall of Love
│   │   └── responsive.css    # Mobile breakpoints
│   ├── js/
│   │   ├── main.js           # Toast, modal, apiFetch, theme toggle
│   │   ├── auth.js           # Auth forms
│   │   ├── dashboard.js      # Dashboard overview
│   │   ├── spaces.js         # Spaces CRUD
│   │   ├── collection.js     # Public submission form
│   │   ├── testimonials.js   # Moderation inbox
│   │   ├── analytics.js      # Charts
│   │   ├── embed.js          # Embed generator
│   │   └── settings.js       # Profile/settings
│   └── uploads/              # Uploaded logos and avatars (gitignored)
│
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_auth.py          # Auth tests
│   ├── test_spaces.py        # Space CRUD tests
│   ├── test_testimonials.py  # Testimonial & moderation tests
│   └── test_widgets.py       # Widget & embed tests
│
├── requirements.txt
├── .env                # Your local config (not committed)
├── .env.example        # Config template
└── .gitignore
```

---

## Setup & Running

### 1. Prerequisites

- Python 3.10+
- MongoDB running locally on `mongodb://localhost:27017/`
  - [Download MongoDB Community](https://www.mongodb.com/try/download/community)

### 2. Clone and setup

```powershell
cd "c:\job project\vouchly"

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment

```powershell
copy .env.example .env
```

Edit `.env` and set your `SECRET_KEY` and `JWT_SECRET_KEY` values.  
The defaults in `.env.example` are fine for local development.

### 4. Start MongoDB

Make sure MongoDB is running. On Windows, start it from the Services panel or:

```powershell
mongod --dbpath C:\data\db
```

### 5. Run the app

```powershell
python app.py
```

Open http://localhost:5000 in your browser.

---

## First Steps After Setup

1. **Sign up** at `/signup`
2. Check the terminal — you'll see a verification link printed there (email simulation)
3. Click the link to verify your email
4. **Log in** at `/login`
5. **Create your first space** at `/spaces/new`
6. Share the collection URL with customers: `http://localhost:5000/collect/your-slug`
7. Review submissions in the **Testimonials** inbox
8. Approve testimonials → they appear on your **Wall of Love**
9. Generate embed code from **Embed Generator** to add widgets to any website

---

## Key Features

### Authentication
- Signup → email verification (console in dev mode)
- Login with JWT stored in HttpOnly cookies
- Auto-refresh tokens
- Forgot / reset password

### Testimonial Collection
- Public form at `/collect/<slug>` — no account needed for customers
- Configurable: star ratings, avatar upload, custom questions
- Branded with your logo and colors

### Moderation
- Inbox with Pending / Approved / Rejected / Archived tabs
- Approve, reject, archive, restore, feature testimonials
- Search by name, company, or content; filter by rating and status
- Edit testimonial text/name if needed

### Public Showcase
- Wall of Love at `/wall/<slug>` — masonry grid of approved testimonials
- Featured testimonials displayed prominently

### Embeddable Widgets
- `/embed` — generate iframe or HTML embed code
- Three layouts: **Grid**, **Carousel**, **Badge**
- Light/dark theme, custom brand color, toggle ratings/avatars/company
- Widget page at `/widget/<slug>` — works in any `<iframe>`

### Analytics
- Rating distribution bar chart
- Submission trend line chart (7, 30, or 90 days)
- Summary metrics: total, pending, approved, average rating

---

## Running Tests

```powershell
venv\Scripts\activate
pytest tests/ -v
```

Make sure MongoDB is running before running tests.  
Tests use a separate `vouchly_test` database that is cleaned before each test.

---

---

## Email Verification (Local Simulation with `itsdangerous`)

Vouchly includes a production-grade, secure email verification workflow **without requiring external email services, SMTP credentials, or third-party APIs**:

### How It Works:
1. **Cryptographic Signed Tokens**: Uses `itsdangerous.URLSafeTimedSerializer` with a dedicated salt (`EMAIL_VERIFICATION_SALT`) and application `SECRET_KEY`. Tokens carry a timestamp and email payload without cluttering the database.
2. **Account Protection**: When an owner registers, `email_verified` is set to `False` and `verified_at` to `None`. No JWT session cookies are issued until verification is complete.
3. **Login Protection**: Attempting to sign in before verification returns HTTP 403, and the UI redirects or prompts the user to complete verification.
4. **Development Simulation**:
   - Verification links (`/verify-email/<token>`) are printed to the console output.
   - In development mode, the `/verification-pending` page renders an instant "Complete Verification Now" button.
   - In production mode (`FLASK_ENV=production`), verification links are suppressed from API responses and the UI, ready to be dispatched via any email delivery provider.
5. **Token Expiry & Resend**: Tokens expire after 1 hour (`EMAIL_VERIFICATION_MAX_AGE = 3600`). Users can request a new link at any time via `/api/auth/resend-verification`.

---

## API Summary

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/signup` | — | Create account (sets `email_verified: false`) |
| POST | `/api/auth/verify-email` | — | Validate token & mark email verified |
| POST | `/api/auth/resend-verification` | — | Generate new verification link |
| POST | `/api/auth/login` | — | Log in (enforces email verification) |
| POST | `/api/auth/logout` | ✓ | Log out |
| GET  | `/api/auth/me` | ✓ | Current user |
| GET  | `/api/spaces` | ✓ | List spaces |
| POST | `/api/spaces` | ✓ | Create space |
| GET  | `/api/spaces/<id>` | ✓ | Get space |
| PATCH| `/api/spaces/<id>` | ✓ | Update space |
| DELETE| `/api/spaces/<id>` | ✓ | Delete space |
| GET  | `/api/public/spaces/<slug>` | — | Public space info |
| POST | `/api/public/<slug>/testimonials` | — | Submit testimonial |
| GET  | `/api/spaces/<id>/testimonials` | ✓ | List testimonials |
| POST | `/api/testimonials/<id>/approve` | ✓ | Approve |
| POST | `/api/testimonials/<id>/reject` | ✓ | Reject |
| POST | `/api/testimonials/<id>/feature` | ✓ | Toggle feature |
| GET  | `/api/public/wall/<slug>` | — | Public wall |
| GET  | `/api/public/widgets/<slug>` | — | Widget data |
| GET  | `/api/spaces/<id>/analytics` | ✓ | Space analytics |
| GET  | `/api/dashboard/overview` | ✓ | Dashboard overview |
| POST | `/api/embed/generate` | ✓ | Generate embed code |

See `docs/API.md` for the full reference.

---

## Design System

The UI uses a **Minimalist Luxury** design with:

- **Typefaces**: Playfair Display (headings) · Inter (body) · DM Sans (UI)
- **Colors**: White `#FFFFFF` · Ivory `#F8F6F0` · Gold `#B89A5A` · Black `#111111`
- **Components**: Design tokens via CSS custom properties in `style.css`

Dark mode is supported and saved to `localStorage`.

---

## Security Notes

- Passwords hashed with Werkzeug (bcrypt-compatible)
- JWTs stored in HttpOnly cookies (not accessible to JavaScript)
- XSS prevention: all user content rendered via `escapeHtml()` in JS, `{{ var | e }}` in Jinja2
- Ownership checks on every private endpoint
- Email enumeration prevention (identical error messages for wrong email vs wrong password)
- Rate limiting on auth endpoints via Flask-Limiter

---

Built with ❤️ for students learning Flask + MongoDB.
