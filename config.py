"""
config.py — Application Configuration
======================================
Reads environment variables from the .env file and exposes them
as a Config object that the Flask app imports.

Why: Centralising config here means we only read .env in one place.
Every other file just does: from config import Config
"""

import os
from dotenv import load_dotenv

# Load .env file into os.environ
load_dotenv()


class Config:
    # ---- Flask ----
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    FLASK_ENV = os.environ.get("FLASK_ENV", "development")

    # ---- MongoDB ----
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "vouchly")

    # ---- JWT ----
    JWT_ACCESS_SECRET = os.environ.get("JWT_ACCESS_SECRET", "dev-access-secret")
    JWT_REFRESH_SECRET = os.environ.get("JWT_REFRESH_SECRET", "dev-refresh-secret")
    JWT_ACCESS_EXPIRES_MINUTES = int(os.environ.get("JWT_ACCESS_EXPIRES_MINUTES", 15))
    JWT_REFRESH_EXPIRES_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRES_DAYS", 7))

    # ---- Cookies ----
    COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "False").lower() == "true"
    COOKIE_SAMESITE = os.environ.get("COOKIE_SAMESITE", "Lax")

    # ---- File Uploads ----
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "static/uploads")
    MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", 5))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024  # Flask reads this
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

    # ---- Application URL (for email verification and embed widget links) ----
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
    PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", APP_BASE_URL)

    # ---- Rate Limiting ----
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "200 per day;50 per hour")
    RATELIMIT_AUTH = os.environ.get("RATELIMIT_AUTH", "10 per minute")

    # ---- Email Verification Configuration (itsdangerous timed signed tokens) ----
    # Token expiration in seconds (default: 3600 = 1 hour)
    EMAIL_VERIFICATION_MAX_AGE = int(os.environ.get("EMAIL_VERIFICATION_MAX_AGE", 3600))
    EMAIL_VERIFICATION_SALT = os.environ.get("EMAIL_VERIFICATION_SALT", "vouchly-email-verification-salt")
    DEV_EMAIL_SIMULATE = os.environ.get("DEV_EMAIL_SIMULATE", "False").lower() == "true"

    # ---- SMTP Email (Gmail) ----
    # To use Gmail: enable 2FA → Google Account → Security → App Passwords → generate one
    MAIL_SERVER   = os.environ.get("MAIL_SERVER",   "smtp.gmail.com")
    MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS  = os.environ.get("MAIL_USE_TLS",  "True").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")   # your Gmail address
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")   # your Gmail App Password
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
