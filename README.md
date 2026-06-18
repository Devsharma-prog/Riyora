# Riyora

### Modern Authentication, Security & Commerce Platform

[![System Health](https://img.shields.io/badge/System_Health-Healthy-success?style=flat-square)](#)
[![Security Audited](https://img.shields.io/badge/Security-A%2B_Audited-blueviolet?style=flat-square)](#)
[![Python Version](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)](#)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](#)

Riyora is a **portfolio-grade web application** designed as an educational showcase of secure web development, advanced authentication systems, payment integration, session management, and Docker deployment engineering. 

This platform is intended solely for demonstration and academic review. No real commercial offerings or transactions are conducted.

---

## 📸 Screenshots & Showcase

Below are visual showcases of the redesigned interface (featuring the Stripe/Linear glassmorphism dark aesthetic):

- **Homepage Dashboard**: `assets/screenshots/homepage.png`
- **Products Details Catalog**: `assets/screenshots/products.png`
- **Customer Sign In Portal**: `assets/screenshots/login.png`
- **Order Tracking Profile**: `assets/screenshots/profile.png`
- **Administrator Console**: `assets/screenshots/admin.png`

*(Screenshots can be added to the `assets/screenshots/` folder before repository commit)*

---

## 🛡️ Core Security Features

Riyora is built around defensive security practices. The following mitigations are implemented:

1. **CSRF Protection**: Handled globally via `Flask-WTF` tokens on standard forms and mapped dynamically as `X-CSRFToken` in AJAX fetch headers.
2. **API Rate Limiting**: Managed by `Flask-Limiter` to protect auth and payment routes (Login/Register: 5 requests/minute; Checkout: 10 requests/minute).
3. **Password Hashing**: Implements salted Bcrypt encryption; plain text strings are never processed in SQLite storage.
4. **Session Cookie Security**: Configured with `HttpOnly=True`, `SameSite=Lax`, and dynamic `Secure=True` (active on HTTPS/production deployments).
5. **Inactivity Auto-Logout**: Monitors request history and automatically invalidates sessions after 15 minutes of idle status.
6. **SQL Injection Mitigation**: All SQLite transactions are fully parameterized to deny script injection vectors.
7. **Privacy-First Data Retention**: Throttled jobs delete demo order rows and guest sessions older than `DATA_RETENTION_HOURS` (default: 24), preserving registered users.
8. **First-Time Administrator Setup**: Deletes hardcoded credential configurations and forces setup at `/setup` to initialize administrator password hashes.

---

## 🏗️ Interactive Architecture Diagram

```
User (Browser)
    │
    ▼ (HTTPS, Security Headers)
Frontend (HTML5, CSS3, JavaScript)
    │
    ▼ (CSRF Validation, Limiter, Session Check)
Flask Backend (app.py)
    ├── [Authentication Layer] ── Google OAuth 2.0 / Local Bcrypt Hashed Users
    ├── [Database Layer] ────── SQLite3 (shop.db with automated column migrations)
    └── [Payment Layer] ────── PayPal JavaScript SDK (Sandbox) / Local Dynamic UPI QR Code
```

---

## ⚙️ Technology Stack

- **Core Microframework**: Python, Flask
- **Database Isolation**: SQLite3
- **CSS Styling Framework**: Vanilla CSS (Stripe/Linear custom Design Tokens, Dark/Light toggling)
- **Local QR Engine**: `qrcode`, `Pillow` (Pillow) in-memory dynamic buffer stream
- **Production Server**: Gunicorn
- **Containerization**: Docker, Docker Compose

---

## 🔑 Environment Variables Configuration

Create a `.env` file in the root directory:

```bash
# Flask Key
SECRET_KEY=your-random-cryptographic-key-string

# Google OAuth Credentials
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# PayPal Checkout
PAYPAL_CLIENT_ID=your-paypal-sandbox-client-id
PAYPAL_SECRET=your-paypal-sandbox-secret

# Indian Users: Local UPI Address
UPI_ID=riyora@upi

# Data Retention Policy (Hours)
DATA_RETENTION_HOURS=24

# Session Cookie HTTPS Flag (Set True in Production)
SESSION_COOKIE_SECURE=False
```

---

## 🚀 Installation & Local Development

### 1. Traditional System Launch

```bash
# Clone the repository
git clone https://github.com/your-username/riyora.git
cd riyora

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install locked dependencies
pip install -r requirements.txt

# Run database setup & start web instance
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

### 2. Containerized launch (Docker)

```bash
# Build and spin up containers
docker-compose up --build
```

Access the instance at `http://localhost:5000`.

---

## 📈 Authentication & Payment Flows

### Authentication Flow
1. User clicks **Login with Google** redirection link.
2. Directs to Google Accounts consent window with credentials and scope.
3. Callback exchanges authentication `code` on server-side for access token.
4. Queries Google Userinfo APIs, checking for emails in the database.
5. Logs in user or provisions a new user, saving details in session cookies.

### Payment Flow
1. Cart checkout requests `/create_order` fetching PayPal order tokens.
2. On payment approval, javascript calls `/capture_payment`.
3. Server captures PayPal transaction, decreases product catalog stocks, records items in `order_items`, and sets status to `COMPLETED`.
4. Redirects to `/order_success` containing PDF download invoice options.

---

## 🔮 Future Improvements

- [ ] Implement complete Role-Based Access Control (RBAC) across inventory actions.
- [ ] Add Multi-Factor Authentication (MFA) for credentials login.
- [ ] Implement automated database migrations using Alembic.
- [ ] Add Redis cache store to accelerate product listings.

---

## 📄 License & Contributing

Distributed under the MIT License. Contributions to enhance educational security models are welcome!
