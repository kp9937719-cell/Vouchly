# Vouchly — Setup & Deployment Guide

This guide walks through setting up Vouchly locally on Windows, macOS, or Linux, as well as configuring MongoDB and running tests.

---

## 1. System Requirements

- **Python:** 3.10 or higher
- **MongoDB:** Community Edition 5.0+ or MongoDB Atlas cluster
- **Modern Web Browser:** Chrome, Edge, Safari, Firefox

---

## 2. Local Setup Steps

### Step A: Clone / Navigate to Project Directory
```powershell
cd "c:\job project\vouchly"
```

### Step B: Virtual Environment Setup
```powershell
# Create venv
python -m venv venv

# Activate venv on Windows:
venv\Scripts\activate

# (On macOS/Linux):
# source venv/bin/activate
```

### Step C: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step D: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```

Ensure your `.env` contains:
```env
FLASK_ENV=development
SECRET_KEY=your-random-secret-key-change-in-production
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=vouchly

JWT_ACCESS_SECRET=your-jwt-access-secret-key
JWT_REFRESH_SECRET=your-jwt-refresh-secret-key
JWT_ACCESS_EXPIRES_MINUTES=60
JWT_REFRESH_EXPIRES_DAYS=30

COOKIE_SECURE=False
COOKIE_SAMESITE=Lax

UPLOAD_FOLDER=static/uploads
MAX_UPLOAD_SIZE_MB=5
APP_BASE_URL=http://localhost:5000
DEV_EMAIL_SIMULATE=True
```

---

## 3. Starting MongoDB

### On Windows
If MongoDB Community was installed as a Windows Service, it starts automatically.
To verify or start manually:
```powershell
net start MongoDB
```
Or start via mongod binary:
```powershell
mongod --dbpath C:\data\db
```

### MongoDB Atlas (Cloud)
1. Create a free cluster on [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
2. Grab the connection string (e.g., `mongodb+srv://<user>:<password>@cluster.mongodb.net/`).
3. Set `MONGO_URI` in `.env` to your Atlas connection string.

---

## 4. Running the Application

```powershell
venv\Scripts\python app.py
```
Visit **http://localhost:5000** in your browser.

- **Landing Page:** `http://localhost:5000/`
- **Sign Up:** `http://localhost:5000/signup`
- **Sign In:** `http://localhost:5000/login`
- **Dashboard:** `http://localhost:5000/dashboard`

*(In dev mode, verification links are printed directly to your console).*

---

## 5. Running the Automated Test Suite

```powershell
venv\Scripts\pytest tests/ -v
```

All 38 integration and unit tests should execute and pass.
Tests utilize the `vouchly_test` MongoDB database and clean up collections automatically.
