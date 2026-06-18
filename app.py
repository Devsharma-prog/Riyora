from flask import Flask, render_template, request, jsonify, redirect, session, send_file, url_for
import sqlite3
import os
import sys
import requests

# Reconfigure stdout for UTF-8 encoding support on Windows terminal
if sys.stdout and sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
import io
import secrets
import time
from functools import wraps
from datetime import timedelta, datetime, timezone
from dotenv import load_dotenv
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from requests.auth import HTTPBasicAuth
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import qrcode

load_dotenv()

# -------------------------
# Startup Validation System
# -------------------------
def run_startup_check():
    print("=========================")
    print("RIYORA STARTUP CHECK")
    print("=========================")
    
    # SECRET_KEY Check
    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        print("✓ SECRET_KEY")
    else:
        print("✗ SECRET_KEY (CRITICAL - MISSING)")
        
    # Google OAuth Check
    google_id = os.getenv("GOOGLE_CLIENT_ID")
    google_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if google_id and google_secret:
        print("✓ GOOGLE_CLIENT_ID")
        print("✓ GOOGLE_CLIENT_SECRET")
    else:
        if not google_id:
            print("⚠ GOOGLE_CLIENT_ID missing")
        if not google_secret:
            print("⚠ GOOGLE_CLIENT_SECRET missing")
        print("⚠ Google OAuth is disabled/unconfigured.")
        
    # PayPal Check & Validation
    paypal_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    paypal_secret = os.getenv("PAYPAL_SECRET", "").strip()
    paypal_mode = os.getenv("PAYPAL_MODE", "sandbox").strip().lower()
    
    if paypal_id:
        print("✓ PAYPAL_CLIENT_ID loaded")
        prefix = paypal_id[:8] if len(paypal_id) >= 8 else paypal_id
        print(f"Client ID Prefix: {prefix}...")
    else:
        print("✗ PAYPAL_CLIENT_ID missing")
        
    if paypal_secret:
        print("✓ PAYPAL_SECRET loaded")
        print(f"Secret Length: {len(paypal_secret)}")
    else:
        print("✗ PAYPAL_SECRET missing")
        
    if paypal_id and paypal_secret:
        if paypal_mode == "live":
            print("✓ PayPal Live Mode Active")
        else:
            print("✓ PayPal Sandbox Mode Active")
    else:
        print("⚠ PayPal Configuration Missing")

    # Debugging logs
    api_base_url = "https://api-m.paypal.com" if paypal_mode == "live" else "https://api-m.sandbox.paypal.com"
    qr_image_path = os.path.abspath(os.path.join("static", "img", "paypal_qr.png"))
    qr_image_exists = os.path.exists(qr_image_path)
    print(f"Resolved PayPal Mode: {paypal_mode}")
    print(f"Resolved API Base URL: {api_base_url}")
    print(f"QR Image Path: {qr_image_path}")
    print(f"Image Exists: {qr_image_exists}")
        
    # UPI Check
    upi_id = os.getenv("UPI_ID")
    if upi_id:
        print("✓ UPI_ID")
    else:
        print("⚠ UPI_ID missing")
        
    # Predefined Admin Check
    admin_email = os.getenv("ADMIN_GOOGLE_EMAIL", "sharmavashudev99@gmail.com")
    print(f"✓ ADMIN_GOOGLE_EMAIL: {admin_email}")

    print("Application Ready")
    print("=========================")

run_startup_check()

app = Flask(__name__)

# Enforce SECRET_KEY security (no fallback allowed)
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is required")
app.secret_key = secret_key


def get_paypal_api_base():
    mode = os.getenv("PAYPAL_MODE", "sandbox").strip().lower()
    if mode == "live":
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"


def get_paypal_access_token():
    paypal_client = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    paypal_secret = os.getenv("PAYPAL_SECRET", "").strip()
    paypal_mode = os.getenv("PAYPAL_MODE", "sandbox").strip().lower()
    
    endpoint = "https://api-m.paypal.com" if paypal_mode == "live" else "https://api-m.sandbox.paypal.com"
    token_url = f"{endpoint}/v1/oauth2/token"
    
    print("----------------------------------------")
    print(f"PayPal Mode: {paypal_mode}")
    print(f"Token URL: {token_url}")
    print("Token Request Started")
    
    if not paypal_client or not paypal_secret:
        print("Error: PayPal Client ID or Secret is missing.")
        print("----------------------------------------")
        return None
        
    try:
        response = requests.post(
            token_url,
            auth=HTTPBasicAuth(paypal_client, paypal_secret),
            data={"grant_type": "client_credentials"},
            headers={
                "Accept": "application/json",
                "Accept-Language": "en_US"
            }
        )
        print(f"Token Response Status: {response.status_code}")
        print(f"Response Status: {response.status_code}")
        
        try:
            response_json = response.json()
        except Exception:
            response_json = response.text
            
        log_body = response_json
        if isinstance(response_json, dict) and "access_token" in response_json:
            log_body = response_json.copy()
            tok = log_body["access_token"]
            log_body["access_token"] = f"{tok[:8]}... (length: {len(tok)})"
            
        print(f"Token Response Body: {log_body}")
        print("----------------------------------------")
        
        if response.status_code == 200:
            return response_json.get("access_token")
        else:
            return None
    except Exception as e:
        print(f"Token Request Exception: {e}")
        print("----------------------------------------")
        return None


# Configure PayPal
app.config['PAYPAL_CLIENT_ID'] = os.getenv("PAYPAL_CLIENT_ID", "").strip()

# Initialize Security Extensions
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)

# Initialize Rate Limiter
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Secure Session & Cookie Configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'

# Automatic Inactivity Expiry (15 minutes)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=15)

# Throttled Cleanup Timestamp
LAST_CLEANUP_TIME = 0


# -------------------------
# Login Required Decorator
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if request is AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({"status": "not_logged_in", "redirect": url_for('login')}), 403
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------
# Admin Required Decorator
# -------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({"error": "Forbidden - Admin Access Required"}), 403
            return redirect(url_for('access_restricted'))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------
# Session & Inactivity Hooks
# -------------------------
@app.before_request
def handle_before_request():
    # Exclude static files and health check
    if request.endpoint in ['static', 'health']:
        return

    # Keep session permanent to enforce lifespan
    session.permanent = True

    # 1. Inactivity Session Timeout (15 minutes)
    now = datetime.now(timezone.utc)
    last_active = session.get('last_activity')

    if last_active:
        try:
            last_active_time = datetime.fromisoformat(last_active)
            if now - last_active_time > timedelta(minutes=15):
                session.clear()
                # Clear cart and return unauthenticated AJAX JSON if request is AJAX
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                    return jsonify({"error": "Session expired due to inactivity", "status": "session_expired"}), 401
        except Exception:
            pass

    session['last_activity'] = now.isoformat()

    # 2. Privacy-First Data Retention Cleanup
    global LAST_CLEANUP_TIME
    now_epoch = time.time()
    # Runs cleanup at most once every 5 minutes on request traffic
    if now_epoch - LAST_CLEANUP_TIME > 300:
        LAST_CLEANUP_TIME = now_epoch
        retention_hours = int(os.getenv("DATA_RETENTION_HOURS", 24))
        try:
            conn = get_db_connection()
            # Delete orders and items older than retention threshold
            conn.execute(
                "DELETE FROM orders WHERE created_at < datetime('now', ?)",
                (f"-{retention_hours} hours",)
            )
            conn.execute(
                "DELETE FROM order_items WHERE order_id NOT IN (SELECT id FROM orders)"
            )
            conn.commit()
            conn.close()
        except Exception as e:
            app.logger.error(f"Automatic cleanup error: {e}")


# -------------------------
# Navbar Context Injectors
# -------------------------
@app.context_processor
def inject_nav_variables():
    cart = session.get('cart', {})
    
    # Security Dashboard live status
    google_configured = bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))
    paypal_configured = bool(os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_SECRET"))
    
    return dict(
        cart_count=sum(cart.values()),
        google_oauth_configured=google_configured,
        paypal_configured=paypal_configured,
        csrf_enabled=True,
        rate_limiting_enabled=True,
        session_security_enabled=True,
        privacy_controls_enabled=True,
        upi_id=os.getenv("UPI_ID", "sharmavashudev99@okaxis"),
        linkedin_url=os.getenv("LINKEDIN_URL")
    )


# -------------------------
# Database Connection & Setup
# -------------------------
def get_db_connection():
    conn = sqlite3.connect('shop.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    # Create users
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        google_id TEXT,
        display_name TEXT,
        avatar_url TEXT,
        role TEXT DEFAULT 'user',
        last_login TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Check and migrate columns in users
    cursor = conn.execute("PRAGMA table_info(users)")
    cols = [col['name'] for col in cursor.fetchall()]
    if 'role' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    if 'google_id' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
    if 'display_name' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    if 'avatar_url' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
    if 'last_login' not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")

    # Create products
    conn.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        image TEXT,
        stock INTEGER DEFAULT 10,
        views INTEGER DEFAULT 0
    )
    """)

    # Check and migrate products
    cursor = conn.execute("PRAGMA table_info(products)")
    cols = [col['name'] for col in cursor.fetchall()]
    if 'stock' not in cols:
        conn.execute("ALTER TABLE products ADD COLUMN stock INTEGER DEFAULT 10")
    if 'views' not in cols:
        conn.execute("ALTER TABLE products ADD COLUMN views INTEGER DEFAULT 0")

    # Create portfolio_metrics
    conn.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_metrics (
        key TEXT PRIMARY KEY,
        value INTEGER DEFAULT 0
    )
    """)
    for key in ['total_visitors', 'support_clicks', 'theme_toggle_clicks', 'products_viewed']:
        conn.execute("INSERT OR IGNORE INTO portfolio_metrics (key, value) VALUES (?, 0)", (key,))

    # Create orders
    conn.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        paypal_order_id TEXT NOT NULL,
        buyer_name TEXT,
        buyer_email TEXT,
        amount REAL,
        status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        shipping_address TEXT
    )
    """)

    # Check and migrate orders
    cursor = conn.execute("PRAGMA table_info(orders)")
    cols = [col['name'] for col in cursor.fetchall()]
    if 'shipping_address' not in cols:
        conn.execute("ALTER TABLE orders ADD COLUMN shipping_address TEXT")

    # Create order items
    conn.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        product_name TEXT,
        price REAL,
        quantity INTEGER
    )
    """)

    # Create contact_messages
    conn.execute("""
    CREATE TABLE IF NOT EXISTS contact_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Seed products if empty
    p_count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if p_count == 0:
        products = [
            ("Gaming Mouse", 25.0, "mouse.jpg", 15),
            ("Mechanical Keyboard", 70.0, "keyboard.jpg", 10),
            ("Gaming Headset", 45.0, "headset.jpg", 12),
            ("Gaming Laptop", 1200.0, "laptop.jpg", 5),
            ("4K Monitor", 350.0, "monitor.jpg", 8),
            ("Game Controller", 60.0, "controller.jpg", 20)
        ]
        for name, price, img, stock in products:
            conn.execute(
                "INSERT INTO products (name, price, image, stock, views) VALUES (?, ?, ?, ?, 0)",
                (name, price, img, stock)
            )

    conn.commit()
    conn.close()


def increment_metric(key):
    try:
        conn = get_db_connection()
        conn.execute("INSERT OR IGNORE INTO portfolio_metrics (key, value) VALUES (?, 0)", (key,))
        conn.execute("UPDATE portfolio_metrics SET value = value + 1 WHERE key=?", (key,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error incrementing metric {key}: {e}")


init_db()


# -------------------------
# Health Check Endpoint
# -------------------------
@app.route('/health')
@csrf.exempt
def health():
    return jsonify({"status": "healthy"}), 200


# -------------------------
# PayPal Health Check Endpoint
# -------------------------
@app.route('/paypal_health')
@csrf.exempt
def paypal_health():
    paypal_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    paypal_secret = os.getenv("PAYPAL_SECRET", "").strip()
    paypal_mode = os.getenv("PAYPAL_MODE", "sandbox").strip().lower()
    
    endpoint = "https://api-m.paypal.com" if paypal_mode == "live" else "https://api-m.sandbox.paypal.com"
    
    return jsonify({
        "mode": paypal_mode,
        "client_loaded": bool(paypal_id),
        "secret_loaded": bool(paypal_secret),
        "endpoint": endpoint
    }), 200



# -------------------------
# Google Authentication
# -------------------------
@app.route('/login/google')
def google_login():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        return "Google Login is not configured. Please define GOOGLE_CLIENT_ID in your environment.", 400

    # CSRF state token generation
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state

    redirect_uri = url_for('google_callback', _external=True)
    if os.getenv("FLASK_ENV") == "production" and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://")

    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"state={state}&"
        f"scope=openid%20email%20profile"
    )
    return redirect(google_auth_url)


@app.route('/login/google/callback')
def google_callback():
    # Validate CSRF state parameter
    state = request.args.get("state")
    saved_state = session.pop('oauth_state', None)
    if not state or state != saved_state:
        return "Invalid OAuth state parameter. Possible CSRF attack detected.", 400

    code = request.args.get("code")
    if not code:
        return "Authorization code missing", 400

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = url_for('google_callback', _external=True)
    if os.getenv("FLASK_ENV") == "production" and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://")

    # Exchange auth code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }

    token_res = requests.post(token_url, data=data)
    if token_res.status_code != 200:
        return f"Failed to retrieve Google token: {token_res.text}", 400

    token_data = token_res.json()
    access_token = token_data.get("access_token")

    # Fetch user details
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    userinfo_res = requests.get(userinfo_url, headers=headers)
    if userinfo_res.status_code != 200:
        return "Failed to fetch Google user info", 400

    user_info = userinfo_res.json()
    email = user_info.get("email")
    if not email:
        return "Google account does not contain a valid email address", 400

    # Auto Role Check
    admin_email = os.getenv("ADMIN_GOOGLE_EMAIL", "sharmavashudev99@gmail.com")
    is_admin = (email.lower() == admin_email.lower())
    role = 'admin' if is_admin else 'user'

    google_id = user_info.get("sub", "")
    display_name = user_info.get("name", email.split("@")[0])
    avatar_url = user_info.get("picture", "")
    now_str = datetime.now(timezone.utc).isoformat()

    # Upsert user in DB
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if not user:
        conn.execute(
            "INSERT INTO users (email, google_id, display_name, avatar_url, role, last_login) VALUES (?, ?, ?, ?, ?, ?)",
            (email, google_id, display_name, avatar_url, role, now_str)
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    else:
        # Sync profile details and role
        conn.execute(
            "UPDATE users SET google_id=?, display_name=?, avatar_url=?, role=?, last_login=? WHERE id=?",
            (google_id, display_name, avatar_url, role, now_str, user['id'])
        )
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE id=?", (user['id'],)).fetchone()

    session['user_id'] = user['id']
    session['email'] = user['email']
    session['is_google_user'] = True
    session['admin'] = (user['role'] == 'admin')
    session['role'] = user['role']
    session['name'] = user['display_name']
    session['picture'] = user['avatar_url']
    session['last_login'] = user['last_login']
    
    conn.close()

    from flask import flash
    flash(f"Welcome back, {session['name']}!", "success")
    flash(f"Role: {'Administrator' if session['admin'] else 'User'}", "info")
    if session['admin']:
        flash("Administrator Access Granted", "warning")

    return redirect('/')


# -------------------------
# Authentication Routes
# -------------------------
@app.route('/login')
def login():
    if session.get('user_id'):
        return redirect('/')
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# -------------------------
# Home Page + Search
# -------------------------
@app.route('/')
def index():
    increment_metric('total_visitors')
    search = request.args.get("search")
    conn = get_db_connection()

    if search:
        products = conn.execute(
            "SELECT * FROM products WHERE name LIKE ?",
            ('%' + search + '%',)
        ).fetchall()
    else:
        products = conn.execute("SELECT * FROM products").fetchall()

    conn.close()
    return render_template("index.html", products=products)


# -------------------------
# Product Page
# -------------------------
@app.route('/product/<int:id>')
def product_page(id):
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    if not product:
        conn.close()
        return "Product not found", 404
    
    # Increment views
    conn.execute("UPDATE products SET views = views + 1 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    
    increment_metric('products_viewed')
    return render_template("product.html", product=product)


# -------------------------
# Cart System
# -------------------------
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form['product_id']
    conn = get_db_connection()
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    conn.close()

    if not product:
        return "Product not found", 404

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']
    current_qty = cart.get(product_id, 0)

    # Check stock limit
    if current_qty + 1 > product['stock']:
        return "Stock limit reached ❌", 400

    cart[product_id] = current_qty + 1
    session['cart'] = cart
    session.modified = True

    return redirect('/')


@app.route('/cart')
def cart():
    conn = get_db_connection()
    cart_items = []
    total = 0
    cart = session.get('cart', {})

    for product_id, quantity in cart.items():
        product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product:
            subtotal = product['price'] * quantity
            total += subtotal
            cart_items.append({
                "id": product['id'],
                "name": product['name'],
                "price": product['price'],
                "quantity": quantity,
                "subtotal": subtotal
            })

    conn.close()
    return render_template("cart.html", products=cart_items, total=total)


@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    product_id = request.form['product_id']
    if 'cart' in session and product_id in session['cart']:
        if session['cart'][product_id] > 1:
            session['cart'][product_id] -= 1
        else:
            session['cart'].pop(product_id)
        session.modified = True

    return redirect('/cart')


# -------------------------
# PayPal Integration
# -------------------------
@app.route('/create_order', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def create_order():
    print("Order Creation Started")
    if 'cart' not in session or not session['cart']:
        return jsonify({"error": "Cart is empty"}), 400

    conn = get_db_connection()
    total = 0
    for product_id, quantity in session['cart'].items():
        product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if product:
            total += product['price'] * quantity
    conn.close()

    paypal_client = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    paypal_secret = os.getenv("PAYPAL_SECRET", "").strip()

    if not paypal_client or not paypal_secret:
        # Mock payment order ID for offline sandbox fallback
        mock_id = f"MOCK-PAYPAL-{secrets.token_hex(8).upper()}"
        print("Order Creation Mock Mode: Missing Credentials")
        return jsonify({"id": mock_id, "status": "CREATED"})

    access_token = get_paypal_access_token()
    if not access_token:
        print("Access Token Retrieval Failed")
        return jsonify({
            "error": "PayPal Authentication Failed",
            "details": {
                "possible_causes": [
                    "Incorrect Client ID",
                    "Incorrect Secret",
                    "Sandbox/Live mismatch (e.g. live mode active but sandbox credentials configured)",
                    "PayPal developer account not activated or REST App disabled"
                ]
            }
        }), 401

    print("Access Token Retrieved")
    
    create_url = f"{get_paypal_api_base()}/v2/checkout/orders"
    print("PayPal Order Request Sent")
    
    try:
        response = requests.post(
            create_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "amount": {
                        "currency_code": "USD",
                        "value": f"{total:.2f}"
                    }
                }]
            }
        )
        print(f"PayPal Response Status: {response.status_code}")
        response_json = response.json()
        print(f"PayPal Response JSON: {response_json}")
        
        return jsonify(response_json)
    except Exception as e:
        print(f"PayPal Order Request Exception: {e}")
        return jsonify({"error": "PayPal connection failed", "details": str(e)}), 500


@app.route('/capture_payment', methods=['POST'])
@limiter.limit("10 per minute")
@login_required
def capture_payment():
    data = request.json
    order_id = data.get("orderID")
    address = data.get("shipping_address", "")

    paypal_client = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    paypal_secret = os.getenv("PAYPAL_SECRET", "").strip()

    # Handle Mock Payment for offline testing
    if order_id and order_id.startswith("MOCK-PAYPAL"):
        conn = get_db_connection()
        # Calculate amount
        amount = 0
        for product_id, quantity in session.get('cart', {}).items():
            product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if product:
                amount += product['price'] * quantity

        cursor = conn.execute(
            """INSERT INTO orders
            (user_id, paypal_order_id, buyer_name, buyer_email, amount, status, shipping_address)
            VALUES (?, ?, ?, ?, ?, 'COMPLETED', ?)""",
            (session['user_id'], order_id, "Demo Buyer", session['email'], amount, address)
        )
        order_db_id = cursor.lastrowid

        # Reduce stock & Add order items
        for product_id, quantity in session.get('cart', {}).items():
            product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if product:
                conn.execute("UPDATE products SET stock = stock - ? WHERE id=?", (quantity, product_id))
                conn.execute(
                    """INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                    VALUES (?, ?, ?, ?, ?)""",
                    (order_db_id, product['id'], product['name'], product['price'], quantity)
                )
        conn.commit()
        conn.close()

        session.pop("cart", None)
        return jsonify({"status": "success", "order_id": order_db_id})

    access_token = get_paypal_access_token()
    if not access_token:
        print("Access Token Retrieval Failed for Capture")
        return jsonify({
            "error": "PayPal Authentication Failed",
            "details": {
                "possible_causes": [
                    "Incorrect Client ID",
                    "Incorrect Secret",
                    "Sandbox/Live mismatch (e.g. live mode active but sandbox credentials configured)",
                    "PayPal developer account not activated or REST App disabled"
                ]
            }
        }), 401

    # Standard API Execution
    capture_url = f"{get_paypal_api_base()}/v2/checkout/orders/{order_id}/capture"
    try:
        response = requests.post(
            capture_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }
        )

        capture_data = response.json()
        print("PAYPAL CAPTURE STATUS:", response.status_code)
        print("PAYPAL CAPTURE DATA:", capture_data)

        if "status" not in capture_data or capture_data["status"] != "COMPLETED":
            return jsonify({"status": "failed"})

        payer = capture_data["payer"]
        name = payer["name"]["given_name"] + " " + payer["name"]["surname"]
        email = payer["email_address"]
        amount = capture_data["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"]

        conn = get_db_connection()
        cursor = conn.execute(
            """INSERT INTO orders
            (user_id, paypal_order_id, buyer_name, buyer_email, amount, status, shipping_address)
            VALUES (?, ?, ?, ?, ?, 'COMPLETED', ?)""",
            (session['user_id'], order_id, name, email, amount, address)
        )
        order_db_id = cursor.lastrowid

        for product_id, quantity in session.get('cart', {}).items():
            product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
            if product:
                conn.execute("UPDATE products SET stock = stock - ? WHERE id=?", (quantity, product_id))
                conn.execute(
                    """INSERT INTO order_items (order_id, product_id, product_name, price, quantity)
                    VALUES (?, ?, ?, ?, ?)""",
                    (order_db_id, product['id'], product['name'], product['price'], quantity)
                )
        conn.commit()
        conn.close()

        session.pop("cart", None)
        return jsonify({"status": "success", "order_id": order_db_id})

    except Exception as e:
        app.logger.error(f"Payment capture exception: {e}")
        return jsonify({"status": "failed"})


# -------------------------
# User Profile
# -------------------------
@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    orders = conn.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()

    return render_template("profile.html", orders=orders, db_user=user)


# -------------------------
# Invoice PDF
# -------------------------
@app.route('/invoice/<int:order_id>')
@login_required
def invoice(order_id):
    conn = get_db_connection()
    order = conn.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?",
        (order_id, session['user_id'])
    ).fetchone()
    conn.close()

    if not order:
        return "Order not found", 404

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, "RIYORA DEMONSTRATION INVOICE")
    
    p.setFont("Helvetica", 11)
    p.drawString(100, 720, f"Invoice Reference: INV-{order['id']}")
    p.drawString(100, 705, f"Date Issued: {order['created_at']}")
    p.drawString(100, 690, f"Customer Email: {order['buyer_email']}")
    p.drawString(100, 675, f"Amount Paid: ${order['amount']:.2f}")
    p.drawString(100, 660, f"Transaction Status: {order['status']}")
    p.drawString(100, 645, f"Shipping Address: {order['shipping_address']}")

    p.setFont("Helvetica-Oblique", 9)
    p.drawString(100, 580, "Disclaimer: This is an educational demonstration receipt. No physical delivery is performed.")
    p.drawString(100, 565, "Thank you for supporting our learning & security showcase portfolio!")
    p.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"invoice_{order_id}.pdf",
        mimetype="application/pdf"
    )


# -------------------------
# Admin Actions
# -------------------------
@app.route('/access_restricted')
def access_restricted():
    return render_template("access_restricted.html")


@app.route('/track_support_click', methods=['POST'])
@csrf.exempt
def track_support_click():
    increment_metric('support_clicks')
    return jsonify({"status": "success"})


@app.route('/track_theme_toggle', methods=['POST'])
@csrf.exempt
def track_theme_toggle():
    increment_metric('theme_toggle_clicks')
    return jsonify({"status": "success"})


@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    
    total_visitors_row = conn.execute("SELECT value FROM portfolio_metrics WHERE key='total_visitors'").fetchone()
    total_visitors = total_visitors_row['value'] if total_visitors_row else 0
    
    support_clicks_row = conn.execute("SELECT value FROM portfolio_metrics WHERE key='support_clicks'").fetchone()
    support_clicks = support_clicks_row['value'] if support_clicks_row else 0

    theme_clicks_row = conn.execute("SELECT value FROM portfolio_metrics WHERE key='theme_toggle_clicks'").fetchone()
    theme_clicks = theme_clicks_row['value'] if theme_clicks_row else 0

    auth_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    orders_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    
    products_viewed_row = conn.execute("SELECT SUM(views) FROM products").fetchone()
    products_viewed = products_viewed_row[0] if products_viewed_row and products_viewed_row[0] is not None else 0
    
    most_viewed_row = conn.execute("SELECT name, views FROM products ORDER BY views DESC LIMIT 1").fetchone()
    most_viewed = f"{most_viewed_row['name']} ({most_viewed_row['views']} views)" if most_viewed_row and most_viewed_row['views'] > 0 else "None"
    
    # Quick Analytics summary
    recent_orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5").fetchall()
    recent_users = conn.execute("SELECT * FROM users ORDER BY last_login DESC LIMIT 5").fetchall()
    
    conn.close()
    
    return render_template(
        "admin_dashboard.html",
        total_visitors=total_visitors,
        support_clicks=support_clicks,
        theme_clicks=theme_clicks,
        auth_users=auth_users,
        orders_count=orders_count,
        products_viewed=products_viewed,
        most_viewed=most_viewed,
        recent_orders=recent_orders,
        recent_users=recent_users
    )


@app.route('/admin_products')
@admin_required
def admin_products():
    conn = get_db_connection()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("admin_products.html", products=products)


@app.route('/admin_add_product', methods=['POST'])
@admin_required
def admin_add_product():
    name = request.form['name']
    price = request.form['price']
    image = request.form['image']
    stock = request.form['stock']

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO products (name, price, image, stock, views) VALUES (?, ?, ?, ?, 0)",
        (name, price, image, stock)
    )
    conn.commit()
    conn.close()

    return redirect('/admin_products')


@app.route('/admin_delete_product', methods=['POST'])
@admin_required
def admin_delete_product():
    product_id = request.form['product_id']

    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id=?", (product_id,))
    conn.commit()
    conn.close()

    return redirect('/admin_products')


@app.route('/admin_edit_product/<int:id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(id):
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        image = request.form['image']
        stock = request.form['stock']

        conn.execute(
            "UPDATE products SET name=?, price=?, image=?, stock=? WHERE id=?",
            (name, price, image, stock, id)
        )
        conn.commit()
        conn.close()
        return redirect('/admin_products')

    product = conn.execute("SELECT * FROM products WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template("admin_edit_product.html", product=product)


@app.route('/admin_orders')
@admin_required
def admin_orders():
    conn = get_db_connection()
    orders = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
    conn.close()

    return render_template("admin_orders.html", orders=orders)


@app.route('/admin_sales')
@admin_required
def admin_sales():
    conn = get_db_connection()
    total_sales = conn.execute(
        "SELECT SUM(amount) FROM orders WHERE status='COMPLETED'"
    ).fetchone()[0]
    if total_sales is None:
        total_sales = 0

    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    conn.close()

    return render_template(
        "admin_sales.html",
        total_sales=total_sales,
        total_orders=total_orders
    )


@app.route('/admin_users')
@admin_required
def admin_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY last_login DESC").fetchall()
    conn.close()
    return render_template("admin_users.html", users=users)


@app.route('/admin_security')
@admin_required
def admin_security():
    security_status = {
        "google_oauth": "Active" if os.getenv("GOOGLE_CLIENT_ID") else "Disabled",
        "csrf": "Active",
        "rate_limiting": "Active",
        "secure_sessions": "Active",
        "cookie_httponly": "Active" if app.config.get('SESSION_COOKIE_HTTPONLY') else "Inactive",
        "cookie_samesite": app.config.get('SESSION_COOKIE_SAMESITE') or "None",
        "cookie_secure": "Active" if app.config.get('SESSION_COOKIE_SECURE') else "Inactive (Local/HTTP)",
        "sql_injection_defense": "Active (Parameterized Queries)",
        "xss_defense": "Active (Jinja Auto-Escaping)"
    }
    return render_template("admin_security.html", security_status=security_status)


@app.route('/admin_status')
@admin_required
def admin_status():
    import sys
    import platform
    db_size = "Unknown"
    if os.path.exists("shop.db"):
        size_bytes = os.path.getsize("shop.db")
        db_size = f"{size_bytes / 1024:.2f} KB"
        
    system_status = {
        "os": platform.system() + " " + platform.release(),
        "python_version": sys.version.split(" ")[0],
        "flask_version": "3.x",
        "db_path": os.path.abspath("shop.db"),
        "db_size": db_size,
        "health_check": "Healthy",
        "environment": os.getenv("FLASK_ENV", "development"),
        "data_retention_policy": f"Auto-Cleanup active ({os.getenv('DATA_RETENTION_HOURS', '24')} hrs)"
    }
    return render_template("admin_status.html", system_status=system_status)


@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    # Retrieve form fields
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()

    # Form Validation
    if not name or not email or not subject or not message:
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    # Email format validation
    import re
    email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(email_regex, email):
        return jsonify({"status": "error", "message": "Please enter a valid email address."}), 400

    if len(message) < 10:
        return jsonify({"status": "error", "message": "Message must be at least 10 characters long."}), 400

    # Check for SMTP
    contact_email = os.getenv("CONTACT_EMAIL")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")

    email_sent = False
    if contact_email and smtp_server and smtp_username and smtp_password:
        try:
            import smtplib
            from email.mime.text import MIMEText
            
            # Construct email
            msg = MIMEText(f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}")
            msg['Subject'] = f"Riyora Contact: {subject}"
            msg['From'] = smtp_username
            msg['To'] = contact_email

            smtp_port = int(os.getenv("SMTP_PORT", 587))
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, [contact_email], msg.as_string())
            server.quit()
            email_sent = True
        except Exception as e:
            # Fallback to DB
            print(f"SMTP failed, falling back to DB: {e}")

    if not email_sent:
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO contact_messages (name, email, subject, message) VALUES (?, ?, ?, ?)",
                (name, email, subject, message)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            return jsonify({"status": "error", "message": f"Failed to save message: {str(e)}"}), 500

    return jsonify({"status": "success", "message": "Thank you for connecting! Your message has been sent successfully."})


@app.route('/admin_contacts')
@admin_required
def admin_contacts():
    conn = get_db_connection()
    messages = conn.execute("SELECT * FROM contact_messages ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('admin_contacts.html', messages=messages)


@app.route('/admin_contact_read/<int:id>', methods=['POST'])
@admin_required
def admin_contact_read(id):
    conn = get_db_connection()
    conn.execute("UPDATE contact_messages SET is_read = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Message marked as read."})


@app.route('/admin_contact_delete/<int:id>', methods=['POST'])
@admin_required
def admin_contact_delete(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM contact_messages WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Message deleted."})


@app.route('/admin_search')
@admin_required
def admin_search():
    query = request.args.get("q")
    conn = get_db_connection()

    products = conn.execute(
        "SELECT * FROM products WHERE name LIKE ?",
        ('%' + query + '%',)
    ).fetchall()
    conn.close()

    return render_template(
        "admin_products.html",
        products=products,
        search_query=query
    )


@app.route('/admin_order_details/<int:order_id>')
@admin_required
def admin_order_details(order_id):
    conn = get_db_connection()
    items = conn.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall()
    conn.close()

    return render_template("admin_order_details.html", items=items)


@app.route('/admin_update_order', methods=['POST'])
@admin_required
def admin_update_order():
    order_id = request.form['order_id']
    status = request.form['status']

    conn = get_db_connection()
    conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()
    conn.close()

    return redirect('/admin_orders')


@app.route('/order_success/<int:order_id>')
@login_required
def order_success(order_id):
    conn = get_db_connection()
    order = conn.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?",
        (order_id, session['user_id'])
    ).fetchone()
    conn.close()

    if not order:
        return "Order not found", 404

    return render_template("order_success.html", order=order)


if __name__ == "__main__":
    env_debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=env_debug)